"""SUU-130: RRF 가중치별 후보 풀 Recall과 실패 진단 (rerank 없음, $0).

사용법 (레포 루트에서):
  python "[6] rag/eval/sweep_rrf.py"   # v2 102건 → results/rrf_sweep.csv + 진단·요약 출력

무엇을 재나:
- 후보 풀 = vector 상위 depth + BM25 상위 depth → RRF(k, weights=[w, 1-w]) 상위 N 청크.
  recall@N = 정답 조문 중 그 N개 청크 안에 청크가 하나라도 있는 비율(조문 단위, 케이스 평균).
  w=1.0·depth=150이면 reranker 조합의 풀, w=0.5·k=60·depth=150이면 hybrid 조합의 풀과 같다.
- 진단 = reranker_v2·hybrid_v2 결과의 top-20 실패를 pool-miss(정답이 150개 풀에 하나도 없음) /
  rank-miss(풀에 있는데 리랭커가 20등 안에 못 올림)로 나눈다.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "[2] db/pipeline/5_rag"), str(Path(__file__).parent)]

from ecfr_eval import citation_section_key, section_key_of_chunk  # noqa: E402
from ecfr_index_run import rank_chunks_by_similarity  # noqa: E402
from ecfr_keyword import build_keyword_search  # noqa: E402
from ecfr_search import rrf_merge  # noqa: E402
from run_eval import EVAL_SETS, RESULTS, fetch_chunks, load_env  # noqa: E402

GRID = {
    "w": [round(i / 10, 1) for i in range(11)],  # vector 비중. BM25 = 1 - w
    "k": [10, 20, 40, 60, 100, 200],
    "depth": [150, 300],  # 목록마다 몇 개씩 섞나
}
POOL = 150  # 리랭커에 넘기는 청크 수
NS = (150, 50, 20)
DEFAULT = (0.5, 60, 150)  # 지금 hybrid 조합
SWEEP_CSV = RESULTS / "rrf_sweep.csv"
DIAG_RUNS = ("2026-09-17_reranker_v2", "2026-09-17_hybrid_v2")


def pool_recall(gold_sections: list[str], pool: list[dict], n: int) -> float:
    """정답 조문 중 상위 n개 청크 안에 있는 비율."""
    seen = {section_key_of_chunk(c) for c in pool[:n]}
    return sum(g in seen for g in gold_sections) / len(gold_sections)


def classify_miss(gold_sections: list[str], pool_sections: list[str]) -> str:
    return "rank-miss" if any(g in pool_sections for g in gold_sections) else "pool-miss"


def fuse(case: dict, w: float, k: int, depth: int) -> list[dict]:
    return rrf_merge([case["vector"][:depth], case["keyword"][:depth]], k=k, weights=[w, 1 - w])[:POOL]


def sweep_table(cases: list[dict]) -> list[dict]:
    """cases: {gold, vector(청크 순위), keyword(청크 순위)} → 132행."""
    rows = []
    for depth in GRID["depth"]:
        for k in GRID["k"]:
            for w in GRID["w"]:
                pools = [fuse(c, w, k, depth) for c in cases]
                row = {"w": w, "k": k, "depth": depth}
                for n in NS:
                    row[f"recall@{n}"] = round(sum(pool_recall(c["gold"], p, n) for c, p in zip(cases, pools)) / len(cases), 4)
                row["any@150"] = round(sum(pool_recall(c["gold"], p, POOL) > 0 for c, p in zip(cases, pools)) / len(cases), 4)
                rows.append(row)
    return rows


def main():
    load_env()
    from supabase import create_client
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
    cases_path, cache_path = EVAL_SETS["v2"]
    raw = [json.loads(l) for l in cases_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    chunks = fetch_chunks(client, release_id, include_text=True)
    keyword = build_keyword_search(chunks)
    by_key = {c["chunk_key"]: c for c in chunks}
    depth = max(GRID["depth"])
    cases = [{
        "case_id": c["case_id"],
        "gold": list(dict.fromkeys(citation_section_key(x) for x in c["gold_citations"])),
        "vector": rank_chunks_by_similarity(cache[c["case_id"]]["embedding"], chunks, top_k=depth),
        "keyword": [by_key[h["chunk_key"]] for h in keyword(c["question"], depth)],
    } for c in raw]
    print(f"cases {len(cases)}, chunks {len(chunks)}", flush=True)

    # 1) 진단: reranker 풀(w=1.0) / hybrid 풀(기본)에서 miss@20을 나눈다
    print("\n== diagnosis (miss@20 → pool-miss / rank-miss)")
    for run_id in DIAG_RUNS:
        w = 1.0 if "reranker" in run_id else DEFAULT[0]
        lines = [json.loads(l) for l in (RESULTS / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        misses = {l["case_id"] for l in lines if not l["hit_loose_20"]}
        kinds = {}
        for c in cases:
            if c["case_id"] in misses:
                pool_sections = [section_key_of_chunk(x) for x in fuse(c, w, DEFAULT[1], DEFAULT[2])]
                kinds[c["case_id"]] = (classify_miss(c["gold"], pool_sections),
                                       f"{sum(g in pool_sections for g in c['gold'])}/{len(c['gold'])} in pool")
        print(f"{run_id}: miss {len(kinds)} = pool-miss {sum(k == 'pool-miss' for k, _ in kinds.values())}"
              f" + rank-miss {sum(k == 'rank-miss' for k, _ in kinds.values())}")
        for cid, (kind, note) in kinds.items():
            print(f"  {kind:9s} {note:12s} {cid}")

    # 2) 스윕
    rows = sweep_table(cases)
    with SWEEP_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pick = lambda w, k, d: next(r for r in rows if (r["w"], r["k"], r["depth"]) == (w, k, d))  # noqa: E731
    print(f"\n== sweep → {SWEEP_CSV.name} ({len(rows)} rows)")
    print("vector-only pool:", pick(1.0, *DEFAULT[1:]))
    print("bm25-only pool:  ", pick(0.0, *DEFAULT[1:]))
    print("default hybrid:  ", pick(*DEFAULT))
    print("best 5 by recall@150:")
    for r in sorted(rows, key=lambda r: (-r["recall@150"], -r["recall@50"]))[:5]:
        print("  ", r)
    print("best w per (depth, k) by recall@150:")
    for d in GRID["depth"]:
        for k in GRID["k"]:
            best = max((r for r in rows if r["k"] == k and r["depth"] == d), key=lambda r: (r["recall@150"], r["recall@50"]))
            print(f"  depth {d} k {k:3d}: w {best['w']}  recall@150 {best['recall@150']}  @50 {best['recall@50']}  @20 {best['recall@20']}")


if __name__ == "__main__":
    main()
