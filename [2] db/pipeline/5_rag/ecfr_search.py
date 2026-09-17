"""Search eCFR chunks and return the highest-ranking sections."""

from __future__ import annotations

from typing import Any, Callable

from ecfr_eval import build_query_embedding_request, rank_sections
from ecfr_index_run import rank_chunks_by_similarity


def build_rerank_request(question: str, chunks: list[dict[str, Any]]) -> dict:
    """Return the Kanon 2 reranking request for retrieved chunks."""
    return {
        "query": question,
        "texts": [
            f"{chunk['context_text']}\n\n{chunk['chunk_text']}"
            if chunk.get("context_text")
            else chunk["chunk_text"]
            for chunk in chunks
        ],
    }


def search_sections(
    question: str,
    *,
    embed: Callable[[dict], list[float]],
    chunks: list[dict[str, Any]],
    rerank: Callable[[str, list[dict[str, Any]]], list[float]] | None = None,
    top_k: int = 5,
    chunk_top_k: int = 300,
) -> list[dict]:
    """Embed a question, rank its chunks, and collapse them to sections."""
    query_embedding = embed(build_query_embedding_request(question))
    ranked_chunks = rank_chunks_by_similarity(
        query_embedding, chunks, top_k=chunk_top_k
    )
    if rerank is not None:
        scores = rerank(question, ranked_chunks)
        ranked_chunks = [
            {**chunk, "score": score}
            for chunk, score in zip(ranked_chunks, scores)
        ]
    return rank_sections(ranked_chunks, k_max=top_k)


__all__ = ["build_rerank_request", "search_sections"]
