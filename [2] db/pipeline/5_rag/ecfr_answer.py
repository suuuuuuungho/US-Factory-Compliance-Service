"""Turn the top sections of a search into a criteria table (SUU-138).

The service promises candidate subparts, the criteria that decide whether each
applies, and the sections behind them — never a final applicability verdict
(``[1] docs/1) project/1_project.md``). The answer is JSON so subparts and
citations can be scored against the EPA gold set without another LLM call.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ecfr_eval import citation_section_key

SECTION_CHARS = 12000  # 조문 하나당 LLM에 주는 최대 글자 수 (≈ 3k 토큰)
ANSWER_MODEL = "gpt-5-mini"
MAX_COMPLETION_TOKENS = 8000

SYSTEM = (
    "You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP). "
    "A factory describes its situation. Using ONLY the regulation sections provided, list the candidate subparts "
    "that may apply and, for each, the criteria that decide whether it applies, each tied to the section that states it. "
    "Do NOT decide whether the subpart applies; the factory decides after checking the criteria. "
    "Keep it short: only criteria that matter for THIS factory's situation, at most 6 per subpart, "
    "at most 4 things to check per subpart; skip exemptions and options that clearly do not concern this factory. "
    "Cite only sections given to you, as '63.NNNN' or '63.NNNN(x)'. "
    "Reply with only JSON: {\"candidates\": [{\"subpart\": \"PPPP\", \"name\": \"short subpart name\", "
    "\"criteria\": [{\"citation\": \"63.4481(a)\", \"check\": \"what the factory must check, in one sentence\"}], "
    "\"you_should_check\": [\"facts the factory should confirm\"]}]}"
)


def build_answer_prompt(question: str, sections: list[dict[str, Any]]) -> str:
    parts = [f"FACTORY SITUATION:\n{question}\n", f"REGULATION SECTIONS ({len(sections)}):"]
    for s in sections:
        parts.append(f"\n=== {s['section_key']} (Subpart {s['subpart']}) ===\n{s.get('text', '')[:SECTION_CHARS]}")
    parts.append("\nReturn the JSON criteria table. Do NOT state whether any subpart applies.")
    return "\n".join(parts)


def parse_answer(text: str) -> dict[str, Any]:
    """JSON 답을 읽는다(```json 펜스·앞뒤 잡음 허용). 못 읽으면 후보 없음."""
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            answer = json.loads(match.group())
            if isinstance(answer.get("candidates"), list):
                return answer
        except json.JSONDecodeError:
            pass
    return {"candidates": []}


def _section_of(citation: str) -> str | None:
    try:
        return citation_section_key(citation)
    except ValueError:
        return None


def score_answer(answer: dict[str, Any], *, gold_subparts: list[str], gold_citations: list[str], context_keys: list[str]) -> dict[str, Any]:
    """$0 채점: 정답 Subpart가 후보에 있나, 정답 조문을 기준에서 인용했나, 인용이 준 조문 안에 있나."""
    candidates = answer.get("candidates", [])
    cited = [_section_of(str(c.get("citation", ""))) for cand in candidates for c in cand.get("criteria", [])]
    gold = {citation_section_key(g) for g in gold_citations}
    return {
        "subpart_hit": any(cand.get("subpart") in gold_subparts for cand in candidates),
        "citation_recall": len(gold & set(cited)) / len(gold) if gold else 0.0,
        "citation_grounded": sum(c in context_keys for c in cited) / len(cited) if cited else 0.0,
        "n_criteria": len(cited),
    }


def call_openai_answer_api(prompt: str, *, model: str = ANSWER_MODEL, client: Any = None) -> dict[str, Any]:
    """Ask OpenAI for the criteria table. Returns ``text`` and token counts."""
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        response_format={"type": "json_object"},  # 1차 102건에서 8건이 JSON을 살짝 틀리게 써서 켰다
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    )
    return {
        "text": response.choices[0].message.content or "",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


__all__ = ["ANSWER_MODEL", "SECTION_CHARS", "SYSTEM", "build_answer_prompt", "call_openai_answer_api", "parse_answer", "score_answer"]
