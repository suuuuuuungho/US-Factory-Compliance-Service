"""SUU-92: 질문 하나로 관련 조문 상위 k개를 돌려준다.
임베딩·DB는 인자로 주입한다. 네트워크·DB는 쓰지 않는다.
"""
from ecfr_search import search_sections


def chunk(chunk_key, embedding):
    node_key = chunk_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    return {"chunk_key": chunk_key, "node_key": node_key, "embedding": embedding}


# 질문 벡터 [1, 0]과의 코사인: 63.4481/0 = 1.0, 63.4481/1 ≈ 0.71, 63.2 ≈ 0.45, 63.6 = 0.0
CHUNKS = [
    chunk("ecfr/40/63/subpart-A/section-63.6/0", [0.0, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/1", [1.0, 1.0]),
    chunk("ecfr/40/63/subpart-A/section-63.2/0", [0.5, 1.0]),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/0", [1.0, 0.0]),
]
QUESTION = "Does Subpart PPPP cover solvent welding?"


def fake_embed(request):
    return [1.0, 0.0]


def test_search_sections_embeds_question_with_query_task():
    seen = []

    def embed(request):
        seen.append(request)
        return [1.0, 0.0]

    search_sections(QUESTION, embed=embed, chunks=CHUNKS)

    assert seen == [{"texts": [QUESTION], "task": "retrieval/query", "overflow_strategy": None}]


def test_search_sections_returns_sections_sorted_by_score():
    hits = search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS)

    assert [h["section_key"] for h in hits] == ["section-63.4481", "section-63.2", "section-63.6"]
    assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)
    assert set(hits[0]) == {"section_key", "chunk_key", "subpart", "score"}


def test_search_sections_collapses_same_section_and_keeps_best_chunk():
    hits = search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS)

    assert hits[0]["chunk_key"] == "ecfr/40/63/subpart-PPPP/section-63.4481/0"
    assert hits[0]["subpart"] == "PPPP"
    assert hits[0]["score"] == 1.0


def test_search_sections_cuts_at_top_k():
    hits = search_sections(QUESTION, embed=fake_embed, chunks=CHUNKS, top_k=2)

    assert [h["section_key"] for h in hits] == ["section-63.4481", "section-63.2"]


def test_search_sections_with_no_chunks_returns_empty():
    assert search_sections(QUESTION, embed=fake_embed, chunks=[]) == []
