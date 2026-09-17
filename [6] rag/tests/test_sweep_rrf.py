"""SUU-130: sweep_rrf.py — 후보 풀 진단(pool-miss / rank-miss)과 RRF 가중치 스윕 표."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from sweep_rrf import GRID, classify_miss, pool_recall, sweep_table  # noqa: E402


def _chunk(key, section):
    return {"chunk_key": key, "node_key": f"ecfr/subpart-A/{section}", "score": 1.0}


def test_classify_miss_sums_to_total():
    pool = ["section-63.1", "section-63.2"]
    kinds = [classify_miss(gold, pool) for gold in (["section-63.1"], ["section-63.9"], ["section-63.2", "section-63.9"])]
    assert kinds == ["rank-miss", "pool-miss", "rank-miss"]
    assert kinds.count("pool-miss") + kinds.count("rank-miss") == 3


def test_pool_recall_counts_gold_sections_in_first_n_chunks():
    pool = [_chunk("a", "section-63.1"), _chunk("b", "section-63.2"), _chunk("c", "section-63.9")]
    assert pool_recall(["section-63.1", "section-63.9"], pool, 2) == 0.5
    assert pool_recall(["section-63.1", "section-63.9"], pool, 3) == 1.0


def test_sweep_table_shape():
    cases = [{"gold": ["section-63.1"], "vector": [_chunk("a", "section-63.1")], "keyword": [_chunk("b", "section-63.2")]}]
    rows = sweep_table(cases)
    assert len(rows) == len(GRID["w"]) * len(GRID["k"]) * len(GRID["depth"]) == 132
    assert {"w", "k", "depth", "recall@150", "recall@50", "recall@20"} <= set(rows[0])
    assert all(r["recall@150"] == 1.0 for r in rows if r["w"] > 0)
