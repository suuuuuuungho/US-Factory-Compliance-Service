"""SUU-157: 질문 하나 → 검색(hybrid + 규칙 + LLM 리랭크) → 상위 10 조문 전문 → 판정 기준표 JSON.

외부 API(embed·rerank·llm·chat)는 전부 함수 인자로 받는다. 색인은 SUU-156의 Index.
"""
from __future__ import annotations

import time
from typing import Callable

from ecfr_answer import build_answer_request, parse_answer
from ecfr_search import search_sections

from app.index import Index

TOP_N = 10                                   # SUU-152·154 기준 조합
CHUNK_TOP_K = 150                            # run_eval.py: 리랭크 쓸 때 150
PRICE_PER_M = {"gpt-5-mini": (0.25, 2.00)}   # [6] rag/eval/llm_rerank.py 와 같음 (USD / 1M 토큰: prompt, completion)


def _piece_order(chunk_key: str) -> tuple[int, int]:
    """본문 /0, /0-1, /0-2 … 먼저(숫자 순), 표 /1, /2 … 뒤. run_answer.py 와 같음."""
    piece = chunk_key.rsplit("/", 1)[1]
    if piece.startswith("0"):
        return (0, int(piece.split("-")[1]) if "-" in piece else 0)
    return (1, int(piece))


def section_text(index: Index, section: dict) -> str:
    """조문 전문. 색인에 청크 본문이 다 있으니 메모리에서 조각을 이어 붙인다."""
    prefix = section["chunk_key"].rsplit("/", 1)[0] + "/"
    rows = [c for c in index.chunks if c["chunk_key"].startswith(prefix)]
    return "\n\n".join(r["chunk_text"] for r in sorted(rows, key=lambda r: _piece_order(r["chunk_key"])))


def answer_question(
    question: str,
    *,
    index: Index,
    embed: Callable[[dict], list[float]],
    rerank: Callable[[str, list[dict]], list[float]],
    llm: Callable[[str], dict],
    chat: Callable[[dict], dict],
) -> dict:
    t0 = time.perf_counter()
    tokens = {"prompt": 0, "completion": 0}

    def count(r: dict) -> str:
        tokens["prompt"] += r["prompt_tokens"]
        tokens["completion"] += r["completion_tokens"]
        return r["text"]

    found = search_sections(
        question,
        embed=embed,
        chunks=index.chunks,
        keyword=index.keyword,
        rerank=rerank,
        top_k=TOP_N,
        chunk_top_k=CHUNK_TOP_K,
        rules=True,
        llm=lambda prompt: count(llm(prompt)),
    )
    request = build_answer_request(question, [{**s, "text": section_text(index, s)} for s in found])
    text = count(chat(request))
    try:
        answer, issues = parse_answer(text, [s["section_key"] for s in found])
    except ValueError as e:
        answer, issues = None, [f"parse error: {e}"]

    price_in, price_out = PRICE_PER_M[request["model"]]
    return {
        "answer": answer,
        "sections": [{"section_key": s["section_key"], "subpart": s["subpart"]} for s in found],
        "issues": issues,
        "tokens": tokens,
        "cost_usd": tokens["prompt"] / 1e6 * price_in + tokens["completion"] / 1e6 * price_out,
        "ms": int((time.perf_counter() - t0) * 1000),
    }
