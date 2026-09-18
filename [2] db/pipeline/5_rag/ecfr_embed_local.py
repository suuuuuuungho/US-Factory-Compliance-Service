"""Embed eCFR chunks and questions with a local open-source model (SUU-133).

Used only by the evaluation to build a no-context baseline; the index in
``rag_chunk`` keeps its Kanon 2 embeddings. torch and the model are imported
lazily so this module is importable without them.
"""

from __future__ import annotations

import math
from typing import Any, Callable

MODELS = {"bge": "BAAI/bge-m3"}
BATCH_SIZE = 16
MAX_LENGTH = 1024
Encoder = Callable[[list[str]], list[list[float]]]


def chunk_document_text(chunk: dict[str, Any], *, with_context: bool) -> str:
    """Text to embed for one chunk: ``context + chunk`` (like the index) or chunk only."""
    if with_context and chunk.get("context_text"):
        return f"{chunk['context_text']}\n\n{chunk['chunk_text']}"
    return chunk["chunk_text"]


def build_local_embedder(encode: Encoder, *, batch_size: int = BATCH_SIZE):
    """Wrap a batch encoder into ``embed(texts) -> unit vectors``."""

    def embed(texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            for v in encode(texts[start : start + batch_size]):
                norm = math.sqrt(sum(x * x for x in v)) or 1.0
                vectors.append([x / norm for x in v])
        return vectors

    return embed


def load_encoder(name: str, *, device: str = "cuda") -> Encoder:
    """Load the model once and return a batch encoder (raw vectors)."""
    if name not in MODELS:
        raise ValueError(f"unknown embedder {name!r}; expected one of {sorted(MODELS)}")
    import torch
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODELS[name], device=device, model_kwargs={"dtype": torch.float16})
    model.max_seq_length = MAX_LENGTH
    return lambda texts: model.encode(texts, batch_size=len(texts), convert_to_numpy=True).tolist()


__all__ = ["MODELS", "build_local_embedder", "chunk_document_text", "load_encoder"]
