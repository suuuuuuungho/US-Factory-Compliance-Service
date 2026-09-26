"""SUU-81: 평가셋으로 검색 정확도를 재는 순수 함수들.
규칙은 `[1] docs/1) project/1_Project_full.md` "RAG 검색 품질 개선 과정" 절을 따른다. 네트워크·DB는 쓰지 않는다.
"""
import math

import pytest

from ecfr_eval import (
    build_query_embedding_request,
    citation_section_key,
    gold_ranks,
    is_hit,
    rank_sections,
    section_key_of_chunk,
    summarize,
)


def chunk(chunk_key, score):
    node_key = chunk_key.removeprefix("ecfr/").rsplit("/", 1)[0]
    return {"chunk_key": chunk_key, "node_key": node_key, "score": score}


# 청크 순위: 63.4481이 3조각, 63.4581 표, 63.4490, 63.2, 63.6 순으로 섞여 있다
RANKED_CHUNKS = [
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/0", 0.90),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/0-1", 0.88),
    chunk("ecfr/40/63/subpart-A/section-63.2/0-3", 0.85),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4481/1", 0.80),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4581/1", 0.70),
    chunk("ecfr/40/63/subpart-A/section-63.2/0-7", 0.65),
    chunk("ecfr/40/63/subpart-PPPP/section-63.4490/0", 0.60),
    chunk("ecfr/40/63/subpart-A/section-63.6/0", 0.50),
]
GOLD = ["40 CFR 63.4481(a)", "40 CFR 63.4581", "40 CFR 63.4490"]


# --- build_query_embedding_request -------------------------------------------

def test_query_request_uses_retrieval_query_task():
    request = build_query_embedding_request("Does Subpart PPPP cover solvent welding?")

    assert request == {
        "texts": ["Does Subpart PPPP cover solvent welding?"],
        "task": "retrieval/query",
        "overflow_strategy": None,
    }


# --- citation_section_key ------------------------------------------------------

@pytest.mark.parametrize(
    "citation, expected",
    [
        ("40 CFR 63.4481(a)(1)", "section-63.4481"),
        ("40 CFR 63.4581", "section-63.4581"),
        ("40 CFR 63.2", "section-63.2"),
        ("40 CFR 63.11(b)(6)(ii)", "section-63.11"),
        ("40 CFR 63.4481 (a)", "section-63.4481"),
    ],
)
def test_citation_section_key_drops_paragraph(citation, expected):
    assert citation_section_key(citation) == expected


def test_citation_section_key_rejects_non_section():
    with pytest.raises(ValueError):
        citation_section_key("40 CFR Part 63 Subpart PPPP")


# --- section_key_of_chunk ------------------------------------------------------

def test_section_key_of_chunk_is_last_node_key_piece():
    assert section_key_of_chunk(RANKED_CHUNKS[0]) == "section-63.4481"
    assert section_key_of_chunk(RANKED_CHUNKS[2]) == "section-63.2"


# --- rank_sections -------------------------------------------------------------

def test_rank_sections_collapses_chunks_of_same_section():
    sections = rank_sections(RANKED_CHUNKS)

    assert [s["section_key"] for s in sections] == [
        "section-63.4481", "section-63.2", "section-63.4581", "section-63.4490", "section-63.6",
    ]


def test_rank_sections_keeps_best_chunk_and_score_per_section():
    sections = rank_sections(RANKED_CHUNKS)

    assert sections[0] == {
        "section_key": "section-63.4481",
        "chunk_key": "ecfr/40/63/subpart-PPPP/section-63.4481/0",
        "subpart": "PPPP",
        "score": 0.90,
    }
    assert sections[1]["subpart"] == "A"
    assert sections[1]["score"] == 0.85


def test_rank_sections_cuts_at_k_max():
    assert len(rank_sections(RANKED_CHUNKS, k_max=3)) == 3


def test_rank_sections_breaks_ties_by_chunk_key():
    tied = [
        chunk("ecfr/40/63/subpart-A/section-63.6/0", 0.5),
        chunk("ecfr/40/63/subpart-A/section-63.2/0", 0.5),
    ]

    assert [s["section_key"] for s in rank_sections(tied)] == ["section-63.2", "section-63.6"]


def test_rank_sections_sorts_by_score_regardless_of_input_order():
    shuffled = list(reversed(RANKED_CHUNKS))

    assert rank_sections(shuffled) == rank_sections(RANKED_CHUNKS)


# --- gold_ranks / is_hit -------------------------------------------------------

def test_gold_ranks_are_section_ranks_starting_at_one():
    sections = rank_sections(RANKED_CHUNKS)

    assert gold_ranks(GOLD, sections) == {
        "section-63.4481": 1,
        "section-63.4581": 3,
        "section-63.4490": 4,
    }


