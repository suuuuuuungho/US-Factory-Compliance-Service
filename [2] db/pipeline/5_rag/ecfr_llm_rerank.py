"""Rerank the top sections of a search with an LLM (SUU-136).

SUU-135 measured this on saved hybrid+rules rankings: gpt-5-mini lifts
nDCG@10 0.631 -> 0.692 by reordering only the top ``LLM_TOP_N`` sections.
The LLM sees the question plus the first ``HEAD_CHARS`` characters of each
section's first chunk (context + text) and answers with candidate numbers.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable

LLM_TOP_N = 20
HEAD_CHARS = 3000
LLM_MODEL = "gpt-5-mini"
MAX_COMPLETION_TOKENS = 4000  # gpt-5 계열은 추론 토큰이 출력에 포함된다

SYSTEM = (
    "You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP). "
    "A factory describes its situation and asks which rule applies. You get candidate sections, each with a key and the start of its text. "
    "Rank ALL candidates from most to least relevant for answering the question. "
    "Most relevant = the section the EPA would cite to answer (applicability, definitions, or the specific requirement asked about). "
    "Reply with only a JSON array of the candidate numbers, most relevant first, containing every number exactly once."
)


def section_head(chunk: dict[str, Any] | None) -> str:
    """Text the LLM reads for one section: its first chunk's context + text, cut to ``HEAD_CHARS``."""
    if not chunk:
        return ""
    return f"{chunk.get('context_text') or ''}\n{chunk['chunk_text']}"[:HEAD_CHARS]


def build_llm_rerank_prompt(question: str, sections: list[dict[str, Any]]) -> str:
    parts = [f"QUESTION:\n{question}\n", f"CANDIDATES ({len(sections)}):"]
    for i, s in enumerate(sections, 1):
        parts.append(f"\n[{i}] key: {s['section_key']} (Subpart {s['subpart']})\n{s.get('text', '')[:HEAD_CHARS]}")
    parts.append("\nReturn a JSON array of all candidate numbers, most relevant first.")
    return "\n".join(parts)


def parse_ranking(text: str, keys: list[str]) -> list[str]:
    """답의 후보 번호(1부터) 순서대로 키를 뽑는다. 번호가 없으면 키 문자열 순서로. 빠진 키는 원래 순서로 뒤에 붙인다."""
    ordered: list[str] = []
    for n in re.findall(r"\d+", text):
        i = int(n) - 1
        if 0 <= i < len(keys) and keys[i] not in ordered:
            ordered.append(keys[i])
    if not ordered:
        found = [(m.start(), key) for key in keys if (m := re.search(re.escape(key) + r"(?![\w.])", text))]
        ordered = [k for _, k in sorted(found)]
    return ordered + [k for k in keys if k not in ordered]


def llm_rerank_sections(
    question: str,
    sections: list[dict[str, Any]],
    ask: Callable[[str], str],
    *,
    texts: dict[str, str],
) -> list[dict[str, Any]]:
    """Reorder the top ``LLM_TOP_N`` sections by ``ask(prompt)``; sections after that keep their order."""
    head, tail = sections[:LLM_TOP_N], sections[LLM_TOP_N:]
    if not head:
        return list(sections)
    by_key = {s["section_key"]: s for s in head}
    prompt = build_llm_rerank_prompt(question, [{**s, "text": texts.get(s["section_key"], "")} for s in head])
    order = parse_ranking(ask(prompt), list(by_key))
    return [by_key[k] for k in order] + tail


def call_openai_rerank_api(prompt: str, *, model: str = LLM_MODEL, client: Any = None) -> dict[str, Any]:
    """Ask OpenAI for the ranking. Returns ``text`` and token counts."""
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    )
    return {
        "text": response.choices[0].message.content or "",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


__all__ = [
    "HEAD_CHARS", "LLM_MODEL", "LLM_TOP_N", "SYSTEM",
    "build_llm_rerank_prompt", "call_openai_rerank_api", "llm_rerank_sections", "parse_ranking", "section_head",
]
