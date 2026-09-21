"""SUU-156: 서버가 켜질 때 청크·BM25 색인을 한 번만 메모리에 올린다."""
from types import SimpleNamespace

from app.index import load_index


class FakeSupabase:
    """client.table("rag_chunk").select(...).eq(...).eq(...).order(...).range(a, b).execute().data 흉내."""

    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def table(self, name):
        assert name == "rag_chunk"
        return self

    def select(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def order(self, *_):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        self.calls += 1
        start, end = self._range
        return SimpleNamespace(data=self.rows[start:end + 1])


ROWS = [
    {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0", "node_key": "ecfr/40/63/subpart-PPPP/section-63.4481",
     "embedding": "[0.1, 0.2]", "context_text": "Subpart PPPP plastic parts", "chunk_text": "solvent welding is coating"},
    {"chunk_key": "ecfr/40/63/subpart-M/section-63.320/0", "node_key": "ecfr/40/63/subpart-M/section-63.320",
     "embedding": [0.3, 0.4], "context_text": "Subpart M dry cleaning", "chunk_text": "perchloroethylene machines"},
]


def test_load_index_reads_supabase_once_per_release():
    client = FakeSupabase(ROWS)
    first = load_index(client, "rel-1")
    second = load_index(client, "rel-1")
    assert client.calls == 1
    assert first is second


def test_index_has_parsed_chunks_keyword_search_and_release_id():
    index = load_index(FakeSupabase(ROWS), "rel-2")
    assert index.release_id == "rel-2"
    assert [c["chunk_key"] for c in index.chunks] == [r["chunk_key"] for r in ROWS]
    assert index.chunks[0]["embedding"] == [0.1, 0.2]  # 문자열로 온 임베딩은 리스트로 바꿔 둔다
    assert index.chunks[1]["embedding"] == [0.3, 0.4]
    hits = index.keyword("solvent welding", 5)
    assert hits[0]["chunk_key"] == ROWS[0]["chunk_key"]
