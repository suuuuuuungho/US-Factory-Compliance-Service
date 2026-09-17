"""Measure eCFR retrieval quality at the section level."""

from __future__ import annotations

import math
import re
import statistics
from typing import Any


_SECTION_RE = re.compile(r"\b63\.(\d+)\b")


def build_query_embedding_request(question: str) -> dict:
    """Return the Kanon embedding request for an evaluation question."""
    return {
        "texts": [question],
        "task": "retrieval/query",
        "overflow_strategy": None,
    }


def citation_section_key(citation: str) -> str:
    """Convert a CFR section citation to its eCFR node-key component."""
    match = _SECTION_RE.search(citation)
    if match is None:
        raise ValueError(f"citation does not contain a CFR 63 section: {citation}")
    return f"section-63.{match.group(1)}"


def section_key_of_chunk(chunk_key_or_node_key: dict[str, Any] | str) -> str:
    """Return the section component of a chunk or node key."""
    if isinstance(chunk_key_or_node_key, dict):
        node_key = chunk_key_or_node_key["node_key"]
    else:
        node_key = chunk_key_or_node_key
        if node_key.startswith("ecfr/"):
            node_key = node_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    return node_key.rsplit("/", 1)[-1]


def _subpart_of_chunk(chunk: dict[str, Any]) -> str:
    """Return the subpart code embedded in a chunk node key."""
    for piece in chunk["node_key"].split("/"):
        if piece.startswith("subpart-"):
            return piece.removeprefix("subpart-")
    return ""


def rank_sections(
    ranked_chunks: list[dict[str, Any]], *, k_max: int = 20
) -> list[dict[str, Any]]:
    """Collapse ranked chunks to their best, deterministically ordered sections."""
    sections = []
    seen = set()
    for chunk in sorted(
        ranked_chunks, key=lambda item: (-item["score"], item["chunk_key"])
    ):
        section_key = section_key_of_chunk(chunk)
        if section_key in seen:
            continue
        seen.add(section_key)
        sections.append(
            {
                "section_key": section_key,
                "chunk_key": chunk["chunk_key"],
                "subpart": _subpart_of_chunk(chunk),
                "score": chunk["score"],
            }
        )
        if len(sections) == k_max:
            break
    return sections


def gold_ranks(
    gold_citations: list[str], ranked_sections: list[dict[str, Any]]
) -> dict[str, int | None]:
    """Map each distinct cited section to its one-based retrieval rank."""
    section_ranks = {
        section["section_key"]: rank
        for rank, section in enumerate(ranked_sections, start=1)
    }
    return {
        section_key: section_ranks.get(section_key)
        for section_key in dict.fromkeys(
            citation_section_key(citation) for citation in gold_citations
        )
    }


def is_hit(
    gold_citations: list[str],
    ranked_sections: list[dict[str, Any]],
    *,
    top_k: int = 5,
    strict: bool = False,
) -> bool:
    """Return whether any, or all, gold sections are within ``top_k``."""
    ranks = gold_ranks(gold_citations, ranked_sections)
    found = [rank is not None and rank <= top_k for rank in ranks.values()]
    return all(found) if strict else any(found)


def _wilson_interval(successes: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.96
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def summarize(
    results: list[dict[str, Any]],
    *,
    ks: tuple[int, ...] = (1, 3, 5, 10, 20),
    k_max: int = 20,
) -> dict:
    """Aggregate section-level evaluation results into the published metrics."""
    total = len(results)

    def rate(predicate: Any) -> dict[str, float]:
        return {
            str(k): (sum(predicate(result, k) for result in results) / total if total else 0.0)
            for k in ks
        }

    def ranks_within(result: dict[str, Any], k: int) -> list[bool]:
        return [
            rank is not None and rank <= k
            for rank in result["gold_ranks"].values()
        ]

    hit_loose = rate(lambda result, k: any(ranks_within(result, k)))
    hit_strict = rate(lambda result, k: all(ranks_within(result, k)))
    recall = rate(
        lambda result, k: (
            sum(ranks_within(result, k)) / len(result["gold_ranks"])
            if result["gold_ranks"]
            else 0.0
        )
    )
    subpart_hit_primary = rate(
        lambda result, k: bool(result["gold_subparts"])
        and result["gold_subparts"][0] in result["returned_subparts"][:k]
    )

    def ndcg_at(result: dict[str, Any], k: int) -> float:
        """Binary gain: every gold section is worth 1."""
        ranks = result["gold_ranks"]
        if not ranks:
            return 0.0
        dcg = sum(
            1 / math.log2(rank + 1)
            for rank in ranks.values()
            if rank is not None and rank <= k
        )
        ideal = sum(1 / math.log2(i + 1) for i in range(1, min(len(ranks), k) + 1))
        return dcg / ideal

    ndcg = rate(ndcg_at)

    first_ranks = [
        min((rank for rank in result["gold_ranks"].values() if rank is not None), default=None)
        for result in results
    ]
    mrr_20 = (
        sum(1 / rank for rank in first_ranks if rank is not None and rank <= k_max)
        / total
        if total
        else 0.0
    )
    median_first_gold_rank = (
        statistics.median(
            rank if rank is not None and rank <= k_max else k_max + 1
            for rank in first_ranks
        )
        if total
        else 0
    )

    return {
        "n_cases": total,
        "hit_loose": hit_loose,
        "hit_strict": hit_strict,
        "recall": recall,
        "subpart_hit_primary": subpart_hit_primary,
        "ndcg": ndcg,
        "mrr_20": mrr_20,
        "median_first_gold_rank": median_first_gold_rank,
        "ci95_hit_loose_5": _wilson_interval(
            sum(any(ranks_within(result, 5)) for result in results), total
        ),
        "ci95_hit_loose_20": _wilson_interval(
            sum(any(ranks_within(result, 20)) for result in results), total
        ),
    }


__all__ = [
    "build_query_embedding_request",
    "citation_section_key",
    "gold_ranks",
    "is_hit",
    "rank_sections",
    "section_key_of_chunk",
    "summarize",
]
