"""SUU-81: 평가셋 32건으로 검색 정확도를 잰다 (파이썬 전수 코사인).

사용법 (레포 루트에서):
  python "[6] rag/eval/run_eval.py" --config vector   # 조합: vector / reranker / hybrid → results/<run_id>.jsonl + runs.jsonl 한 줄
  python "[6] rag/eval/run_eval.py" --eval-set v2   # 평가셋: v1 32건(기본) / v2 102건(SUU-120)
  python "[6] rag/eval/run_eval.py" --run-id X      # run_id 직접 지정

규칙: rag_eval_plan.md [5] 절차, [8] 파일 형식. 채점표(SUU-117): Hit@5, Hit@20, nDCG@10, Recall@20 (+MRR 비교용). 질문 임베딩은 rag_eval_query_embeddings[_v2].json에 캐시한다.
failure_code/failure_note는 실행 후 Claude가 손으로 채운다.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "[2] db/pipeline/5_rag")]

from ecfr_chunk_index import call_isaacus_rerank_api, call_kanon2_api  # noqa: E402
from ecfr_eval import (  # noqa: E402
    build_query_embedding_request, citation_section_key, gold_ranks, summarize,
)
from ecfr_keyword import build_keyword_search  # noqa: E402
from ecfr_search import build_rerank_request, search_sections  # noqa: E402

HERE = Path(__file__).parent
EVAL_SETS = {
    "v1": (HERE / "rag_eval_case.jsonl", HERE / "rag_eval_query_embeddings.json"),
    "v2": (HERE / "rag_eval_case_v2.jsonl", HERE / "rag_eval_query_embeddings_v2.json"),
}
RUNS = HERE / "runs.jsonl"
RESULTS = HERE / "results"
K_MAX = 20
CHUNK_TOP_K = 300  # 조문 20개를 채우기에 넉넉한 청크 수


def load_env():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_chunks(client, release_id, *, include_text=False):
    rows, start, page = [], 0, 500
    columns = "chunk_key,node_key,embedding"
    if include_text:
        columns += ",context_text,chunk_text"
    while True:
        r = (client.table("rag_chunk").select(columns)
             .eq("release_id", release_id).eq("index_status", "embedded")
             .order("chunk_key").range(start, start + page - 1).execute())
        rows.extend(r.data)
        print(f"  chunks fetched {len(rows)}", flush=True)
        if len(r.data) < page:
            break
        start += page
    for row in rows:
        if isinstance(row["embedding"], str):
            row["embedding"] = json.loads(row["embedding"])
    return rows


def query_embeddings(cases, cache_path):
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    latency = {}
    for c in cases:
        if c["case_id"] in cache and cache[c["case_id"]]["question"] == c["question"]:
            continue
        t0 = time.perf_counter()
        emb = call_kanon2_api(build_query_embedding_request(c["question"]))
        latency[c["case_id"]] = (time.perf_counter() - t0) * 1000
        cache[c["case_id"]] = {"question": c["question"], "embedding": emb, "embed_ms": latency[c["case_id"]]}
        print(f"  embedded {c['case_id']}", flush=True)
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    return cache


def p(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, int(round(q * (len(values) - 1))))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--config", choices=("vector", "reranker", "hybrid"), default="vector")
    ap.add_argument("--eval-set", choices=tuple(EVAL_SETS), default="v1")
    args = ap.parse_args()
    load_env()
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    run_at = datetime.now(timezone.utc)
    run_id = args.run_id or f"{run_at:%Y-%m-%d}_{args.config}_{args.eval_set}"
    cases_path, cache_path = EVAL_SETS[args.eval_set]

    cases = [json.loads(l) for l in cases_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"release {release_id}, cases {len(cases)}, commit {commit}")
    chunks = fetch_chunks(client, release_id, include_text=args.config in ("hybrid", "reranker"))
    cache = query_embeddings(cases, cache_path)
    rerank_input_tokens = 0

    def rerank(question, ranked):
        nonlocal rerank_input_tokens
        response = call_isaacus_rerank_api(build_rerank_request(question, ranked))
        rerank_input_tokens += response["input_tokens"]
        return response["scores"]

    keyword = build_keyword_search(chunks) if args.config == "hybrid" else None

    lines = []
    for c in cases:
        t0 = time.perf_counter()
        sections = search_sections(
            c["question"],
            embed=lambda request: cache[c["case_id"]]["embedding"],
            chunks=chunks,
            keyword=keyword,
            rerank=rerank if args.config in ("hybrid", "reranker") else None,
            top_k=K_MAX,
            chunk_top_k=150 if args.config in ("hybrid", "reranker") else CHUNK_TOP_K,
        )
        search_ms = (time.perf_counter() - t0) * 1000
        ranks = gold_ranks(c["gold_citations"], sections)
        within = lambda k: [r is not None and r <= k for r in ranks.values()]  # noqa: E731
        first = min((r for r in ranks.values() if r is not None), default=None)
        lines.append({
            "run_id": run_id,
            "case_id": c["case_id"],
            "gold_sections": list(ranks),
            "gold_subparts": c["gold_subparts"],
            "returned_sections": [s["section_key"] for s in sections],
            "returned_chunk_keys": [s["chunk_key"] for s in sections],
            "returned_scores": [round(s["score"], 4) for s in sections],
            "returned_subparts": [s["subpart"] for s in sections],
            "first_gold_rank": first,
            "gold_ranks": ranks,
            "hit_loose_5": any(within(5)), "hit_strict_5": all(within(5)), "recall_5": sum(within(5)) / len(ranks),
            "hit_loose_20": any(within(20)), "hit_strict_20": all(within(20)), "recall_20": sum(within(20)) / len(ranks),
            "subpart_hit_primary_5": c["gold_subparts"][0] in [s["subpart"] for s in sections[:5]],
            "latency_ms": {"embed": round(cache[c["case_id"]]["embed_ms"]), "search": round(search_ms)},
            "failure_code": None,
            "failure_note": None,
        })

    metrics = summarize(lines, k_max=K_MAX)
    embed_ms = [l["latency_ms"]["embed"] for l in lines]
    search_ms = [l["latency_ms"]["search"] for l in lines]
    run = {
        "run_id": run_id,
        "run_at": run_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": args.config,
        "eval_set_version": args.eval_set,
        "n_cases": len(lines),
        "release_id": release_id,
        "embed_model": "kanon-2-embedder",
        "contextualizer_model": "gpt-4o-mini",
        "context_prompt_version": "ctx_prompt_v1",
        "chunk_rule_commit": commit,
        "k_max": K_MAX,
        "metrics": metrics,
        "latency_ms": {"embed_p50": p(embed_ms, 0.5), "embed_p95": p(embed_ms, 0.95),
                       "search_p50": p(search_ms, 0.5), "search_p95": p(search_ms, 0.95)},
        "cost_usd": (
            {"per_query": rerank_input_tokens * 0.35 / 1e6 / len(cases),
             "total": rerank_input_tokens * 0.35 / 1e6}
            if args.config in ("hybrid", "reranker")
            else {"per_query": None, "total": None}
        ),
        "failure_counts": {f"F{i}": 0 for i in range(1, 8)},
        "notes": f"index coverage {len(chunks)} embedded chunks (python full-scan cosine"
                 f"{' + BM25 RRF + Kanon 2 rerank' if args.config == 'hybrid' else ' + Kanon 2 rerank' if args.config == 'reranker' else ''}, not HNSW)",
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{run_id}.jsonl").write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lines), encoding="utf-8")
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps(metrics, indent=1))
    print(f"scoreboard: Hit@5 {metrics['hit_loose']['5']:.3f}  Hit@20 {metrics['hit_loose']['20']:.3f}  "
          f"nDCG@10 {metrics['ndcg']['10']:.3f}  Recall@20 {metrics['recall']['20']:.3f}  (MRR {metrics['mrr_20']:.3f})")
    print("misses@20:", [l["case_id"] for l in lines if not l["hit_loose_20"]])


if __name__ == "__main__":
    main()
