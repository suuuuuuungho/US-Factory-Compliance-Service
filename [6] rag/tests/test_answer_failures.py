"""SUU-149: 답변 실패를 원인별로 나눈다 — 지어냄 / 검색 / 형식 / 답."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from answer_failures import classify, summarize  # noqa: E402

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
