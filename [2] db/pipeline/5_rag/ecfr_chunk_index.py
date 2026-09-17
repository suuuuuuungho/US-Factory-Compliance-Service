"""Contextualize, embed, and persist one eCFR chunk."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from typing import Any

import requests
from openai import OpenAI

from ecfr_context import build_context_request
from ecfr_embed import build_embedding_request


def call_openai_api(request: dict[str, Any], *, client: Any = None) -> str:
    """Generate one chunk context with OpenAI."""
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [
        {"role": "system", "content": request["system"][0]["text"]},
        *request["messages"],
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=256,
        messages=messages,
    )
    return response.choices[0].message.content


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


def call_isaacus_rerank_api(request: dict[str, Any]) -> dict:
    """Rerank texts with Kanon 2 and restore the input order of scores."""
    response = requests.post(
        "https://api.isaacus.com/v1/rerankings",
        headers={"Authorization": f"Bearer {os.environ['ISAACUS_API_KEY']}"},
        json={"model": "kanon-2-reranker", **request},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    scores = [0.0] * len(request["texts"])
    for result in payload["results"]:
        scores[result["index"]] = result["score"]
    return {"scores": scores, "input_tokens": payload["usage"]["input_tokens"]}


def index_chunk(
    node: dict[str, Any],
    chunk: dict[str, Any],
    doc_text: str,
    *,
    subpart_name: str | None,
    client: Any,
    call_context: Callable[[dict[str, Any]], str] = call_openai_api,
    call_kanon2: Callable[[dict[str, Any]], list[float]] = call_kanon2_api,
) -> None:
    """Contextualize, embed, and upsert one chunk into ``rag_chunk``."""
    chunk_text = chunk["chunk_text"]
    context_text = call_context(
        build_context_request(doc_text, chunk_text, subpart_name=subpart_name)
    )
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


__all__ = [
    "call_isaacus_rerank_api",
    "call_openai_api",
    "call_kanon2_api",
    "index_chunk",
]
