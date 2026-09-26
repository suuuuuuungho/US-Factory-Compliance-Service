"""SUU-282: 답변(나열 모양)에서 넘겨준 조문 밖의 인용을 코드가 지운다.

밖의 인용만 지우고, 인용이 안 남은 기준 문장은 문장째, 기준 문장이 안 남은 후보는 후보째 지운다.
원본은 그대로 둔다(근거율은 원본으로 잰다). 관문(gates) 모양은 손대지 않는다(verify_answer가 담당).
"""
import copy

from ecfr_answer import drop_outside_citations

GIVEN = ["section-63.4481", "section-63.4581", "section-63.2"]


def crit(text, *citations):
    return {"criterion": text, "citations": list(citations)}


def answer(*candidates):
    return {
        "candidates": [{"subpart": sp, "title": "t", "criteria": crits} for sp, crits in candidates],
        "checklist": ["x"],
    }


def test_removes_only_outside_citations():
    a = answer(("PPPP", [crit("major source", "40 CFR 63.4481(a)", "40 CFR 63.9(b)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert clean["candidates"][0]["criteria"][0]["citations"] == ["40 CFR 63.4481(a)"]
    assert len(dropped) == 1 and "section-63.9" in dropped[0]


def test_non_part63_citation_counts_as_outside():
    a = answer(("PPPP", [crit("keep", "40 CFR 63.4481(a)", "40 CFR 70.6(c)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert clean["candidates"][0]["criteria"][0]["citations"] == ["40 CFR 63.4481(a)"]
    assert len(dropped) == 1 and "70.6" in dropped[0]


def test_removes_criterion_with_no_citation_left():
    a = answer(("PPPP", [crit("keep", "40 CFR 63.4481(a)"), crit("gone", "40 CFR 63.9(b)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert [c["criterion"] for c in clean["candidates"][0]["criteria"]] == ["keep"]
    assert any("criteria[1]" in d for d in dropped)


def test_removes_candidate_with_no_criterion_left():
    a = answer(("PPPP", [crit("keep", "40 CFR 63.4481(a)")]), ("M", [crit("gone", "40 CFR 63.9(b)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert [c["subpart"] for c in clean["candidates"]] == ["PPPP"]
    assert any("candidates[1]" in d for d in dropped)


def test_all_candidates_dropped_leaves_empty_list_not_error():
    a = answer(("M", [crit("gone", "40 CFR 63.9(b)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert clean["candidates"] == [] and clean["checklist"] == ["x"]
    assert dropped


def test_input_is_not_mutated():
    a = answer(("PPPP", [crit("keep", "40 CFR 63.4481(a)", "40 CFR 63.9(b)")]))
    before = copy.deepcopy(a)
    drop_outside_citations(a, GIVEN)
    assert a == before


def test_nothing_outside_returns_equal_answer_and_empty_dropped():
    a = answer(("PPPP", [crit("keep", "40 CFR 63.4481(a)")]))
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert clean == a and dropped == []


def test_gates_shape_is_left_alone():
    a = {
        "candidates": [{"subpart": "PPPP", "title": "t", "missing": [],
                        "gates": [{"type": "scope", "question": "q", "test": "t",
                                   "citations": ["40 CFR 63.9(b)"], "quote": "x"}]}],
        "checklist": [{"item": "i", "gate": "scope"}],
    }
    clean, dropped = drop_outside_citations(a, GIVEN)
    assert clean == a and dropped == []
