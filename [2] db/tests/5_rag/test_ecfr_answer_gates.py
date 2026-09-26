"""SUU-274: 답 생성기가 관문(gate) 모양(`[1] docs/1) project/1_Project_full.md` "RAG 답변 품질 개선 과정" 절)의 요청·파싱도 한다.

`shape="criteria"`(후보 A, 지금 그대로)와 `shape="gates"`(후보 B)를 인자로 고른다. 호출은 하지 않는다.
"""
import json

import pytest

from ecfr_answer import ANSWER_SYSTEM, build_answer_request, parse_answer

QUESTION = "Does the NESHAP for surface coating of plastic parts cover this solvent welding step?"
SECTIONS = [
    {"section_key": "section-63.4481", "subpart": "PPPP", "text": "§ 63.4481 Am I subject to this subpart? (a) ..."},
    {"section_key": "section-63.4581", "subpart": "PPPP", "text": "§ 63.4581 What definitions apply? Adhesive means ..."},
    {"section_key": "section-63.2", "subpart": "A", "text": "§ 63.2 Definitions. Major source means ..."},
]
GIVEN = [s["section_key"] for s in SECTIONS]
GATE_TYPES = ["source_category", "affected_source", "major_or_area", "threshold", "exemption", "compliance_date"]

GATE_A = {
    "type": "affected_source",
    "question": "두 면을 붙이려고 바르는 물질이 '접착제'에 해당하는가?",
    "test": "접착제이면 코팅으로 보아 적용 쪽, 아니면 비적용 쪽",
    "citations": ["40 CFR 63.4581"],
    "quote": "Adhesive means any chemical substance that is applied for the purpose of bonding two surfaces together",
}
GATE_B = {
    "type": "major_or_area",
    "question": "이 공장이 major source인가?",
    "test": "major source이면 적용 쪽",
    "citations": ["40 CFR 63.4481(a)"],
    "quote": "Am I subject to this subpart",
}
GOOD = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts and Products",
            "gates": [GATE_A, GATE_B],
            "missing": ["major source 정의(63.2)는 넘겨받지 못함"],
        }
    ],
    "checklist": [
        {"item": "바르는 물질의 SDS에서 고형분 함량을 확인한다", "gate": "threshold"},
        {"item": "접합 뒤 마른 막이 남는지 확인한다", "gate": "affected_source"},
    ],
}


def copy(obj):
    return json.loads(json.dumps(obj))


# ---- 요청 ----


def test_build_answer_request_gates_prompt_names_six_gate_types_and_quote_rule():
    req = build_answer_request(QUESTION, SECTIONS, shape="gates")
    system = req["messages"][0]["content"]
    for gate_type in GATE_TYPES:
        assert gate_type in system, f"관문 type '{gate_type}'이 프롬프트에 없다"
    assert "gates" in system and "quote" in system and "missing" in system
    assert "20" in system and "40" in system  # 발췌는 20~40단어
    low = system.lower()
    assert "verdict" in low or "conclusion" in low  # 판정 금지 지시
    # 질문·조문 전문은 criteria 모양과 똑같이 들어간다
    user = req["messages"][-1]["content"]
    assert QUESTION in user
    for s in SECTIONS:
        assert s["section_key"] in user and s["text"] in user


def test_build_answer_request_criteria_is_the_default_and_unchanged():
    default = build_answer_request(QUESTION, SECTIONS)
    criteria = build_answer_request(QUESTION, SECTIONS, shape="criteria")
    assert default == criteria
    assert criteria["messages"][0]["content"] == ANSWER_SYSTEM  # 후보 A 프롬프트는 글자까지 그대로
    assert "gates" not in ANSWER_SYSTEM


def test_build_answer_request_rejects_unknown_shape():
    with pytest.raises(ValueError):
        build_answer_request(QUESTION, SECTIONS, shape="table")


# ---- 파싱 ----


