"""Turn the top retrieved sections into an applicability-criteria answer (SUU-147).

The LLM gets the factory's question plus the full text of the top sections and
returns the JSON defined in ``[1] docs/3) rag/4_rag 답변 품질 개선 과정.md`` §1:
candidate subparts, the criteria that decide applicability (each with citations
to the given sections only) and a checklist for the plant. No verdict.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ecfr_answer_score import normalize_subpart
from ecfr_eval import citation_section_key

ANSWER_MODEL = "gpt-5-mini"
MAX_COMPLETION_TOKENS = 10000  # gpt-5 계열은 추론 토큰이 출력에 포함된다. 6000이면 102건 중 3건이 빈 답(SUU-147)

ANSWER_SYSTEM = """You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP).
A factory describes its situation and asks which rule applies. You get the full text of the most relevant sections.
Build an APPLICABILITY CRITERIA TABLE as JSON with exactly this schema:

{"candidates": [{"subpart": "PPPP", "title": "<subpart name>", "criteria": [{"criterion": "<one sentence>", "citations": ["40 CFR 63.xxxx(a)"]}]}], "checklist": ["<fact the plant must verify>"]}

Rules:
- candidates: list EVERY subpart that could apply to this plant (1 to 4), including the general provisions Subpart A when its sections were given. Only subparts that appear in the given sections.
- subpart: the subpart code only ("A", "M", "PPPP"). Never "Subpart M", never a section number like "40 CFR 63.460".
- criterion: one sentence of the form "if ... then subject" / "if ... then not subject". It is the test, not the result.
- citations: only sections you were given, formatted "40 CFR 63.xxxx" with the paragraph, e.g. "40 CFR 63.4481(a)". At least one per criterion.
- checklist: concrete facts the plant must check about its own operation to apply the criteria.
- Do NOT give a verdict or conclusion on whether the rule applies. The plant decides; you give the criteria and where to look.
- No other fields. Output the JSON only, no prose."""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)
_SUBPART_CODE_RE = re.compile(r"[A-Z]{1,7}")
_TOP_KEYS = {"candidates", "checklist"}
_CANDIDATE_KEYS = {"subpart", "title", "criteria"}
_CRITERION_KEYS = {"criterion", "citations"}


def build_answer_request(question: str, sections: list[dict[str, Any]], *, model: str = ANSWER_MODEL) -> dict[str, Any]:
    """Chat-completions request: question + full text of each ``{section_key, subpart, text}``."""
    parts = [f"QUESTION:\n{question}\n", f"SECTIONS ({len(sections)}):"]
    for i, s in enumerate(sections, 1):
        parts.append(f"\n[{i}] {s['section_key']} (Subpart {s['subpart']})\n{s['text']}")
    return {
        "model": model,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "messages": [{"role": "system", "content": ANSWER_SYSTEM}, {"role": "user", "content": "\n".join(parts)}],
    }


def _nonempty_list(obj: dict, key: str, where: str) -> list:
    value = obj.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where}: '{key}' must be a non-empty list")
    return value


def _keep(obj: dict, allowed: set[str], where: str, issues: list[str]) -> dict:
    for key in list(obj):
        if key not in allowed:
            issues.append(f"unknown field: {where}.{key}")
    return {k: v for k, v in obj.items() if k in allowed}


def parse_answer(text: str, given_section_keys: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Parse the LLM reply into the answer schema.

    Missing required parts raise ``ValueError``. Unknown fields are dropped and
    noted in ``issues``; citations outside the given sections are kept (the
    groundedness score catches them) but noted too.
    """
    try:
        raw = json.loads(_FENCE_RE.sub("", text.strip()))
    except json.JSONDecodeError as e:
        raise ValueError(f"answer is not JSON: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError("answer must be a JSON object")
    issues: list[str] = []
    given = set(given_section_keys)

    answer = _keep(raw, _TOP_KEYS, "answer", issues)
    candidates = _nonempty_list(answer, "candidates", "answer")
    _nonempty_list(answer, "checklist", "answer")
    answer["candidates"] = []
    for ci, cand in enumerate(candidates):
        if not isinstance(cand, dict) or not isinstance(cand.get("subpart"), str):
            raise ValueError(f"candidates[{ci}]: 'subpart' must be a string")
        cand = _keep(cand, _CANDIDATE_KEYS, f"candidates[{ci}]", issues)
        code = normalize_subpart(cand["subpart"])
        if _SUBPART_CODE_RE.fullmatch(code):
            cand["subpart"] = code
        else:
            issues.append(f"candidates[{ci}].subpart is not a code: {cand['subpart']}")
        criteria = _nonempty_list(cand, "criteria", f"candidates[{ci}]")
        cand["criteria"] = []
        for ki, crit in enumerate(criteria):
            where = f"candidates[{ci}].criteria[{ki}]"
            if not isinstance(crit, dict) or not isinstance(crit.get("criterion"), str):
                raise ValueError(f"{where}: 'criterion' must be a string")
            crit = _keep(crit, _CRITERION_KEYS, where, issues)
            for citation in _nonempty_list(crit, "citations", where):
                try:
                    key = citation_section_key(str(citation))
                except ValueError:
                    issues.append(f"citation not a Part 63 section: {citation}")
                    continue
                if key not in given:
                    issues.append(f"citation outside given sections: {key} ({citation})")
            cand["criteria"].append(crit)
        answer["candidates"].append(cand)
    return answer, issues


def call_openai_chat(request: dict[str, Any], *, client: Any = None) -> dict[str, Any]:
    """Send a chat-completions request built here or by ``ecfr_answer_score``. Returns ``text`` and token counts."""
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(**request)
    return {
        "text": response.choices[0].message.content or "",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


__all__ = ["ANSWER_MODEL", "ANSWER_SYSTEM", "MAX_COMPLETION_TOKENS", "build_answer_request", "call_openai_chat", "parse_answer"]
