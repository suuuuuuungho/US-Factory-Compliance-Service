"""Contextualize, embed, and persist one eCFR chunk."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from typing import Any

import requests
from anthropic import Anthropic

from ecfr_context import build_context_request
from ecfr_embed import build_embedding_request


def call_claude_api(request: dict[str, Any]) -> str:
    """Generate one chunk context with Claude."""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=request["system"],
        messages=request["messages"],
    )
    return response.content[0].text


def call_kanon2_api(request: dict[str, Any]) -> list[float]:
    """Embed one contextualized chunk with Kanon 2."""
    response = requests.post(
        "https://api.isaacus.com/v1/embeddings",
        headers={"Authorization": f"Bearer {os.environ['ISAACUS_API_KEY']}"},
        json={"model": "kanon-2-embedder", **request},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]["embedding"]


def index_chunk(
    node: dict[str, Any],
    chunk: dict[str, Any],
    doc_text: str,
    *,
    client: Any,
    call_claude: Callable[[dict[str, Any]], str] = call_claude_api,
    call_kanon2: Callable[[dict[str, Any]], list[float]] = call_kanon2_api,
) -> None:
    """Contextualize, embed, and upsert one chunk into ``rag_chunk``."""
    chunk_text = chunk["chunk_text"]
    context_text = call_claude(build_context_request(doc_text, chunk_text))
    embedding = call_kanon2(build_embedding_request(context_text, chunk_text))
    content_hash = hashlib.sha256(
        f"{chunk_text}\n\n{context_text}".encode("utf-8")
    ).hexdigest()

    row = {
        **chunk,
        "release_id": node["release_id"],
        "context_text": context_text,
        "embedding": embedding,
        "content_hash": content_hash,
        "index_status": "embedded",
    }
    (
        client.table("rag_chunk")
        .upsert([row], on_conflict="release_id,chunk_key")
        .execute()
    )


__all__ = ["call_claude_api", "call_kanon2_api", "index_chunk"]
