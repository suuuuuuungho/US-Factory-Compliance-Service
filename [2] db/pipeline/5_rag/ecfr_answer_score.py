"""Score one applicability-criteria answer against an eval case (SUU-146).

Four metrics, defined in ``[1] docs/3) rag/4_rag 답변 품질 개선 과정.md`` §2:
subpart hit, citation recall and citation groundedness are $0 rules; the
criteria score is a 0/1/2 judgement by an LLM judge against the EPA ``notes``.
This module only builds the judge request and parses its reply; calling the
API is the runner's job (SUU-147).
"""

from __future__ import annotations

import json
import re
from typing import Any

from ecfr_eval import citation_section_key

JUDGE_MODEL = "gpt-5-mini"
MAX_COMPLETION_TOKENS = 2000  # gpt-5 계열은 추론 토큰이 출력에 포함된다

JUDGE_SYSTEM = (
    "You are an expert judge on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP). "
    "You get a factory's question, OUR ANSWER (candidate subparts, the criteria that decide applicability, "
    "and the sections cited for each criterion), and EPA NOTES: the reasoning the EPA actually gave in its "
    "applicability determination letter. "
    "Judge ONE thing only: are the key reasons in the EPA NOTES captured by the criteria in OUR ANSWER? "
    "Do not penalize the answer for not stating a final conclusion (applies / does not apply); it is not supposed to. "
    "Scale: 2 = all key reasons in the notes are present in the criteria; "
    "1 = some are present; "
    "0 = none are present or the criteria contradict the notes. "
    'Reply with one line of JSON only: {"score": N, "reason": "..."}.'
)

_SCORE_RE = re.compile(r"score\D*(-?\d+)", re.I)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def _answer_sections(answer: dict[str, Any]) -> list[str]:
    """답에 나온 인용을 조문 단위로, 등장 순서대로, 중복 없이."""
    keys: list[str] = []
    for cand in answer.get("candidates", []):
        for crit in cand.get("criteria", []):
            for citation in crit.get("citations", []):
                key = citation_section_key(citation)
                if key not in keys:
                    keys.append(key)
    return keys


def score_subpart(answer: dict[str, Any], case: dict[str, Any]) -> int:
    """1 if the case's primary gold subpart is one of the answer's candidates."""
    candidates = {c.get("subpart") for c in answer.get("candidates", [])}
    return int(case["gold_subparts"][0] in candidates)


def score_citation_recall(answer: dict[str, Any], case: dict[str, Any]) -> float:
    """Share of gold sections (paragraph numbers dropped) cited anywhere in the answer."""
    gold = {citation_section_key(c) for c in case["gold_citations"]}
    cited = set(_answer_sections(answer))
    return len(gold & cited) / len(gold) if gold else 0.0


def score_citation_grounded(answer: dict[str, Any], given_section_keys: list[str]) -> tuple[float, list[str]]:
    """Share of the answer's cited sections that were among the given sections, plus the ones outside."""
    cited = _answer_sections(answer)
    if not cited:
        return 0.0, []
    given = set(given_section_keys)
    outside = [k for k in cited if k not in given]
    return (len(cited) - len(outside)) / len(cited), outside


def build_judge_request(answer: dict[str, Any], case: dict[str, Any], *, model: str = JUDGE_MODEL) -> dict[str, Any]:
    """Chat-completions request asking the judge to score the answer's criteria against the EPA notes."""
    user = (
        f"QUESTION:\n{case['question']}\n\n"
        f"OUR ANSWER (JSON):\n{json.dumps(answer, ensure_ascii=False, indent=2)}\n\n"
        f"EPA NOTES:\n{case['notes']}"
    )
    return {
        "model": model,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "messages": [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}],
    }


def parse_judge(text: str) -> int:
    """Read the 0/1/2 score from the judge's reply. Anything else is a ValueError."""
    body = _FENCE_RE.sub("", text.strip())
    score: Any = None
    try:
        score = json.loads(body).get("score")
    except (json.JSONDecodeError, AttributeError):
        match = _SCORE_RE.search(body)
        if match:
            score = int(match.group(1))
    if score not in (0, 1, 2):
        raise ValueError(f"judge score must be 0, 1 or 2: {text!r}")
    return int(score)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean of the four metrics over cases, plus the ids of cases that failed."""
    n = len(rows)
    mean = lambda key: sum(r[key] for r in rows) / n if n else 0.0  # noqa: E731
    failed = [r["case_id"] for r in rows if r["subpart"] == 0 or r["judge"] == 0 or r["citation_grounded"] < 1]
    return {
        "n": n,
        "subpart": mean("subpart"),
        "citation_recall": mean("citation_recall"),
        "citation_grounded": mean("citation_grounded"),
        "judge": mean("judge"),
        "failed": failed,
    }


__all__ = [
    "JUDGE_MODEL", "JUDGE_SYSTEM", "MAX_COMPLETION_TOKENS",
    "aggregate", "build_judge_request", "parse_judge",
    "score_citation_grounded", "score_citation_recall", "score_subpart",
]
