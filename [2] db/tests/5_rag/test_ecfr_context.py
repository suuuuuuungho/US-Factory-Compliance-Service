"""SUU-71: 청크 컨텍스트 생성을 위해 Claude에 보낼 요청(문서 전체+청크+지시문)을
조립한다. 실제 Claude API 호출은 하지 않는다(네트워크 필요, 다음 티켓 범위) —
"무엇을 보내는지"만 확인한다.
"""
from ecfr_context import build_context_request

DOC_TEXT = "Subpart G text ... covers surface coating operations ..."
CHUNK_TEXT = "(a) The owner or operator shall comply with the emission limits in Table 1."


def test_system_prompt_contains_full_document_with_cache_control():
    request = build_context_request(DOC_TEXT, CHUNK_TEXT)

    system_blocks = request["system"]
    assert any(
        block["text"] == DOC_TEXT and block["cache_control"] == {"type": "ephemeral"}
        for block in system_blocks
    )


def test_user_message_contains_the_chunk_text():
    request = build_context_request(DOC_TEXT, CHUNK_TEXT)

    messages = request["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert CHUNK_TEXT in messages[0]["content"]


def test_returns_the_prompt_version_for_storage():
    result = build_context_request(DOC_TEXT, CHUNK_TEXT)

    assert result["prompt_version"] == "ctx_prompt_v1"


def test_prompt_version_can_be_overridden():
    result = build_context_request(DOC_TEXT, CHUNK_TEXT, prompt_version="ctx_prompt_v2")

    assert result["prompt_version"] == "ctx_prompt_v2"


def test_instruction_tells_claude_not_to_invent_names():
    request = build_context_request(DOC_TEXT, CHUNK_TEXT)

    instruction = request["messages"][0]["content"]
    assert "invent" in instruction.lower()
    assert "name" in instruction.lower()


def test_instruction_states_the_real_subpart_name():
    request = build_context_request(DOC_TEXT, CHUNK_TEXT, subpart_name="Subpart XXXXXX")

    instruction = request["messages"][0]["content"]
    assert "Subpart XXXXXX" in instruction


def test_works_without_a_subpart_name():
    request = build_context_request(DOC_TEXT, CHUNK_TEXT)

    assert request["messages"][0]["role"] == "user"
    assert CHUNK_TEXT in request["messages"][0]["content"]