def test_parse_answer_gates_returns_structure_as_is():
    answer, issues = parse_answer(json.dumps(GOOD), GIVEN, shape="gates")
    assert answer == GOOD and issues == []
    answer, issues = parse_answer("```json\n" + json.dumps(GOOD) + "\n```", GIVEN, shape="gates")
    assert answer == GOOD and issues == []


def test_parse_answer_gates_drops_verdict_keys_everywhere_and_notes_them():
    raw = copy(GOOD)
    raw["applies"] = False
    raw["candidates"][0]["verdict"] = "subject"
    raw["candidates"][0]["gates"][0]["conclusion"] = "yes"
    answer, issues = parse_answer(json.dumps(raw), GIVEN, shape="gates")
    assert answer == GOOD  # 판정 키만 빠지고 나머지는 그대로
    assert any("applies" in i for i in issues)
    assert any("verdict" in i for i in issues)
    assert any("conclusion" in i for i in issues)


def test_parse_answer_gates_missing_defaults_to_empty_list():
    raw = copy(GOOD)
    del raw["candidates"][0]["missing"]
    answer, issues = parse_answer(json.dumps(raw), GIVEN, shape="gates")
    assert answer["candidates"][0]["missing"] == []
    assert issues == []


def test_parse_answer_gates_drops_gate_lacking_required_key_but_keeps_the_rest():
    raw = copy(GOOD)
    del raw["candidates"][0]["gates"][1]["quote"]  # 발췌 없는 관문
    answer, issues = parse_answer(json.dumps(raw), GIVEN, shape="gates")
    assert answer["candidates"][0]["gates"] == [GATE_A]
    assert any("quote" in i for i in issues)


def test_parse_answer_gates_flags_outside_citation_but_keeps_it():
    raw = copy(GOOD)
    raw["candidates"][0]["gates"][0]["citations"] = ["40 CFR 63.9(b)"]
    answer, issues = parse_answer(json.dumps(raw), GIVEN, shape="gates")
    assert answer["candidates"][0]["gates"][0]["citations"] == ["40 CFR 63.9(b)"]  # 채점기 G0가 잡는다
    assert any("section-63.9" in i for i in issues)


def _without(path: list, value=None):
    raw = copy(GOOD)
    obj = raw
    for key in path[:-1]:
        obj = obj[key]
    if value is None:
        del obj[path[-1]]
    else:
        obj[path[-1]] = value
    return json.dumps(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        _without(["checklist"]),  # checklist 없음
        _without(["checklist"], []),  # checklist 비어 있음
        _without(["checklist"], ["문자열 항목"]),  # checklist 항목이 {item, gate}가 아님
        _without(["candidates", 0, "gates"], []),  # 관문 없음
        _without(["candidates", 0, "gates"], [{**GATE_A, "citations": []}]),  # 하나뿐인 관문이 인용 없음 → 버리면 관문 0개
        _without(["candidates", 0, "subpart"]),  # subpart 없음
    ],
    ids=["not-json", "no-checklist", "empty-checklist", "checklist-not-item-gate", "no-gates", "only-gate-has-no-citation", "no-subpart"],
)
def test_parse_answer_gates_rejects_missing_required_parts(raw):
    with pytest.raises(ValueError):
        parse_answer(raw, GIVEN, shape="gates")


def test_parse_answer_criteria_shape_still_works_by_default():
    criteria_answer = {
        "candidates": [{"subpart": "PPPP", "title": "t", "criteria": [{"criterion": "c", "citations": ["40 CFR 63.4481(a)"]}]}],
        "checklist": ["고형분이 있는가"],
    }
    answer, issues = parse_answer(json.dumps(criteria_answer), GIVEN)
    assert answer == criteria_answer and issues == []
    with pytest.raises(ValueError):  # 관문 모양 답을 criteria 파서에 넣으면 criteria가 없어 거절
        parse_answer(json.dumps(GOOD), GIVEN, shape="criteria")
