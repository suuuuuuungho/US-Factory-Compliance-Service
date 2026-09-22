"""SUU-257: 공장 설명 → 유사 판정서한 상위 5건.

similar_letters(): 벡터 + BM25 → RRF → 리랭크(상위 20 청크) → source_key 로 묶기(서한마다 최고 score 1개)
→ MIN_SCORE 미만 제거 → 점수 내림차순 상위 5. 외부 API(embed·rerank)와 색인은 전부 가짜.
POST /letters/similar: {description} → {letters: [...]}. 빈 description 은 422.
"""
import importlib

import pytest
from fastapi.testclient import TestClient

from app import letters
from app.index import Index
from app.letters import similar_letters, source_key_of_chunk

# 서한 청크. SUU-256: chunk_key = dashboard/{source_key}/{n}, context_text 는 제목·시설명·Subpart 한 줄
def _chunk(source_key: str, n: int, text: str) -> dict:
    return {"chunk_key": f"dashboard/{source_key}/{n}", "node_key": f"dashboard/{source_key}",
            "context_text": f"Letter {source_key}", "chunk_text": text}


CHUNKS = [
    _chunk("aaa", 0, "aaa first"), _chunk("aaa", 1, "aaa second"),
    _chunk("bbb", 0, "bbb first"), _chunk("bbb", 1, "bbb second"),
    _chunk("ccc", 0, "ccc first"), _chunk("ccc", 1, "ccc second"),
]

# 리랭커 점수(0~1). 서한별 최고: bbb 0.9 > aaa 0.8 > ccc 0.2
RERANK = {"dashboard/aaa/0": 0.8, "dashboard/aaa/1": 0.5,
          "dashboard/bbb/0": 0.4, "dashboard/bbb/1": 0.9,
          "dashboard/ccc/0": 0.2, "dashboard/ccc/1": 0.1}

META = {
    "aaa": {"source_key": "aaa", "facility_name": "Plant A", "title": "Letter A", "subparts": ["S"], "date": "2025-01-01", "pdf_url": "https://epa.gov/a.pdf"},
    "bbb": {"source_key": "bbb", "facility_name": "Plant B", "title": "Letter B", "subparts": ["DDDDD"], "date": "2024-02-02", "pdf_url": "https://epa.gov/b.pdf"},
    "ccc": {"source_key": "ccc", "facility_name": "Plant C", "title": "Letter C", "subparts": [], "date": "2023-03-03", "pdf_url": "https://epa.gov/c.pdf"},
}


def _index(chunks: list[dict]) -> Index:
    # 벡터 검색은 청크를 그대로(코사인 점수 흉내), BM25 는 빈 결과. RRF 는 벡터만으로 돌아간다
    return Index("letters-rel", chunks, keyword=lambda q, k: [],
                 vector=lambda emb, k: [{**c, "score": 1.0 - i * 0.01} for i, c in enumerate(chunks)][:k])


def _rerank(scores: dict[str, float]):
    return lambda question, chunks: [scores.get(c["chunk_key"], 0.0) for c in chunks]


def _search(chunks=CHUNKS, scores=RERANK, meta=META):
    return similar_letters("our plant coats plastic parts", index=_index(chunks),
                           embed=lambda req: [0.0], rerank=_rerank(scores), meta=meta)


def test_source_key_of_chunk_reads_it_from_chunk_key():
    assert source_key_of_chunk(_chunk("ce814c7924dce44b", 3, "x")) == "ce814c7924dce44b"


def test_six_chunks_of_three_letters_collapse_to_three_letters_best_score_desc(monkeypatch):
    monkeypatch.setattr(letters, "MIN_SCORE", 0.0)
    got = _search()
    assert [l["source_key"] for l in got] == ["bbb", "aaa", "ccc"]        # 점수 내림차순
    assert [l["score"] for l in got] == [0.9, 0.8, 0.2]                    # 서한마다 최고 score 1개
    assert got[0]["snippet"] == "bbb second"                               # 근거 문장 = 최고 청크 본문
    assert got[0] == {**META["bbb"], "score": 0.9, "snippet": "bbb second"}  # 메타 6개 + score + snippet


def test_letters_below_min_score_are_dropped(monkeypatch):
    monkeypatch.setattr(letters, "MIN_SCORE", 0.3)
    assert [l["source_key"] for l in _search()] == ["bbb", "aaa"]         # ccc(0.2) 탈락


def test_all_below_min_score_gives_empty_list(monkeypatch):
    monkeypatch.setattr(letters, "MIN_SCORE", 0.95)
    assert _search() == []


def test_at_most_five_letters(monkeypatch):
    monkeypatch.setattr(letters, "MIN_SCORE", 0.0)
    keys = [f"k{i}" for i in range(7)]
    chunks = [_chunk(k, 0, f"{k} text") for k in keys]
    scores = {f"dashboard/{k}/0": 0.9 - i * 0.1 for i, k in enumerate(keys)}
    meta = {k: {**META["aaa"], "source_key": k} for k in keys}
    got = _search(chunks, scores, meta)
    assert len(got) == 5 and [l["source_key"] for l in got] == keys[:5]


def test_rerank_gets_at_most_20_chunks(monkeypatch):
    monkeypatch.setattr(letters, "MIN_SCORE", 0.0)
    chunks = [_chunk(f"k{i}", 0, "t") for i in range(30)]
    seen = []

    def rerank(question, cs):
        seen.append(len(cs))
        return [0.5] * len(cs)

    similar_letters("q", index=_index(chunks), embed=lambda req: [0.0], rerank=rerank,
                    meta={f"k{i}": {**META["aaa"], "source_key": f"k{i}"} for i in range(30)})
    assert seen == [20]


def test_min_score_is_a_rerank_probability_between_0_and_1():
    assert 0.0 < letters.MIN_SCORE < 1.0


# ---- POST /letters/similar ----
@pytest.fixture
def client(monkeypatch):
    import app.main as main
    importlib.reload(main)
    main.STATE["index"] = Index("rel-9", [], lambda q, k: [])
    main.STATE["letters"] = _index(CHUNKS)
    main.STATE["letter_meta"] = META
    calls = []

    def fake_similar_letters(description, *, index, embed, rerank, meta):
        calls.append((description, index.release_id))
        return [{**META["bbb"], "score": 0.9, "snippet": "bbb second"}]

    monkeypatch.setattr(main, "similar_letters", fake_similar_letters)
    c = TestClient(main.app)
    c.calls = calls
    return c


def test_post_letters_similar_returns_letters(client):
    r = client.post("/letters/similar", json={"description": "our plant coats plastic parts"})
    assert r.status_code == 200
    assert r.json() == {"letters": [{**META["bbb"], "score": 0.9, "snippet": "bbb second"}]}
    assert client.calls == [("our plant coats plastic parts", "letters-rel")]  # 서한 색인을 넘긴다


def test_post_letters_similar_blank_description_is_422(client):
    assert client.post("/letters/similar", json={"description": ""}).status_code == 422
    assert client.post("/letters/similar", json={"description": "   "}).status_code == 422
    assert client.post("/letters/similar", json={}).status_code == 422
    assert client.calls == []


def test_post_letters_similar_is_503_before_letter_index_is_ready(client):
    import app.main as main
    main.STATE["letters"] = None
    assert client.post("/letters/similar", json={"description": "x"}).status_code == 503
