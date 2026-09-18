"""SUU-133: run_eval --embedder kanon|bge / --no-context — run_id·runs.jsonl에 임베더·컨텍스트 여부가 남는다."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path[:0] = [str(RAG / "eval"), str(RAG.parent / "[2] db/pipeline/5_rag")]

from run_eval import embed_model_of, run_id_for  # noqa: E402


def test_run_id_marks_embedder_and_context():
    assert run_id_for("2026-09-18", "vector", "v2", "kanon") == "2026-09-18_vector_v2"
    assert run_id_for("2026-09-18", "vector", "v2", "kanon", embedder="bge") == "2026-09-18_vector_v2_bge"
    assert run_id_for("2026-09-18", "vector", "v2", "kanon", embedder="bge", with_context=False) == "2026-09-18_vector_v2_bge_nocontext"
    assert embed_model_of("kanon") == "kanon-2-embedder"
    assert embed_model_of("bge") == "BAAI/bge-m3"
