"""SUU-146: 판정 기준표 답 JSON 하나를 4개 지표로 채점한다.
Subpart 적중·인용 Recall·인용 근거율은 $0 규칙, 판정 기준 점수는 심판 LLM 요청 만들기·파싱만(호출 없음).
답 모양·채점표는 `[1] docs/3) rag/4_rag 답변 품질 개선 과정.md` 1·2절.
"""
import pytest

from ecfr_answer_score import (
    aggregate,
    build_judge_request,
    parse_judge,
    score_citation_grounded,
    score_citation_recall,
    score_subpart,
)

CASE = {
    "case_id": "dashboard-king-systems-2020-06-16",
    "question": "Does the NESHAP for surface coating of plastic parts cover this solvent welding step?",
    "gold_subparts": ["PPPP"],
    "gold_citations": ["40 CFR 63.4481(a)", "40 CFR 63.4581", "40 CFR 63.4490"],
    "notes": "Not subject to PPPP. MeCl applied to bond two surfaces is an 'adhesive' and therefore a coating under 63.4581, "
    "but with no coating solids the 63.4490 emission limit cannot be determined.",
}
# 검색이 넘겨준 조문(상위 5) — section key
GIVEN = ["section-63.4481", "section-63.4581", "section-63.4490", "section-63.4482", "section-63.2"]
ANSWER = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts",
            "criteria": [
                {"criterion": "플라스틱 부품 코팅 major source면 대상", "citations": ["40 CFR 63.4481(a)"]},
                {"criterion": "고형분 없으면 한도 계산 불가", "citations": ["40 CFR 63.4490", "40 CFR 63.4481(b)"]},
                {"criterion": "정의는 63.2", "citations": ["40 CFR 63.9(b)"]},  # 63.9는 넘겨준 조문 밖 → 지어냄
            ],
        }
    ],
    "checklist": ["고형분이 있는가"],
}


# --- $0 지표 3개 -------------------------------------------------------------


def test_score_subpart_hits_when_primary_gold_subpart_is_a_candidate():
    assert score_subpart(ANSWER, CASE) == 1
    assert score_subpart({"candidates": [{"subpart": "MMMM", "criteria": []}], "checklist": []}, CASE) == 0
    assert score_subpart({"candidates": [], "checklist": []}, CASE) == 0


def test_score_citation_recall_counts_gold_sections_cited_anywhere_in_answer():
    # 정답 3조문 {4481, 4581, 4490} 중 답에 나온 것 = 4481, 4490 → 2/3. 문단 번호(a)/(b)는 뗀다
    assert score_citation_recall(ANSWER, CASE) == pytest.approx(2 / 3)
    assert score_citation_recall({"candidates": [], "checklist": []}, CASE) == 0.0


def test_score_citation_grounded_flags_citations_outside_given_sections():
    # 답의 인용 4개(4481(a), 4490, 4481(b), 63.9) → 조문 단위 {4481, 4490, 63.9}. 63.9는 GIVEN 밖 → 2/3
    grounded, outside = score_citation_grounded(ANSWER, GIVEN)
    assert grounded == pytest.approx(2 / 3)
    assert outside == ["section-63.9"]
    # 인용이 하나도 없으면 근거율 0, 밖 목록 빈 리스트
    assert score_citation_grounded({"candidates": [], "checklist": []}, GIVEN) == (0.0, [])


# --- 심판 LLM: 요청 만들기·파싱만 ---------------------------------------------


def test_build_judge_request_contains_question_answer_and_notes():
    req = build_judge_request(ANSWER, CASE, model="gpt-5-mini")
    assert req["model"] == "gpt-5-mini"
    user = req["messages"][-1]["content"]
    assert CASE["question"] in user
    assert CASE["notes"] in user
    assert "고형분 없으면 한도 계산 불가" in user  # 답 JSON이 들어간다
    system = req["messages"][0]["content"]
    assert "0" in system and "1" in system and "2" in system  # 척도 설명


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"score": 2, "reason": "notes의 근거가 다 있다"}', 2),
        ('```json\n{"score": 0, "reason": "x"}\n```', 0),
        ("score: 1", 1),
    ],
)
def test_parse_judge_reads_0_1_2(text, expected):
    assert parse_judge(text) == expected


@pytest.mark.parametrize("text", ['{"score": 3}', '{"score": -1}', "no number here", ""])
def test_parse_judge_rejects_out_of_range_or_missing(text):
    with pytest.raises(ValueError):
        parse_judge(text)


# --- 집계 ------------------------------------------------------------------------


def test_aggregate_returns_four_means_and_failed_case_ids():
    rows = [
        {"case_id": "a", "subpart": 1, "citation_recall": 1.0, "citation_grounded": 1.0, "judge": 2},
        {"case_id": "b", "subpart": 0, "citation_recall": 0.5, "citation_grounded": 1.0, "judge": 1},
        {"case_id": "c", "subpart": 1, "citation_recall": 0.0, "citation_grounded": 0.5, "judge": 0},
    ]
    out = aggregate(rows)
    assert out["n"] == 3
    assert out["subpart"] == pytest.approx(2 / 3)
    assert out["citation_recall"] == pytest.approx(0.5)
    assert out["citation_grounded"] == pytest.approx(2.5 / 3)
    assert out["judge"] == pytest.approx(1.0)
    # 실패 = Subpart 0 이거나 심판 0점 이거나 근거율 < 1
    assert out["failed"] == ["b", "c"]


# --- SUU-149: subpart 표기 정규화 ----------------------------------------------


@pytest.mark.parametrize("label", ["M", "Subpart M", "subpart m", " M "])
def test_score_subpart_normalizes_label_to_code(label):
    answer = {"candidates": [{"subpart": label, "criteria": []}], "checklist": []}
    assert score_subpart(answer, {"gold_subparts": ["M"]}) == 1


def test_score_subpart_does_not_accept_section_number_as_subpart():
    answer = {"candidates": [{"subpart": "40 CFR 63.320", "criteria": []}], "checklist": []}
    assert score_subpart(answer, {"gold_subparts": ["M"]}) == 0


# ---- SUU-151: 정답 Subpart가 여럿이면 A 빼고 하나만 맞아도 적중 ----


def _ans(*subparts):
    return {"candidates": [{"subpart": s, "criteria": []} for s in subparts], "checklist": []}


def test_score_subpart_hits_when_any_non_a_gold_is_present():
    assert score_subpart(_ans("PPPPP"), {"gold_subparts": ["ZZZZ", "PPPPP"]}) == 1
    assert score_subpart(_ans("HHH", "A"), {"gold_subparts": ["DDDDD", "HHH"]}) == 1


def test_score_subpart_does_not_count_general_provisions_a_alone():
    assert score_subpart(_ans("A"), {"gold_subparts": ["FFFFF", "A"]}) == 0
    assert score_subpart(_ans("A", "EE"), {"gold_subparts": ["FFFFF", "A"]}) == 0
    assert score_subpart(_ans("FFFFF"), {"gold_subparts": ["FFFFF", "A"]}) == 1


def test_score_subpart_counts_a_when_it_is_the_only_gold():
    assert score_subpart(_ans("A"), {"gold_subparts": ["A"]}) == 1
    assert score_subpart(_ans("ZZZZ"), {"gold_subparts": ["A"]}) == 0
