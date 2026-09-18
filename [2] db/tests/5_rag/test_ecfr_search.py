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


# SUU-134: 리랭크 뒤 후처리 규칙(창 안에서 표 뒤로, 5등 안 Subpart 상위 2 + A 우선)
from ecfr_search import RULES, apply_rank_rules  # noqa: E402


def sec(key, subpart):
    return {"section_key": key, "chunk_key": key, "subpart": subpart, "score": 1.0}


RANKED = [sec("section-63.4500", "PPPP"), sec("appendix-Table-1", "PPPP"), sec("section-63.1573", "UUU"),
          sec("section-63.8", "A"), sec("section-63.4510", "PPPP"), sec("section-63.700", "EEE"),
          sec("appendix-Table-2", "EEE")]


def test_apply_rank_rules_moves_tables_back():
    out = apply_rank_rules(RANKED, window=6, demote_tables=True, subpart_top=0)
    assert [s["section_key"] for s in out] == [
        "section-63.4500", "section-63.1573", "section-63.8", "section-63.4510", "section-63.700",
        "appendix-Table-1",  # 창 안 표는 창 맨 뒤로
        "appendix-Table-2",  # 창 밖은 그대로
    ]


def test_apply_rank_rules_prefers_found_subparts():
    # 1~5등 Subpart 순서: PPPP, UUU, A → 상위 2 = PPPP·UUU, 거기에 A. EEE는 뒤로
    out = apply_rank_rules(RANKED, window=None, demote_tables=False, subpart_top=2)
    assert [s["section_key"] for s in out] == [
        "section-63.4500", "appendix-Table-1", "section-63.1573", "section-63.8", "section-63.4510",
        "section-63.700", "appendix-Table-2",
    ]
    assert RULES == {"window": 60, "demote_tables": True, "subpart_top": 2}


def test_search_sections_applies_rules_after_rerank():
    # 리랭크 점수로 표(63.4481/1을 표로 가장)가 1등이 되게 한 뒤, 규칙이 표를 뒤로 보내는지 본다
    table = {**chunk("ecfr/40/63/subpart-PPPP/appendix-Table-1/0", [1.0, 0.0])}
    chunks = CHUNKS + [table]
    score = {"appendix-Table-1": 2.0, "section-63.4481": 1.0, "section-63.2": 0.9, "section-63.6": 0.8}
    rerank = lambda q, ranked: [score[c["chunk_key"].rsplit("/", 2)[1]] for c in ranked]  # noqa: E731

    with_rules = search_sections(QUESTION, embed=fake_embed, chunks=chunks, rerank=rerank, top_k=2)
    assert [h["section_key"] for h in with_rules] == ["section-63.4481", "section-63.2"]

    no_rules = search_sections(QUESTION, embed=fake_embed, chunks=chunks, rerank=rerank, top_k=2, rules=False)
    assert no_rules[0]["section_key"] == "appendix-Table-1"

    no_rerank = search_sections(QUESTION, embed=fake_embed, chunks=chunks, top_k=1)
    assert no_rerank[0]["section_key"] in ("section-63.4481", "appendix-Table-1")  # 리랭커 없으면 규칙 없음(동점)
