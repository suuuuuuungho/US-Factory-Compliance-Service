"""SUU-273: 채점기 v2 — 관문(gate) 모양 답을 $0 규칙 6개(G0~G5)로 채점한다. LLM 심판 없음.

답 모양·지표 정의는 `[1] docs/3) rag/2_rag 구축 계획.md` [4]·[5].
G0 근거율(인용이 넘겨준 조문 안) · G1 발췌 일치율(quote가 인용 조문 원문에 있나, 공백·대소문자 무시)
· G2 Subpart 적중(A는 정답이 A뿐일 때만) · G3 인용 Recall(조문 단위) · G4 체크리스트 연결률 · G5 비용·지연.
"""
import pytest

from ecfr_answer_score import (
    aggregate_v2,
    score_answer_v2,
    score_checklist_link,
    score_citation_grounded,
    score_citation_recall,
    score_quote_match,
)

CASE = {
    "case_id": "dashboard-king-systems-2020-06-16",
    "question": "Does the NESHAP for surface coating of plastic parts cover this solvent welding step?",
    "gold_subparts": ["PPPP"],
    "gold_citations": ["40 CFR 63.4481(a)", "40 CFR 63.4581", "40 CFR 63.4490"],
    "notes": "Not subject to PPPP.",
}

# 넘겨준 조문 원문 (section key → 전문). 발췌(quote) 검사는 이 텍스트 안에서 한다
SECTION_TEXTS = {
    "section-63.4481": "§ 63.4481 Am I subject to this subpart? (a) You are subject if you own or operate a plastic parts "
    "and products surface coating facility that is a major source of HAP.",
    "section-63.4581": "§ 63.4581 What definitions apply? Adhesive means any chemical substance that is applied for the "
    "purpose of bonding two surfaces together other than by mechanical means.",
    "section-63.4490": "§ 63.4490 What emission limits must I meet? (a) kilograms (kg) of organic HAP emitted per liter "
    "of coating solids used.",
    "section-63.2": "§ 63.2 Definitions. Major source means any stationary source that emits 10 tons per year of any HAP.",
}
GIVEN = list(SECTION_TEXTS)

# 답 1: 정상. 인용은 다 넘겨준 조문 안, 발췌는 원문 그대로(공백·대소문자만 다름), 체크리스트는 관문과 이어짐
GOOD = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts and Products",
            "gates": [
                {
                    "type": "affected_source",
                    "question": "두 면을 붙이려고 바르는 물질이 접착제에 해당하는가?",
                    "test": "접착제이면 코팅으로 보아 적용 쪽",
                    "citations": ["40 CFR 63.4581"],
                    "quote": "adhesive means any chemical   substance that is applied for the purpose of bonding two surfaces together",
                },
                {
                    "type": "threshold",
                    "question": "바르는 물질에 고형분이 조금이라도 들어 있는가?",
                    "test": "고형분이 전혀 없으면 비적용 쪽",
                    "citations": ["40 CFR 63.4490(a)"],
                    "quote": "kilograms (kg) of organic HAP emitted per liter of coating solids used",
                },
            ],
            "missing": [],
        }
    ],
    "checklist": [
        {"item": "SDS에서 고형분 함량을 확인한다", "gate": "threshold"},
        {"item": "접합 뒤 마른 막이 남는지 확인한다", "gate": "affected_source"},
    ],
}

# 답 2: 넘겨준 조문 밖 인용(63.9). 발췌·체크리스트는 정상
OUTSIDE = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts and Products",
            "gates": [
                {
                    "type": "affected_source",
                    "question": "접착제인가?",
                    "test": "접착제이면 적용 쪽",
                    "citations": ["40 CFR 63.4581"],
                    "quote": "Adhesive means any chemical substance that is applied for the purpose of bonding two surfaces together",
                },
                {
                    "type": "compliance_date",
                    "question": "언제부터 지켜야 하는가?",
                    "test": "신고 기한이 지났으면 적용 쪽",
                    "citations": ["40 CFR 63.9(b)"],  # 넘겨준 조문 밖 → 지어냄
                    "quote": "any text",
                },
            ],
            "missing": [],
        }
    ],
    "checklist": [{"item": "접착제 여부", "gate": "affected_source"}],
}

