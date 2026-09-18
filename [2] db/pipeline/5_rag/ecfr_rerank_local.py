"""Rerank eCFR chunks with a local open-source cross-encoder (SUU-131).

Same input as ``build_rerank_request`` (question, chunks) and same output as
the Kanon 2 API (one score per chunk, higher is better). torch and the model
libraries are imported lazily so this module is importable without them.
"""

from __future__ import annotations

from typing import Any, Callable

from ecfr_search import build_rerank_request

MODELS = {
    "bge": "BAAI/bge-reranker-v2-m3",
    "nemotron": "nvidia/llama-nemotron-rerank-1b-v2",
}
MAX_LENGTH = 512
BATCH_SIZE = {"bge": 64, "nemotron": 16}  # RTX 4070 8GB에서 잰 최적값
Scorer = Callable[[list[tuple[str, str]]], list[float]]


def rerank_pairs(question: str, chunks: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """(question, text) pairs using exactly the texts Kanon receives."""
    return [(question, text) for text in build_rerank_request(question, chunks)["texts"]]


def build_local_reranker(score_batch: Scorer, *, batch_size: int = 32):
    """Wrap a batch scorer into the ``rerank(question, chunks) -> scores`` shape."""

    def rerank(question: str, chunks: list[dict[str, Any]]) -> list[float]:
        pairs = rerank_pairs(question, chunks)
        scores: list[float] = []
        for start in range(0, len(pairs), batch_size):
            scores.extend(score_batch(pairs[start : start + batch_size]))
        return scores

    return rerank


def load_scorer(name: str, *, device: str = "cuda") -> Scorer:
    """Load the model once and return a batch scorer."""
    if name not in MODELS:
        raise ValueError(f"unknown reranker {name!r}; expected one of {sorted(MODELS)}")
    import torch

    if name == "bge":
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(MODELS[name], device=device, max_length=MAX_LENGTH, model_kwargs={"dtype": torch.float16})
        return lambda pairs: [float(s) for s in model.predict(pairs, batch_size=len(pairs))]

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODELS[name], trust_remote_code=True, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = (
        AutoModelForSequenceClassification.from_pretrained(MODELS[name], trust_remote_code=True, dtype=torch.bfloat16)
        .eval()
        .to(device)
    )

    def score(pairs: list[tuple[str, str]]) -> list[float]:
        texts = [f"question:{q} \n \n passage:{p}" for q, p in pairs]
        batch = tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=MAX_LENGTH).to(device)
        with torch.inference_mode():
            return model(**batch).logits.view(-1).float().cpu().tolist()

    return score


__all__ = ["MODELS", "build_local_reranker", "load_scorer", "rerank_pairs"]
