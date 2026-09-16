"""SUU-75: 청크 하나를 Claude(컨텍스트)·Kanon 2(임베딩) API로 실제로 색인해
rag_chunk 한 행에 저장한다.

실제 네트워크 호출은 하지 않는다 — call_claude/call_kanon2를 가짜로 주입해서
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
DOC_TEXT = "Subpart XXXXXX full document text used for Claude's cached system prompt."
CONTEXT_TEXT = "This chunk is from Subpart XXXXXX, covering metal fabrication area sources."
EMBEDDING = [0.1] * 1792


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


def test_calls_claude_then_kanon2_with_context_chained_into_embedding_request():
    client = FakeClient()
    calls = []

    def call_claude(request):
        calls.append(("claude", request))
        return CONTEXT_TEXT

    def call_kanon2(request):
        calls.append(("kanon2", request))
        return EMBEDDING

    index_chunk(NODE, CHUNK, DOC_TEXT, client=client, call_claude=call_claude, call_kanon2=call_kanon2)

    assert [name for name, _ in calls] == ["claude", "kanon2"]
    claude_request = calls[0][1]
    assert claude_request["system"][0]["text"] == DOC_TEXT
    assert CHUNK["chunk_text"] in claude_request["messages"][0]["content"]
    kanon2_request = calls[1][1]
    assert kanon2_request["texts"] == [f"{CONTEXT_TEXT}\n\n{CHUNK['chunk_text']}"]


def test_saved_row_has_context_embedding_hash_and_embedded_status():
    client = FakeClient()

    index_chunk(
        NODE, CHUNK, DOC_TEXT,
        client=client,
        call_claude=lambda request: CONTEXT_TEXT,
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


def test_uses_the_real_api_callers_by_default():
    import ecfr_chunk_index

    assert ecfr_chunk_index.index_chunk.__kwdefaults__["call_claude"].__name__ == "call_claude_api"
    assert ecfr_chunk_index.index_chunk.__kwdefaults__["call_kanon2"].__name__ == "call_kanon2_api"
