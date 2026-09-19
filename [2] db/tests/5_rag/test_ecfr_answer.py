"""SUU-147: 검색 상위 조문 전문 → LLM → 판정 기준표 JSON. 요청 만들기·파싱만(호출 없음).
답 모양은 `[1] docs/3) rag/4_rag 답변 품질 개선 과정.md` 1절.
"""
import json

import pytest

from ecfr_answer import ANSWER_MODEL, build_answer_request, parse_answer

QUESTION = "Does the NESHAP for surface coating of plastic parts cover this solvent welding step?"
SECTIONS = [
    {"section_key": "section-63.4481", "subpart": "PPPP", "text": "§ 63.4481 Am I subject to this subpart? (a) ..."},
    {"section_key": "section-63.4581", "subpart": "PPPP", "text": "§ 63.4581 What definitions apply? Adhesive means ..."},
    {"section_key": "section-63.2", "subpart": "A", "text": "§ 63.2 Definitions. Major source means ..."},
]
GIVEN = [s["section_key"] for s in SECTIONS]

GOOD = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts and Products",
            "criteria": [{"criterion": "major source면 대상", "citations": ["40 CFR 63.4481(a)"]}],
        }
    ],
    "checklist": ["고형분이 있는가"],
}


def test_build_answer_request_has_question_and_every_section_text():
    req = build_answer_request(QUESTION, SECTIONS)
    assert req["model"] == ANSWER_MODEL == "gpt-5-mini"
    user = req["messages"][-1]["content"]
    assert QUESTION in user
    for s in SECTIONS:
        assert s["section_key"] in user and s["text"] in user
    system = req["messages"][0]["content"]
    assert "candidates" in system and "checklist" in system and "citations" in system
    # 최종 판정을 내리지 말라는 지시가 있다
    assert "not" in system.lower() and ("verdict" in system.lower() or "conclusion" in system.lower())


def test_parse_answer_accepts_plain_and_fenced_json():
    answer, issues = parse_answer(json.dumps(GOOD), GIVEN)
    assert answer == GOOD and issues == []
    answer, issues = parse_answer("```json\n" + json.dumps(GOOD) + "\n```", GIVEN)
    assert answer == GOOD and issues == []


def test_parse_answer_flags_unknown_fields_and_outside_citations_but_keeps_answer():
    raw = json.loads(json.dumps(GOOD))
    raw["applies"] = False  # 스키마 밖: 최종 판정
    raw["candidates"][0]["criteria"].append({"criterion": "x", "citations": ["40 CFR 63.9(b)"]})  # 넘겨준 조문 밖
    answer, issues = parse_answer(json.dumps(raw), GIVEN)
    assert "applies" not in answer  # 스키마 밖 필드는 떼고 돌려준다
    assert len(answer["candidates"][0]["criteria"]) == 2  # 인용은 그대로 두고(채점에서 근거율로 잡힘) 표시만 한다
    assert any("applies" in i for i in issues)
    assert any("section-63.9" in i for i in issues)


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        '{"candidates": []}',  # checklist 없음
        '{"candidates": [{"subpart": "PPPP", "criteria": []}], "checklist": ["x"]}',  # criteria 비어 있음
        '{"candidates": [{"subpart": "PPPP", "criteria": [{"criterion": "c", "citations": []}]}], "checklist": ["x"]}',  # 인용 없음
    ],
)
def test_parse_answer_rejects_missing_required_parts(raw):
    with pytest.raises(ValueError):
        parse_answer(raw, GIVEN)


# ---- SUU-150: 프롬프트가 subpart 칸을 코드로, 정답이 여럿이면 다 적게 시킨다 ----


def test_answer_system_tells_code_only_and_list_every_subpart():
    from ecfr_answer import ANSWER_SYSTEM

    system = ANSWER_SYSTEM.lower()
    assert "code only" in system  # subpart 칸: "M", "PPPP" 같은 코드만. "Subpart M"·조문 번호 X
    assert "every subpart" in system  # 적용될 수 있는 subpart가 여럿이면(Subpart A 포함) 다 적기


def test_parse_answer_normalizes_subpart_label_to_code():
    raw = json.loads(json.dumps(GOOD))
    raw["candidates"][0]["subpart"] = "Subpart PPPP"
    answer, issues = parse_answer(json.dumps(raw), GIVEN)
    assert answer["candidates"][0]["subpart"] == "PPPP"
    assert issues == []


def test_parse_answer_keeps_section_number_in_subpart_but_flags_it():
    raw = json.loads(json.dumps(GOOD))
    raw["candidates"][0]["subpart"] = "40 CFR 63.4481"
    answer, issues = parse_answer(json.dumps(raw), GIVEN)
    assert answer["candidates"][0]["subpart"] == "40 CFR 63.4481"  # 채점기가 미적중으로 잡게 그대로 둔다
    assert any("subpart" in i and "63.4481" in i for i in issues)