# 답 3: 발췌가 원문에 없음 + 체크리스트가 없는 관문을 가리킴. 인용은 안에 있음
BAD_QUOTE = {
    "candidates": [
        {
            "subpart": "PPPP",
            "title": "Surface Coating of Plastic Parts and Products",
            "gates": [
                {
                    "type": "affected_source",
                    "question": "접착제인가?",
                    "test": "접착제이면 적용 쪽",
                    "citations": ["40 CFR 63.4581"],
                    "quote": "Adhesive means any chemical substance that is applied for the purpose of bonding two surfaces together",
                },
                {
                    "type": "major_or_area",
                    "question": "주요 배출원인가?",
                    "test": "10톤 넘으면 적용 쪽",
                    "citations": ["40 CFR 63.2"],
                    "quote": "Major source means any source that emits 25 tons per year",  # 원문은 10 tons → 없는 말
                },
            ],
            "missing": ["63.4490 한도는 넘겨받지 못함"],
        }
    ],
    "checklist": [
        {"item": "HAP 연간 배출량", "gate": "major_or_area"},
        {"item": "고형분 함량", "gate": "threshold"},  # 그런 관문이 답에 없음
    ],
}


# --- G1 발췌 일치 -------------------------------------------------------------


def test_score_quote_match_ignores_whitespace_and_case_and_flags_missing_quotes():
    assert score_quote_match(GOOD, SECTION_TEXTS) == (1.0, [])
    ratio, mismatched = score_quote_match(BAD_QUOTE, SECTION_TEXTS)
    assert ratio == pytest.approx(1 / 2)
    assert mismatched == ["PPPP/major_or_area"]  # "<subpart>/<type>" 로 어느 관문인지
    # 관문이 하나도 없으면 0.0, 빈 목록
    assert score_quote_match({"candidates": [], "checklist": []}, SECTION_TEXTS) == (0.0, [])


def test_score_quote_match_requires_quote_inside_the_cited_section():
    # 발췌가 넘겨준 다른 조문에는 있어도 그 관문이 인용한 조문에 없으면 불일치
    answer = {
        "candidates": [{"subpart": "PPPP", "title": "x", "gates": [
            {"type": "threshold", "question": "q", "test": "t", "citations": ["40 CFR 63.4581"],
             "quote": "kilograms (kg) of organic HAP emitted per liter of coating solids used"}], "missing": []}],
        "checklist": [],
    }
    assert score_quote_match(answer, SECTION_TEXTS) == (0.0, ["PPPP/threshold"])
    # 발췌 칸이 비어 있으면 불일치
    answer["candidates"][0]["gates"][0]["quote"] = ""
    assert score_quote_match(answer, SECTION_TEXTS) == (0.0, ["PPPP/threshold"])


# --- G4 체크리스트 연결 ---------------------------------------------------------


def test_score_checklist_link_is_share_of_items_pointing_to_an_existing_gate_type():
    assert score_checklist_link(GOOD) == 1.0
    assert score_checklist_link(BAD_QUOTE) == pytest.approx(1 / 2)  # threshold 관문이 없다
    assert score_checklist_link({"candidates": [], "checklist": []}) == 0.0


# --- 손으로 만든 답 3개 → 케이스 한 줄 ------------------------------------------------


def test_score_answer_v2_good_answer_gets_full_marks_on_g0_to_g4():
    row = score_answer_v2(GOOD, CASE, SECTION_TEXTS)
    assert row["scorer_version"] == "v2"
    assert row["case_id"] == CASE["case_id"]
    assert row["g0_grounded"] == 1.0 and row["g0_outside"] == []
    assert row["g1_quote"] == 1.0 and row["g1_mismatched"] == []
    assert row["g2_subpart"] == 1
    assert row["g3_citation_recall"] == pytest.approx(2 / 3)  # 정답 {4481, 4581, 4490} 중 4581·4490
    assert row["g4_checklist"] == 1.0
    assert row["failed"] is False


