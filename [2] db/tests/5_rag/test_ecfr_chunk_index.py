"""SUU-75: 청크 하나를 컨텍스트 모델·Kanon 2(임베딩) API로 실제로 색인해
rag_chunk 한 행에 저장한다.

SUU-86: 컨텍스트 프롬프트에 넣는 Subpart 이름은 호출자가 subpart_name으로
명시해서 넘긴다. 청크가 속한 조문(section) 노드의 heading을 대신 쓰면 안 된다.

SUU-89: 컨텍스트 생성 모델을 Claude Haiku 4.5에서 OpenAI gpt-4o-mini로 바꾼다.
주입 인자 이름은 call_context.

실제 네트워크 호출은 하지 않는다 — call_context/call_kanon2를 가짜로 주입해서
호출 순서·인자·저장된 행만 확인한다. 실제 호출 함수(기본값)는 이 티켓에서
실행해보지 않는다(사람이 다음 POC 티켓에서 직접 실행).
"""
from ecfr_chunk_index import index_chunk

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
NODE = {
    "release_id": RELEASE_ID,
    "node_key": "40/63/subpart-XXXXXX/section-63.11514",
    "heading": "Section 63.11514",
}
CHUNK = {
    "chunk_key": "ecfr/40/63/subpart-XXXXXX/section-63.11514/0",
    "dataset": "ecfr",
    "doc_key": "40/63",
    "node_key": "40/63/subpart-XXXXXX/section-63.11514",
    "block_from": 1,
    "block_to": 3,
    "hierarchy_path": "Title 40 > Part 63 > Subpart XXXXXX > 63.11514",
    "heading": "Section 63.11514",
    "citation": "40 CFR 63.11514(a)",
    "source_locator": "//section[63.11514]",
    "chunk_text": "(a) You are subject to this subpart if you own or operate an affected source.",
}
DOC_TEXT = "Subpart XXXXXX full document text used as the cached system prompt."
CONTEXT_TEXT = "This chunk is from Subpart XXXXXX, covering metal fabrication area sources."
EMBEDDING = [0.1] * 1792
SUBPART_NAME = "Subpart XXXXXX—National Emission Standards for Hazardous Air Pollutants for Nine Metal Fabrication and Finishing Source Categories"


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def execute(self):
        return _Result(self._rows)


class FakeClient:
    """supabase-py의 .table(name).upsert(rows, on_conflict=...).execute() 모양을 흉내낸다."""

    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def upsert(self, rows, on_conflict=None):
        rows_list = rows if isinstance(rows, list) else [rows]
        self._store.setdefault(self._name, []).extend(dict(row) for row in rows_list)
        return _Query(list(rows_list))


def test_calls_context_then_kanon2_with_context_chained_into_embedding_request():
    client = FakeClient()
    calls = []

    def call_context(request):
        calls.append(("context", request))
        return CONTEXT_TEXT

    def call_kanon2(request):
        calls.append(("kanon2", request))
        return EMBEDDING

    index_chunk(
        NODE, CHUNK, DOC_TEXT, subpart_name=SUBPART_NAME,
        client=client, call_context=call_context, call_kanon2=call_kanon2,
    )

    assert [name for name, _ in calls] == ["context", "kanon2"]
    context_request = calls[0][1]
    assert context_request["system"][0]["text"] == DOC_TEXT
    assert CHUNK["chunk_text"] in context_request["messages"][0]["content"]
    kanon2_request = calls[1][1]
    assert kanon2_request["texts"] == [f"{CONTEXT_TEXT}\n\n{CHUNK['chunk_text']}"]


def test_saved_row_has_context_embedding_hash_and_embedded_status():
    client = FakeClient()

    index_chunk(
        NODE, CHUNK, DOC_TEXT, subpart_name=SUBPART_NAME,
        client=client,
        call_context=lambda request: CONTEXT_TEXT,
        call_kanon2=lambda request: EMBEDDING,
    )

    assert len(client.store["rag_chunk"]) == 1
    row = client.store["rag_chunk"][0]
    assert row["release_id"] == RELEASE_ID
    assert row["chunk_key"] == CHUNK["chunk_key"]
    assert row["chunk_text"] == CHUNK["chunk_text"]
    assert row["context_text"] == CONTEXT_TEXT
    assert row["embedding"] == EMBEDDING
    assert row["content_hash"]
    assert row["index_status"] == "embedded"


def _context_prompt(**kwargs):
    requests = []

    def call_context(request):
        requests.append(request)
        return CONTEXT_TEXT

    index_chunk(
        NODE, CHUNK, DOC_TEXT, **kwargs,
        client=FakeClient(), call_context=call_context, call_kanon2=lambda request: EMBEDDING,
    )
    return requests[0]["messages"][0]["content"]


def test_index_chunk_uses_given_subpart_name_not_section_heading():
    prompt = _context_prompt(subpart_name=SUBPART_NAME)

    assert f"This chunk belongs to {SUBPART_NAME}." in prompt
    assert f"This chunk belongs to {NODE['heading']}." not in prompt


def test_index_chunk_with_none_subpart_name_omits_belongs_line():
    prompt = _context_prompt(subpart_name=None)

    assert "This chunk belongs to" not in prompt


def test_index_chunk_requires_subpart_name_keyword():
    import pytest

    with pytest.raises(TypeError):
        index_chunk(
            NODE, CHUNK, DOC_TEXT,
            client=FakeClient(),
            call_context=lambda request: CONTEXT_TEXT,
            call_kanon2=lambda request: EMBEDDING,
        )


def test_uses_the_real_api_callers_by_default():
    import ecfr_chunk_index

    assert ecfr_chunk_index.index_chunk.__kwdefaults__["call_context"].__name__ == "call_openai_api"
    assert ecfr_chunk_index.index_chunk.__kwdefaults__["call_kanon2"].__name__ == "call_kanon2_api"


class _FakeOpenAI:
    """openai.OpenAI의 .chat.completions.create(**kwargs) 모양만 흉내낸다."""

    def __init__(self):
        self.kwargs = None
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": CONTEXT_TEXT})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def test_call_openai_api_sends_doc_as_system_message_and_returns_text():
    from ecfr_chunk_index import call_openai_api
    from ecfr_context import build_context_request

    fake = _FakeOpenAI()
    request = build_context_request(DOC_TEXT, CHUNK["chunk_text"], subpart_name=SUBPART_NAME)

    text = call_openai_api(request, client=fake)

    assert text == CONTEXT_TEXT
    assert fake.kwargs["model"] == "gpt-4o-mini"
    messages = fake.kwargs["messages"]
    assert messages[0] == {"role": "system", "content": DOC_TEXT}
    assert messages[1:] == request["messages"]
    assert "cache_control" not in str(fake.kwargs)


def test_no_claude_left_in_pipeline_or_requirements():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    files = list((repo / "[2] db" / "pipeline" / "5_rag").glob("*.py")) + [repo / "requirements.txt"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "claude-haiku-4-5" not in text, path
        assert "ANTHROPIC_API_KEY" not in text, path
        assert "anthropic" not in text.lower(), path
