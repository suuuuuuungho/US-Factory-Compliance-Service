"""Search eCFR chunks and return the highest-ranking sections."""

from __future__ import annotations

from typing import Any, Callable

from ecfr_eval import build_query_embedding_request, rank_sections
from ecfr_index_run import rank_chunks_by_similarity


def search_sections(
    question: str,
    *,
    embed: Callable[[dict], list[float]],
    chunks: list[dict[str, Any]],
    top_k: int = 5,
    chunk_top_k: int = 300,
) -> list[dict]:
    """Embed a question, rank its chunks, and collapse them to sections."""
    query_embedding = embed(build_query_embedding_request(question))
    ranked_chunks = rank_chunks_by_similarity(
        query_embedding, chunks, top_k=chunk_top_k
    )
    return rank_sections(ranked_chunks, k_max=top_k)


__all__ = ["search_sections"]
