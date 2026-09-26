"""SUU-149: 답변 실패를 원인별로 나눈다 — 지어냄 / 검색 / 형식 / 답.
SUU-275: 채점기 v2 행(`scorer_version: "v2"`)은 `classify_v2`로. 태그는 계획 [5]-5 중 자동으로 알 수 있는 것만.
"""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from answer_failures import TAGS, TAGS_V2, classify, classify_v2, summarize  # noqa: E402

CASE = {"case_id": "c", "gold_subparts": ["M"], "gold_citations": ["40 CFR 63.320(a)", "40 CFR 63.322"]}


def out(**kw):
    base = {"case_id": "c", "subpart": 1, "judge": 2, "citation_grounded": 1.0, "outside_citations": [],
            "given": ["section-63.320", "section-63.322", "section-63.2"],
            "answer": {"candidates": [{"subpart": "M", "criteria": []}], "checklist": []}}
    return {**base, **kw}


def test_passing_case_has_no_tag():
    assert classify(out(), CASE) is None


def test_fabricated_citation_wins_over_everything():
    o = out(subpart=0, judge=0, citation_grounded=0.5, outside_citations=["section-63.9"], given=["section-63.2"])
    assert classify(o, CASE) == "fabricated"


def test_search_when_no_gold_section_was_given():
    o = out(subpart=0, given=["section-63.2", "section-63.6"])
    assert classify(o, CASE) == "search"


def test_format_when_subpart_label_is_not_a_code():
    # 정답 조문은 줬는데 subpart 칸에 조문 번호를 썼다
    o = out(subpart=0, answer={"candidates": [{"subpart": "40 CFR 63.460", "criteria": []}], "checklist": []})
    assert classify(o, CASE) == "format"


def test_answer_when_sections_given_but_subpart_wrong_or_judge_zero():
    assert classify(out(subpart=0, answer={"candidates": [{"subpart": "CC", "criteria": []}], "checklist": []}), CASE) == "answer"
    assert classify(out(judge=0), CASE) == "answer"


def test_summarize_counts_tags_and_lists_case_ids_in_order():
    rows = [
        ("a", "search"), ("b", None), ("c", "answer"), ("d", "search"), ("e", "format"),
    ]
    outs = [out(case_id=cid) for cid, _ in rows]
    tags = {cid: tag for cid, tag in rows}
    table = summarize(outs, lambda o: tags[o["case_id"]])
    assert table["n_failed"] == 4
    assert table["counts"] == {"fabricated": 0, "search": 2, "format": 1, "answer": 1}
    assert table["cases"] == {"fabricated": [], "search": ["a", "d"], "format": ["e"], "answer": ["c"]}


# ---- SUU-275: 채점기 v2 행 ----


def out_v2(**kw):
    base = {"case_id": "c", "scorer_version": "v2", "g0_grounded": 1.0, "g0_outside": [], "g1_quote": 1.0, "g1_mismatched": [],
            "g2_subpart": 1, "g3_citation_recall": 1.0, "g4_checklist": 1.0, "failed": False,
            "given": ["section-63.320", "section-63.322", "section-63.2"],
            "answer": {"candidates": [{"subpart": "M", "gates": []}], "checklist": []}}
    return {**base, **kw}


def test_v2_tags_are_the_automatic_ones_from_the_plan_in_priority_order():
    assert TAGS == ("fabricated", "search", "format", "answer")  # v1 그대로
    assert TAGS_V2 == ("format", "fabricated", "quote_mismatch", "search", "answer")


def test_classify_v2_passing_row_has_no_tag():
    assert classify_v2(out_v2(), CASE) is None
    # G1·G4가 깎여도 자동 실패는 아니다(지표로만 본다). 단 발췌 불일치 관문이 있으면 태그
    assert classify_v2(out_v2(g4_checklist=0.5), CASE) is None


def test_classify_v2_format_when_answer_could_not_be_parsed():
    o = out_v2(answer=None, g0_grounded=0.0, g2_subpart=0, failed=True)
    assert classify_v2(o, CASE) == "format"


def test_classify_v2_fabricated_wins_over_quote_search_and_answer():
    o = out_v2(g0_grounded=0.5, g0_outside=["section-63.9"], g1_mismatched=["M/threshold"], g2_subpart=0, failed=True,
               given=["section-63.2"])
    assert classify_v2(o, CASE) == "fabricated"


def test_classify_v2_quote_mismatch_when_a_gate_quote_is_not_in_its_section():
    o = out_v2(g1_quote=0.5, g1_mismatched=["M/threshold"])
    assert classify_v2(o, CASE) == "quote_mismatch"
    o = out_v2(g1_quote=0.5, g1_mismatched=["M/threshold"], g2_subpart=0, failed=True, given=["section-63.2"])
    assert classify_v2(o, CASE) == "quote_mismatch"  # search보다 앞


def test_classify_v2_search_when_no_gold_section_was_given():
    o = out_v2(g2_subpart=0, failed=True, given=["section-63.2", "section-63.6"])
    assert classify_v2(o, CASE) == "search"


def test_classify_v2_answer_when_sections_given_but_subpart_wrong():
    o = out_v2(g2_subpart=0, failed=True, answer={"candidates": [{"subpart": "CC", "gates": []}], "checklist": []})
    assert classify_v2(o, CASE) == "answer"


def test_summarize_takes_v2_tags():
    rows = [("a", "quote_mismatch"), ("b", None), ("c", "answer"), ("d", "fabricated")]
    outs = [out_v2(case_id=cid) for cid, _ in rows]
    tags = {cid: tag for cid, tag in rows}
    table = summarize(outs, lambda o: tags[o["case_id"]], tags=TAGS_V2)
    assert table["n_failed"] == 3
    assert table["counts"] == {"format": 0, "fabricated": 1, "quote_mismatch": 1, "search": 0, "answer": 1}
    assert table["cases"]["quote_mismatch"] == ["a"] and table["cases"]["fabricated"] == ["d"]
