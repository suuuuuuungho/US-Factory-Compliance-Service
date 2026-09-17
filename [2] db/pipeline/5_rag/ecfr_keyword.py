"""BM25 keyword search over eCFR chunks, indexed in memory."""

from __future__ import annotations

import re
from typing import Any, Callable

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase words and section numbers such as ``63.7485``."""
    return _TOKEN_RE.findall(text.lower())


def build_keyword_search(
    chunks: list[dict[str, Any]],
) -> Callable[[str, int], list[dict[str, Any]]]:
    """Index ``context_text + chunk_text`` and return ``keyword(question, k)``."""
    corpus = [
        tokenize(f"{chunk.get('context_text') or ''} {chunk['chunk_text']}")
        for chunk in chunks
    ]
    bm25 = BM25Okapi(corpus)

    def keyword(question: str, k: int) -> list[dict[str, Any]]:
        scores = bm25.get_scores(tokenize(question))
        ranked = sorted(
            (
                (score, chunk["chunk_key"], chunk["node_key"])
                for score, chunk in zip(scores, chunks)
                if score > 0
            ),
            key=lambda item: (-item[0], item[1]),
        )
        return [
            {"chunk_key": chunk_key, "node_key": node_key, "score": float(score)}
            for score, chunk_key, node_key in ranked[:k]
        ]

    return keyword


__all__ = ["build_keyword_search", "tokenize"]
