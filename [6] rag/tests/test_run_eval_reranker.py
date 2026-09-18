"""SUU-131: run_eval --reranker kanon|bge|nemotron — run_id·runs.jsonl에 리랭커 모델이 남는다."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from run_eval import rerank_model, run_id_for  # noqa: E402


def test_runs_has_rerank_model():
    assert rerank_model("vector", "kanon") is None
    assert rerank_model("reranker", "kanon") == "kanon-2-reranker"
    assert rerank_model("hybrid", "bge") == "BAAI/bge-reranker-v2-m3"
    assert rerank_model("hybrid", "nemotron") == "nvidia/llama-nemotron-rerank-1b-v2"


def test_run_id_keeps_kanon_name_and_adds_local_suffix():
    assert run_id_for("2026-09-18", "reranker", "v2", "kanon") == "2026-09-18_reranker_v2"
    assert run_id_for("2026-09-18", "hybrid", "v2", "nemotron") == "2026-09-18_hybrid_v2_nemotron"
    assert run_id_for("2026-09-18", "vector", "v2", "bge") == "2026-09-18_vector_v2"
