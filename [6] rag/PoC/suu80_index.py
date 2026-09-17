"""SUU-80: Part 63 전체를 OpenAI(gpt-4o-mini) + Kanon 2로 색인해 rag_chunk를 채운다.

사용법 (레포 루트에서):
  python <이 파일> --dry            # API 호출 없이 대상 청크 수·비용 추정만
  python <이 파일> --sample 20      # 표본 20개만 색인하고 context_text를 화면에 출력
  python <이 파일> --all            # 남은 전부 (이미 있는 chunk_key는 건너뜀)

규칙 (Linear SUU-80 실행 메모):
- doc_text = Subpart 제목 + 그 청크가 속한 조문(node) 전체. 조문이 400k자 넘으면 Subpart 제목 + 청크 자신.
- subpart_name = subpart_heading_for(nodes, node_key)
- 이미 rag_chunk에 있는 chunk_key는 건너뛴다(재실행 가능)
- 비용 캡 $10 (문자수/4 토큰 추정)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(r"C:\Users\Admin\Desktop\US Factory Compliance Service")
sys.path[:0] = [str(REPO / "[2] db/pipeline/5_rag"), str(REPO / "[2] db/pipeline/1_eCFR")]

from ecfr_chunk_index import index_chunk  # noqa: E402
from ecfr_index_run import select_subpart_chunks, subpart_heading_for  # noqa: E402

OUT = Path(__file__).parent / "suu80_out"
DOC_MAX_CHARS = 400_000          # 4o-mini 128k 토큰 안전선
COST_CAP_USD = 10.0
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6
WORKERS = 16                     # 청크당 ~3초 → 5,600개 ≈ 18분. 429는 아래 재시도로 흡수


def load_env():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_all(client, table, columns, release_id):
    rows, start, page = [], 0, 1000
    while True:
        r = (client.table(table).select(columns).eq("release_id", release_id)
             .range(start, start + page - 1).execute())
        rows.extend(r.data)
        if len(r.data) < page:
            return rows
        start += page


def current_release_id(client):
    r = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute()
    assert len(r.data) == 1, r.data
    return r.data[0]["release_id"]


def section_citation(node_key):
    m = re.search(r"/section-(63\.\d+)$", node_key)
    return f"40 CFR {m.group(1)}" if m else None


def build_targets(nodes, blocks, existing_keys):
    node_by_key = {n["node_key"]: n for n in nodes}
    blocks_by_node = defaultdict(list)
    for b in blocks:
        blocks_by_node[b["node_key"]].append(b)
    for bs in blocks_by_node.values():
        bs.sort(key=lambda b: b["block_no"])
    subparts = sorted({"/".join(n["node_key"].split("/")[:3]) for n in nodes if n["node_key"].count("/") >= 2})

    targets = []
    for sp in subparts:
        if node_by_key[sp]["node_type"] == "subpart":
            sp_heading = subpart_heading_for(nodes, sp + "/x")
        else:  # Part 단위 부록(Appendix A~E to Part 63) 등 6개: 자기 제목을 쓴다
            sp_heading = node_by_key[sp]["heading"]
        for chunk in select_subpart_chunks(nodes, blocks, sp):
            if chunk["chunk_key"] in existing_keys:
                continue
            node = node_by_key[chunk["node_key"]]
            node_blocks = blocks_by_node[chunk["node_key"]]
            body = "\n\n".join(b["text_content"] for b in node_blocks if b["text_content"])
            doc_text = f"{sp_heading}\n\n{node['heading']}\n\n{body}"
            if len(doc_text) > DOC_MAX_CHARS:
                doc_text = f"{sp_heading}\n\n{chunk['chunk_text']}"
            nos = chunk["block_nos"]
            locator = next((b["source_locator"] for b in node_blocks if b["block_no"] == nos[0]), None) if nos else None
            row_chunk = {
                "chunk_key": chunk["chunk_key"],
                "dataset": "ecfr",
                "doc_key": sp,  # Subpart(또는 Part 단위 부록) node_key
                "node_key": chunk["node_key"],
                "block_from": min(nos) if nos else None,
                "block_to": max(nos) if nos else None,
                "hierarchy_path": f"Title 40 > {sp_heading} > {node['heading']}",
                "heading": node["heading"],
                "citation": section_citation(chunk["node_key"]),
                "source_locator": locator,
                "chunk_text": chunk["chunk_text"],
                "contextualizer_model": "gpt-4o-mini",
                "context_prompt_version": "ctx_prompt_v1",
                "embed_model": "kanon-2-embedder",
                "embed_dims": 1792,
            }
            kind = "table" if chunk["parent_chunk_key"] else ("split" if "-" in chunk["chunk_key"].rsplit("/", 1)[1] else "body")
            targets.append({"node": node, "chunk": row_chunk, "doc_text": doc_text,
                            "subpart_name": sp_heading, "kind": kind})
    return targets


def estimate_cost(targets):
    tokens_in = sum((len(t["doc_text"]) + len(t["chunk"]["chunk_text"]) + 400) / 4 for t in targets)
    return tokens_in, tokens_in * PRICE_IN + len(targets) * 100 * PRICE_OUT


def pick_sample(targets, n):
    by_kind = defaultdict(list)
    for t in targets:
        by_kind[t["kind"]].append(t)
    rng = random.Random(80)
    picks = []
    for kind, share in (("body", n // 2), ("table", n // 4), ("split", n - n // 2 - n // 4)):
        picks += rng.sample(by_kind[kind], min(share, len(by_kind[kind])))
    return picks


def run_one(client, t, captured):
    def call_context(request):
        from ecfr_chunk_index import call_openai_api
        text = call_openai_api(request)
        captured[t["chunk"]["chunk_key"]] = text
        return text

    for attempt in range(5):
        try:
            index_chunk(t["node"], t["chunk"], t["doc_text"], subpart_name=t["subpart_name"],
                        client=client, call_context=call_context)
            return None
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** (attempt + 1))  # 2,4,8,16,32초 (429 흡수)
    return err


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--sample", type=int)
    g.add_argument("--all", action="store_true")
    args = ap.parse_args()

    load_env()
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = current_release_id(client)
    nodes = fetch_all(client, "ecfr_node", "release_id,node_key,node_type,heading,reserved", release_id)
    blocks = fetch_all(client, "ecfr_block", "node_key,block_no,kind,text_content,label_path,source_locator", release_id)
    existing = {r["chunk_key"] for r in fetch_all(client, "rag_chunk", "chunk_key", release_id)}
    print(f"release {release_id}: nodes {len(nodes)}, blocks {len(blocks)}, already indexed {len(existing)}")

    targets = build_targets(nodes, blocks, existing)
    tokens_in, cost = estimate_cost(targets)
    kinds = defaultdict(int)
    for t in targets:
        kinds[t["kind"]] += 1
    print(f"targets {len(targets)} {dict(kinds)} | est input {tokens_in/1e6:.1f}M tokens, est ${cost:.2f}")
    if args.dry:
        big = [t["chunk"]["chunk_key"] for t in targets if len(t["chunk"]["chunk_text"]) > 60_000]
        print("chunks >60k chars (Kanon 한도 위험):", big or "none")
        return
    if cost > COST_CAP_USD and args.all:
        sys.exit(f"예상 비용 ${cost:.2f} > 캡 ${COST_CAP_USD}. 중단.")

    todo = pick_sample(targets, args.sample) if args.sample else targets
    OUT.mkdir(exist_ok=True)
    captured, failed, done = {}, [], 0
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(run_one, client, t, captured): t for t in todo}
        for f in as_completed(futs):
            t = futs[f]
            err = f.result()
            done += 1
            if err:
                failed.append({"chunk_key": t["chunk"]["chunk_key"], "error": err})
            if done % 100 == 0 or args.sample:
                print(f"[{done}/{len(todo)}] {time.time()-t0:.0f}s failed={len(failed)}", flush=True)

    (OUT / "failed.json").write_text(json.dumps(failed, indent=1, ensure_ascii=False), encoding="utf-8")
    if args.sample:
        rows = [{"chunk_key": t["chunk"]["chunk_key"], "kind": t["kind"], "subpart_name": t["subpart_name"],
                 "chunk_text": t["chunk"]["chunk_text"][:600], "context_text": captured.get(t["chunk"]["chunk_key"])}
                for t in todo]
        (OUT / "sample.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        for r in rows:
            print("\n=== ", r["kind"], r["chunk_key"], "\n", r["context_text"])
    print(f"done {done}, failed {len(failed)}, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
