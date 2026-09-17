"""SUU-100: 벡터·키워드 검색 결과를 RRF로 합쳐 조문을 찾는다.
키워드 검색은 `keyword(question, k) -> [{"chunk_key", "node_key", "score"}]`로 주입한다. 네트워크는 쓰지 않는다.
"""
import pytest

from ecfr_search import rrf_merge, search_sections


def chunk(chunk_key, embedding):
    node_key = chunk_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    return {"chunk_key": chunk_key, "node_key": node_key, "embedding": embedding}


CHUNKS = [
    chunk("ecfr/40/63/subpart-A/section-63.6/0", [0.0, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/1", [1.0, 1.0]),
    chunk("ecfr/40/63/subpart-A/section-63.2/0", [0.5, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/0", [1.0, 0.0]),
]
QUESTION = "Does Subpart PPPP cover solvent welding?"


def fake_embed(request):
    return [1.0, 0.0]


def test_rrf_merge_ranks_chunks_in_both_lists_first():
    a = [{"chunk_key": "x1"}, {"chunk_key": "x2"}, {"chunk_key": "x3"}]
    b = [{"chunk_key": "x3"}, {"chunk_key": "y1"}]
    merged = rrf_merge([a, b], k=60)
    assert [m["chunk_key"] for m in merged] == ["x3", "x1", "x2", "y1"]
    assert merged[0]["score"] == pytest.approx(1 / 63 + 1 / 61)
    assert merged[2]["score"] == merged[3]["score"] == pytest.approx(1 / 62)


def test_search_sections_passes_rrf_candidates_to_rerank():
    seen_keyword, seen_rerank = [], []

    def keyword(question, k):
        seen_keyword.append((question, k))
        return [
            {"chunk_key": "ecfr/40/63/subpart-A/section-63.6/0", "node_key": "40/63/subpart-A/section-63.6", "score": 0.5},
            {"chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0", "node_key": "40/63/subpart-PPPP/section-63.4481", "score": 0.4},
        ]

    def rerank(question, ranked):
        seen_rerank.append([c["chunk_key"] for c in ranked])
        assert all("embedding" in c for c in ranked)
        return [0.0] * len(ranked)

    search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, keyword=keyword, rerank=rerank, chunk_top_k=2)
    assert seen_keyword == [(QUESTION, 2)]
    assert seen_rerank == [[
        "ecfr/40/63/subpart-PPPP/section-63.4481/0",
        "ecfr/40/63/subpart-A/section-63.6/0",
    ]]


def test_search_sections_hybrid_without_rerank_uses_rrf_scores():
    def keyword(question, k):
        return [{"chunk_key": "ecfr/40/63/subpart-A/section-63.6/0", "node_key": "40/63/subpart-A/section-63.6", "score": 0.5}]

    hits = search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, keyword=keyword)
    # 벡터 4위(1/64) + 키워드 1위(1/61) 인 63.6 이 벡터 1위(1/61)만 있는 63.4481 보다 위
    assert [h["section_key"] for h in hits] == ["section-63.6", "section-63.4481", "section-63.2"]
    assert hits[0]["score"] == pytest.approx(1 / 64 + 1 / 61)
    assert hits[1]["score"] == pytest.approx(1 / 61)


def test_search_sections_without_keyword_is_unchanged():
    assert search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, keyword=None) == \
        search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS)
