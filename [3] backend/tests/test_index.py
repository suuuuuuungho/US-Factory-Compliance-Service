"""SUU-156: 서버가 켜질 때 청크·BM25 색인을 한 번만 메모리에 올린다.
SUU-166: 임베딩은 안 내려받고, 벡터 검색은 Supabase RPC match_rag_chunk(pgvector)에 맡긴다.
"""
import re
from pathlib import Path
from types import SimpleNamespace

from app.index import load_index

MIGRATION = Path(__file__).parents[2] / "[2] db" / "migrations" / "SUU-166_match_rag_chunk.sql"


class FakeSupabase:
    """client.table("rag_chunk").select(...).eq(...).eq(...).order(...).range(a, b).execute().data
    + client.rpc("match_rag_chunk", params).execute().data 흉내."""

    def __init__(self, rows, matches=()):
        self.rows, self.matches = rows, list(matches)
        self.calls, self.rpc_calls, self.columns = 0, [], None

    def table(self, name):
        assert name == "rag_chunk"
        self._mode = "table"
        return self

    def select(self, columns):
        self.columns = columns
        return self

    def eq(self, *_):
        return self

    def order(self, *_):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def rpc(self, name, params):
        assert name == "match_rag_chunk"
        self._mode = "rpc"
        self.rpc_calls.append(params)
        return self

    def execute(self):
        if self._mode == "rpc":
            return SimpleNamespace(data=self.matches)
        self.calls += 1
        start, end = self._range
        return SimpleNamespace(data=self.rows[start:end + 1])


ROWS = [
    {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0", "node_key": "ecfr/40/63/subpart-PPPP/section-63.4481",
     "context_text": "Subpart PPPP plastic parts", "chunk_text": "solvent welding is coating"},
    {"chunk_key": "ecfr/40/63/subpart-M/section-63.320/0", "node_key": "ecfr/40/63/subpart-M/section-63.320",
     "context_text": "Subpart M dry cleaning", "chunk_text": "perchloroethylene machines"},
    # BM25는 문서 2개면 점수가 0이 되어 결과가 비니까 3개 이상 둔다
    {"chunk_key": "ecfr/40/63/subpart-A/section-63.1/0", "node_key": "ecfr/40/63/subpart-A/section-63.1",
     "context_text": "Subpart A general provisions", "chunk_text": "applicability of this part"},
]


def test_load_index_reads_supabase_once_per_release():
    client = FakeSupabase(ROWS)
    first = load_index(client, "rel-1")
    second = load_index(client, "rel-1")
    assert client.calls == 1
    assert first is second


def test_index_has_chunks_without_embedding_keyword_search_and_release_id():
    client = FakeSupabase(ROWS)
    index = load_index(client, "rel-2")
    assert index.release_id == "rel-2"
    assert [c["chunk_key"] for c in index.chunks] == [r["chunk_key"] for r in ROWS]
    # 임베딩은 143MB라 안 내려받는다. 벡터 검색은 DB(pgvector)가 한다
    assert "embedding" not in client.columns
    assert all("embedding" not in c for c in index.chunks)
    hits = index.keyword("solvent welding", 5)
    assert hits[0]["chunk_key"] == ROWS[0]["chunk_key"]


def test_index_vector_calls_match_rag_chunk_rpc_and_returns_scored_chunks():
    matches = [{"chunk_key": ROWS[1]["chunk_key"], "score": 0.9}, {"chunk_key": ROWS[0]["chunk_key"], "score": 0.8}]
    client = FakeSupabase(ROWS, matches)
    index = load_index(client, "rel-3")

    hits = index.vector([0.1, 0.2], 2)
    assert client.rpc_calls == [{"query_embedding": [0.1, 0.2], "p_release_id": "rel-3", "k": 2}]
    # RPC는 chunk_key·score만 준다. 메모리 청크(본문 포함)에 score를 붙여 돌려준다
    assert hits == [{**ROWS[1], "score": 0.9}, {**ROWS[0], "score": 0.8}]


def test_migration_creates_match_rag_chunk_with_cosine_and_filters():
    sql = " ".join(MIGRATION.read_text(encoding="utf-8").split()).lower()
    assert re.search(r"create (or replace )?function match_rag_chunk\s*\(", sql)
    assert "<=>" in sql  # pgvector 코사인 거리
    assert "release_id = p_release_id" in sql
    assert "index_status = 'embedded'" in sql
    assert "limit k" in sql
