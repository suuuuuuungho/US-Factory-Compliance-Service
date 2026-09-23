"""SUU-257: 공장 설명 → 유사 판정서한 상위 5건.

서한 청크(SUU-256, rag_chunk release LETTER_RELEASE_ID, chunk_key = dashboard/{source_key}/{n})를
/ask 와 같은 체인(벡터 + BM25 → RRF → Kanon 리랭커)으로 찾되, eCFR 전용 규칙·LLM 은 쓰지 않는다.
서한마다 최고 리랭커 점수 하나만 남기고 MIN_SCORE 미만은 버린다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from ecfr_eval import build_query_embedding_request
from ecfr_index_run import rank_chunks_by_similarity
from ecfr_search import rrf_merge

from app.answer import CHUNK_TOP_K
from app.index import Index

LETTER_RELEASE_ID = "5cc370d0-c513-4376-981f-2d910b39ae6b"  # SUU-256 이 서한 청크를 넣는 adi release
TOP_N = 5
RERANK_K = 20
# 리랭커 점수(0~1) 기준선. 2026-09-22 실제 128건으로 잼: 같은 사례 0.71~0.93, 같은 업종 0.044~0.14, 무관 ≤0.002.
# 같은 업종 사례(말투 따라 0.044~0.053 오르내림)는 살리고 무관은 거르는 값. 자세한 표는 [5] tickets/3)Backend/1_feat/SUU-257.md
MIN_SCORE = 0.03

META_PATH = Path(__file__).resolve().parents[2] / "[4]frontend" / "public" / "decision-letters.json"


def source_key_of_chunk(chunk: dict) -> str:
    return chunk["chunk_key"].split("/")[1]


def load_letter_meta(path: Path = META_PATH) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return {l["source_key"]: l for l in json.load(f)["letters"]}


def similar_letters(
    description: str,
    *,
    index: Index,
    embed: Callable[[dict], list[float]],
    rerank: Callable[[str, list[dict]], list[float]],
    meta: dict[str, dict],
) -> list[dict]:
    query_embedding = embed(build_query_embedding_request(description))
    if index.vector is not None:
        vector_chunks = index.vector(query_embedding, CHUNK_TOP_K)
    else:
        vector_chunks = rank_chunks_by_similarity(query_embedding, index.chunks, top_k=CHUNK_TOP_K)
    by_key = {c["chunk_key"]: c for c in index.chunks}
    keyword_chunks = [by_key[h["chunk_key"]] for h in index.keyword(description, CHUNK_TOP_K) if h["chunk_key"] in by_key]
    ranked = rrf_merge([vector_chunks, keyword_chunks])[:RERANK_K]
    if not ranked:
        return []
    scores = rerank(description, ranked)

    best: dict[str, tuple[float, dict]] = {}  # source_key → (최고 score, 그 청크)
    for chunk, score in zip(ranked, scores):
        key = source_key_of_chunk(chunk)
        if key not in best or score > best[key][0]:
            best[key] = (score, chunk)
    kept = sorted(((k, s, c) for k, (s, c) in best.items() if s >= MIN_SCORE and k in meta), key=lambda t: (-t[1], t[0]))
    return [{**meta[k], "score": s, "snippet": c["chunk_text"]} for k, s, c in kept[:TOP_N]]
