"""SUU-73: 컨텍스트+청크 텍스트를 Kanon 2 Embedder에 보낼 요청을 조립한다.
실제 API 호출은 하지 않는다(네트워크 필요, 다음 티켓 범위) — "무엇을 보내는지"만
확인한다.
"""
from ecfr_embed import build_embedding_request

CONTEXT_TEXT = "This chunk is from Subpart XXXXXX, covering metal fabrication area sources."
CHUNK_TEXT = "(a) You are subject to this subpart if you own or operate an affected source."


def test_input_text_joins_context_and_chunk_with_blank_line():
    request = build_embedding_request(CONTEXT_TEXT, CHUNK_TEXT)

    assert request["texts"] == [f"{CONTEXT_TEXT}\n\n{CHUNK_TEXT}"]


def test_task_is_fixed_to_retrieval_document():
    request = build_embedding_request(CONTEXT_TEXT, CHUNK_TEXT)

    assert request["task"] == "retrieval/document"


def test_overflow_strategy_is_fixed_to_null():
    request = build_embedding_request(CONTEXT_TEXT, CHUNK_TEXT)

    assert request["overflow_strategy"] is None