def test_gold_ranks_none_when_missing_and_dedupes_same_section():
    sections = rank_sections(RANKED_CHUNKS, k_max=2)

    assert gold_ranks(["40 CFR 63.4481(a)", "40 CFR 63.4481(b)", "40 CFR 63.9999"], sections) == {
        "section-63.4481": 1,
        "section-63.9999": None,
    }


def test_is_hit_loose_needs_any_gold_in_top_k():
    sections = rank_sections(RANKED_CHUNKS)

    assert is_hit(GOLD, sections, top_k=1) is True
    assert is_hit(["40 CFR 63.4490"], sections, top_k=3) is False
    assert is_hit(["40 CFR 63.4490"], sections, top_k=4) is True


def test_is_hit_strict_needs_all_gold_in_top_k():
    sections = rank_sections(RANKED_CHUNKS)

    assert is_hit(GOLD, sections, top_k=3, strict=True) is False
    assert is_hit(GOLD, sections, top_k=4, strict=True) is True


# --- summarize -----------------------------------------------------------------

def result(gold_ranks_, gold_subparts, returned_subparts):
    return {
        "gold_ranks": gold_ranks_,
        "gold_subparts": gold_subparts,
        "returned_subparts": returned_subparts,
    }


RESULTS = [
    result({"section-63.4481": 1, "section-63.4581": 3}, ["PPPP"], ["PPPP", "A", "PPPP"]),
    result({"section-63.2": 2}, ["A"], ["PPPP", "A"]),
    result({"section-63.10": 7, "section-63.11": None}, ["A"], ["B"] * 7),
    result({"section-63.640": None}, ["CC"], ["A"] * 20),
]


def test_summarize_hit_loose_per_k():
    metrics = summarize(RESULTS, ks=(1, 5, 20))

    assert metrics["hit_loose"] == {"1": 0.25, "5": 0.5, "20": 0.75}


def test_summarize_hit_strict_and_recall():
    metrics = summarize(RESULTS, ks=(5, 20))

    assert metrics["hit_strict"] == {"5": 0.5, "20": 0.5}
    assert metrics["recall"] == {"5": 0.5, "20": pytest.approx((1 + 1 + 0.5 + 0) / 4)}


def test_summarize_subpart_hit_primary():
    metrics = summarize(RESULTS, ks=(1, 5))

    assert metrics["subpart_hit_primary"] == {"1": 0.25, "5": 0.5}


def test_summarize_mrr_and_median_rank():
    metrics = summarize(RESULTS, ks=(5, 20))

    assert metrics["mrr_20"] == pytest.approx((1 + 0.5 + 1 / 7 + 0) / 4)
    # first_gold_rank = 1, 2, 7, null→21 → 중앙값 (2+7)/2
    assert metrics["median_first_gold_rank"] == 4.5


def test_summarize_wilson_ci_for_hit_loose():
    metrics = summarize(RESULTS, ks=(5, 20))

    assert metrics["ci95_hit_loose_5"] == pytest.approx([0.150, 0.850], abs=0.001)
    assert metrics["ci95_hit_loose_20"] == pytest.approx([0.301, 0.954], abs=0.001)


def test_summarize_wilson_ci_at_boundaries():
    all_miss = [result({"section-63.2": None}, ["A"], [])] * 4
    all_hit = [result({"section-63.2": 1}, ["A"], ["A"])] * 4

    assert summarize(all_miss, ks=(5, 20))["ci95_hit_loose_5"] == pytest.approx([0.0, 0.490], abs=0.001)
    assert summarize(all_hit, ks=(5, 20))["ci95_hit_loose_5"] == pytest.approx([0.510, 1.0], abs=0.001)


def test_summarize_reports_n_cases():
    assert summarize(RESULTS)["n_cases"] == 4


def test_summarize_ndcg_binary_gain():
    # 정답은 전부 1점. DCG = Σ 1/log2(rank+1), IDCG = 정답 수만큼 1등부터 채운 값
    metrics = summarize(RESULTS, ks=(5, 10))
    case1 = (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))     # 1등, 3등 / 정답 2개
    case2 = (1 / math.log2(3)) / 1                              # 2등 / 정답 1개
    case3 = (1 / math.log2(8)) / (1 + 1 / math.log2(3))         # 7등, 없음 / 정답 2개
    assert metrics["ndcg"]["10"] == pytest.approx((case1 + case2 + case3 + 0) / 4)
    assert metrics["ndcg"]["5"] == pytest.approx((case1 + case2 + 0 + 0) / 4)