def test_score_answer_v2_flags_citation_outside_given_sections_as_failure():
    row = score_answer_v2(OUTSIDE, CASE, SECTION_TEXTS)
    assert row["g0_grounded"] == pytest.approx(1 / 2)  # {4581, 63.9} 중 63.9 밖
    assert row["g0_outside"] == ["section-63.9"]
    assert row["g1_quote"] == pytest.approx(1 / 2)  # 밖 인용의 발췌는 대조할 원문이 없으니 불일치
    assert row["g2_subpart"] == 1
    assert row["g3_citation_recall"] == pytest.approx(1 / 3)
    assert row["g4_checklist"] == 1.0
    assert row["failed"] is True  # G0 < 1 이면 그 케이스는 실패


def test_score_answer_v2_flags_quote_not_in_source_text():
    row = score_answer_v2(BAD_QUOTE, CASE, SECTION_TEXTS)
    assert row["g0_grounded"] == 1.0
    assert row["g1_quote"] == pytest.approx(1 / 2)
    assert row["g1_mismatched"] == ["PPPP/major_or_area"]
    assert row["g2_subpart"] == 1
    assert row["g3_citation_recall"] == pytest.approx(1 / 3)  # 4581만
    assert row["g4_checklist"] == pytest.approx(1 / 2)
    assert row["failed"] is False  # 발췌 불일치는 지표로만 깎인다. 케이스 실패는 G0 < 1 또는 G2 == 0


def test_score_answer_v2_marks_missed_subpart_as_failure():
    answer = {"candidates": [{"subpart": "MMMM", "title": "x", "gates": [], "missing": []}], "checklist": []}
    row = score_answer_v2(answer, CASE, SECTION_TEXTS)
    assert row["g2_subpart"] == 0
    assert row["failed"] is True


def test_score_answer_v2_is_deterministic():
    assert score_answer_v2(GOOD, CASE, SECTION_TEXTS) == score_answer_v2(GOOD, CASE, SECTION_TEXTS)
    assert score_answer_v2(BAD_QUOTE, CASE, SECTION_TEXTS) == score_answer_v2(BAD_QUOTE, CASE, SECTION_TEXTS)


# --- 집계 ------------------------------------------------------------------------


def test_aggregate_v2_means_six_metrics_and_lists_failed_cases():
    rows = [
        {"case_id": "a", "g0_grounded": 1.0, "g1_quote": 1.0, "g2_subpart": 1, "g3_citation_recall": 1.0,
         "g4_checklist": 1.0, "cost_usd": 0.02, "latency_s": 40.0, "failed": False},
        {"case_id": "b", "g0_grounded": 0.5, "g1_quote": 0.5, "g2_subpart": 1, "g3_citation_recall": 0.5,
         "g4_checklist": 1.0, "cost_usd": 0.04, "latency_s": 60.0, "failed": True},
        {"case_id": "c", "g0_grounded": 1.0, "g1_quote": 0.0, "g2_subpart": 0, "g3_citation_recall": 0.0,
         "g4_checklist": 0.0, "cost_usd": 0.03, "latency_s": 50.0, "failed": True},
    ]
    out = aggregate_v2(rows)
    assert out["scorer_version"] == "v2"
    assert out["n"] == 3
    assert out["g0_grounded"] == pytest.approx(2.5 / 3)
    assert out["g1_quote"] == pytest.approx(0.5)
    assert out["g2_subpart"] == pytest.approx(2 / 3)
    assert out["g3_citation_recall"] == pytest.approx(0.5)
    assert out["g4_checklist"] == pytest.approx(2 / 3)
    assert out["g5_cost_usd"] == pytest.approx(0.03)  # 질문당 평균 달러
    assert out["g5_latency_s"] == pytest.approx(50.0)  # 질문당 중앙값 초
    assert out["failed"] == ["b", "c"]
    assert aggregate_v2([])["n"] == 0


# --- v1 함수가 관문 모양도 읽는다 (같은 함수로 두 모양을 잰다) ----------------------------


def test_v1_citation_functions_also_read_gate_shaped_answers():
    assert score_citation_recall(GOOD, CASE) == pytest.approx(2 / 3)
    grounded, outside = score_citation_grounded(OUTSIDE, GIVEN)
    assert grounded == pytest.approx(1 / 2)
    assert outside == ["section-63.9"]
