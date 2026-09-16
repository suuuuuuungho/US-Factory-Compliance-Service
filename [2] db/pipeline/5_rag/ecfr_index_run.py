"""Select and rank eCFR chunks for a small indexing run."""

from __future__ import annotations

import math
from typing import Any

from ecfr_chunks import build_chunks


def select_subpart_chunks(
    nodes: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    subpart_key: str,
) -> list[dict[str, Any]]:
    """Build chunks for sections and appendices below one subpart."""
    prefix = f"{subpart_key}/"
    subpart_nodes = [
        node for node in nodes if node["node_key"].startswith(prefix)
    ]
    chunks = build_chunks(subpart_nodes, blocks)

    block_text_by_node: dict[str, dict[int, str]] = {}
    for block in blocks:
        block_text_by_node.setdefault(block["node_key"], {})[
            block["block_no"]
        ] = block["text_content"]

    for chunk in chunks:
        block_texts = block_text_by_node[chunk["node_key"]]
        chunk["chunk_text"] = "\n\n".join(
            block_texts[block_no] for block_no in chunk["block_nos"]
        )

    return [chunk for chunk in chunks if chunk["chunk_text"].strip()]


def rank_chunks_by_similarity(
    query_embedding: list[float],
    chunks: list[dict[str, Any]],
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return copies of chunks ordered by cosine similarity."""
    query_norm = math.sqrt(sum(value * value for value in query_embedding))
    ranked = []

    for chunk in chunks:
        embedding = chunk["embedding"]
        embedding_norm = math.sqrt(sum(value * value for value in embedding))
        denominator = query_norm * embedding_norm
        score = (
            sum(a * b for a, b in zip(query_embedding, embedding)) / denominator
            if denominator
            else 0.0
        )
        ranked.append({**chunk, "score": score})

    ranked.sort(key=lambda chunk: chunk["score"], reverse=True)
    return ranked if top_k is None else ranked[:top_k]


__all__ = ["rank_chunks_by_similarity", "select_subpart_chunks"]
