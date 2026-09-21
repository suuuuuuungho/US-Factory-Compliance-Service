"""SUU-159: /ask 한 번 = rag_answer_log 한 줄. insert가 깨져도 답은 그대로 나간다."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def answer_log_row(question: str, result: dict, release_id: str) -> dict:
    """id·created_at은 DB 기본값."""
    return {
        "release_id": release_id,
        "question": question,
        "answer": result["answer"],
        "sections": result["sections"],
        "issues": result["issues"],
        "prompt_tokens": result["tokens"]["prompt"],
        "completion_tokens": result["tokens"]["completion"],
        "cost_usd": result["cost_usd"],
        "ms": result["ms"],
    }


def save_answer_log(client, row: dict) -> None:
    """답보다 로그가 덜 중요하다. 실패는 기록만 하고 삼킨다."""
    try:
        client.table("rag_answer_log").insert(row).execute()
    except Exception:
        logger.exception("answer log insert failed")
