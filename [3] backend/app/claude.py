"""OpenAI가 하던 두 단계(LLM 리랭크·최종 답)를 Claude로. 반환 모양은 call_openai_rerank_api / call_openai_chat 과 같다."""
from __future__ import annotations

import os
from typing import Any

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 16000


def _call(system: str, user: str) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS, system=system,
                                messages=[{"role": "user", "content": user}]) as stream:
        response = stream.get_final_message()
    return {
        "text": "".join(b.text for b in response.content if b.type == "text"),
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
    }


def call_claude_rerank_api(prompt: str) -> dict[str, Any]:
    from ecfr_llm_rerank import SYSTEM

    return _call(SYSTEM, prompt)


def call_claude_chat(request: dict[str, Any]) -> dict[str, Any]:
    """build_answer_request 가 만든 chat-completions 요청에서 system/user 본문만 꺼내 쓴다."""
    system, user = (m["content"] for m in request["messages"])
    return _call(system, user)
