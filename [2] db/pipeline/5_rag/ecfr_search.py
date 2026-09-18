"""Search eCFR chunks and return the highest-ranking sections."""

from __future__ import annotations

from typing import Any, Callable

from ecfr_eval import build_query_embedding_request, rank_sections
from ecfr_index_run import rank_chunks_by_similarity
from ecfr_llm_rerank import LLM_TOP_N, llm_rerank_sections, section_head

# SUU-132에서 고른 리랭크 후처리 규칙: 조문 상위 ``window``개 안에서
# 표(appendix-Table)를 뒤로, 1~5등에 나온 Subpart 상위 ``subpart_top``개 + A를 앞으로.
RULES = {"window": 60, "demote_tables": True, "subpart_top": 2}


def rrf_merge(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    k: int = 60,
    weights: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Merge ranked result lists with reciprocal-rank fusion.

    ``weights`` scales each list's contribution (default 1.0 each); a list
    weighted 0 is skipped entirely.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    merged: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    for ranked, weight in zip(ranked_lists, weights):
        if weight == 0:
            continue
        for rank, chunk in enumerate(ranked, start=1):
            key = chunk["chunk_key"]
            if key not in merged:
                merged[key] = dict(chunk)
            scores[key] = scores.get(key, 0.0) + weight / (k + rank)
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


def apply_rank_rules(
    sections: list[dict[str, Any]],
    *,
    window: int | None,
    demote_tables: bool,
    subpart_top: int,
) -> list[dict[str, Any]]:
    """Reorder the top ``window`` sections with the $0 rules; the rest stay put."""
    head, tail = (sections[:window], sections[window:]) if window else (list(sections), [])
    if subpart_top:
        found: list[str] = []
        for section in head[:5]:
            if section["subpart"] not in found:
                found.append(section["subpart"])
        keep = set(found[:subpart_top]) | {"A"}
        head = [s for s in head if s["subpart"] in keep] + [s for s in head if s["subpart"] not in keep]
    if demote_tables:
        head = [s for s in head if "Table" not in s["section_key"]] + [s for s in head if "Table" in s["section_key"]]
    return head + tail


def search_sections(
    question: str,
    *,
    embed: Callable[[dict], list[float]],
    chunks: list[dict[str, Any]],
    keyword: Callable[[str, int], list[dict[str, Any]]] | None = None,
    rerank: Callable[[str, list[dict[str, Any]]], list[float]] | None = None,
    top_k: int = 5,
    chunk_top_k: int = 300,
    rules: bool = True,
    llm: Callable[[str], str] | None = None,
) -> list[dict]:
    """Embed a question, rank its chunks, and collapse them to sections.

    With a reranker, ``rules`` applies ``RULES`` to the reranked sections.
    ``llm`` (prompt -> answer) then reorders the top ``LLM_TOP_N`` sections
    (SUU-136) before cutting to ``top_k``.
    """
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
    ruled = rerank is not None and rules
    k_max = max(top_k, RULES["window"] if ruled else 0, LLM_TOP_N if llm else 0)
    sections = rank_sections(ranked_chunks, k_max=k_max)
    if ruled:
        sections = apply_rank_rules(sections, **RULES)
    if llm is not None:
        by_key = {chunk["chunk_key"]: chunk for chunk in chunks}
        texts = {
            s["section_key"]: section_head(by_key.get(s["chunk_key"].rsplit("/", 1)[0] + "/0"))
            for s in sections[:LLM_TOP_N]
        }
        sections = llm_rerank_sections(question, sections, llm, texts=texts)
    return sections[:top_k]


__all__ = ["RULES", "apply_rank_rules", "build_rerank_request", "rrf_merge", "search_sections"]
