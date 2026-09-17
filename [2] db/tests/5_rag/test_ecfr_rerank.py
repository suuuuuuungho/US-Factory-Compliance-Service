"""SUU-101: Kanon 2 리랭커로 조문 순위를 다시 매긴다.
리랭커 호출은 `rerank(question, ranked_chunks) -> list[float]`로 주입한다. 네트워크는 쓰지 않는다.
"""
from ecfr_search import build_rerank_request, search_sections


def chunk(chunk_key, embedding):
    node_key = chunk_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    return {"chunk_key": chunk_key, "node_key": node_key, "embedding": embedding}


# 질문 벡터 [1, 0]과의 코사인 순서: 63.4481/0 (1.0) > 63.4481/1 (0.71) > 63.2 (0.45) > 63.6 (0.0)
CHUNKS = [
    chunk("ecfr/40/63/subpart-A/section-63.6/0", [0.0, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/1", [1.0, 1.0]),
    chunk("ecfr/40/63/subpart-A/section-63.2/0", [0.5, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/0", [1.0, 0.0]),
]
QUESTION = "Does Subpart PPPP cover solvent welding?"


def fake_embed(request):
    return [1.0, 0.0]


def test_build_rerank_request_joins_context_and_chunk_text():
    chunks = [
        {"chunk_key": "a", "context_text": "ctx A", "chunk_text": "body A"},
        {"chunk_key": "b", "context_text": None, "chunk_text": "body B"},
    ]

    assert build_rerank_request(QUESTION, chunks) == {
        "query": QUESTION,
        "texts": ["ctx A\n\nbody A", "body B"],
    }


def test_search_sections_passes_vector_candidates_to_rerank_in_vector_order():
    seen = []

    def rerank(question, ranked):
        seen.append((question, [c["chunk_key"] for c in ranked]))
        return [0.0] * len(ranked)

    search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, rerank=rerank, chunk_top_k=3)

    assert seen == [(QUESTION, [
        "ecfr/40/63/subpart-PPPP/section-63.4481/0",
        "ecfr/40/63/subpart-PPPP/section-63.4481/1",
        "ecfr/40/63/subpart-A/section-63.2/0",
    ])]


def test_search_sections_orders_sections_by_rerank_score():
    # 벡터 순서 63.4481/0, 63.4481/1, 63.2, 63.6 에 리랭커 점수 0.1, 0.3, 0.6, 0.9 → 순서가 뒤집힌다
    def rerank(question, ranked):
        return [0.1, 0.3, 0.6, 0.9]

    hits = search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, rerank=rerank)

    assert [h["section_key"] for h in hits] == ["section-63.6", "section-63.2", "section-63.4481"]
    assert hits[0]["score"] == 0.9
    assert hits[2]["chunk_key"] == "ecfr/40/63/subpart-PPPP/section-63.4481/1"
    assert hits[2]["score"] == 0.3


def test_search_sections_without_rerank_is_unchanged():
    assert search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, rerank=None) == \
        search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS)
