"""Search eCFR chunks and return the highest-ranking sections."""

from __future__ import annotations

from typing import Any, Callable

from ecfr_eval import build_query_embedding_request, rank_sections
from ecfr_index_run import rank_chunks_by_similarity


def rrf_merge(ranked_lists: list[list[dict[str, Any]]], *, k: int = 60) -> list[dict[str, Any]]:
    """Merge ranked result lists with reciprocal-rank fusion."""
    merged: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            key = chunk["chunk_key"]
            if key not in merged:
                merged[key] = dict(chunk)
            scores[key] = scores.get(key, 0.0) + 1 / (k + rank)
    return [
        {**merged[key], "score": scores[key]}
        for key in sorted(scores, key=lambda item: (-scores[item], item))
    ]


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
    keyword: Callable[[str, int], list[dict[str, Any]]] | None = None,
    rerank: Callable[[str, list[dict[str, Any]]], list[float]] | None = None,
    top_k: int = 5,
    chunk_top_k: int = 300,
) -> list[dict]:
    """Embed a question, rank its chunks, and collapse them to sections."""
    query_embedding = embed(build_query_embedding_request(question))
    vector_chunks = rank_chunks_by_similarity(
        query_embedding, chunks, top_k=chunk_top_k
    )
    if keyword is None:
        ranked_chunks = vector_chunks
    else:
        by_key = {chunk["chunk_key"]: chunk for chunk in chunks}
        keyword_chunks = [
            by_key[hit["chunk_key"]]
            for hit in keyword(question, chunk_top_k)
            if hit["chunk_key"] in by_key
        ]
        ranked_chunks = rrf_merge([vector_chunks, keyword_chunks])[:chunk_top_k]
    if rerank is not None:
        scores = rerank(question, ranked_chunks)
        ranked_chunks = [
            {**chunk, "score": score}
            for chunk, score in zip(ranked_chunks, scores)
        ]
    return rank_sections(ranked_chunks, k_max=top_k)


__all__ = ["build_rerank_request", "rrf_merge", "search_sections"]
