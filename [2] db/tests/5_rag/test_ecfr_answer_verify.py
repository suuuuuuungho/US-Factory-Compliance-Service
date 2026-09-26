"""SUU-278: 나가기 전 검증문 — 답이 나온 뒤 $0 규칙으로 관문마다 G0·G1을 검사해 미달 관문을 지우고 `missing`으로 옮긴다.

계획 `[1] docs/1) project/1_Project_full.md` "RAG 답변 품질 개선 과정" 절. LLM을 쓰지 않는다. 채점기(`ecfr_answer_score`)와 같은 판정이다:
- G0: 관문 인용이 넘겨준 조문(given) 밖이면 그 관문을 지운다. 63.xxxx 모양이 아닌 인용(표·부록)은 채점기처럼 무시한다
- G1: 관문 발췌(quote)가 인용 조문 원문에 없으면(공백·대소문자 무시) 그 관문을 지운다
- 지운 관문은 `missing`에 "{type}: {question}"으로 남긴다. 지운 관문만 가리키던 checklist 항목도 지운다
"""
import copy

from ecfr_answer import verify_answer
from ecfr_answer_score import score_answer_v2

CASE = {"case_id": "c1", "question": "q", "gold_subparts": ["PPPP"], "gold_citations": ["40 CFR 63.4481(a)", "40 CFR 63.4581"], "notes": "n"}

TEXTS = {
    "section-63.4481": "§ 63.4481 Am I subject to this subpart? (a) You are subject if you own or operate a plastic parts "
    "and products surface coating facility that is a major source of HAP.",
    "section-63.4581": "§ 63.4581 What definitions apply? Adhesive means any chemical substance that is applied for the "
    "purpose of bonding two surfaces together other than by mechanical means.",
    "section-63.2": "§ 63.2 Definitions. Major source means any stationary source that emits 10 tons per year of any HAP.",
}
GIVEN = list(TEXTS)

OK_SOURCE = {"type": "affected_source", "question": "접착제인가?", "test": "접착제면 적용 쪽",
             "citations": ["40 CFR 63.4581"], "quote": "adhesive MEANS any chemical substance"}
OK_MAJOR = {"type": "major_or_area", "question": "major source인가?", "test": "major면 적용 쪽",
            "citations": ["40 CFR 63.4481(a)", "40 CFR 63.2"], "quote": "Major source means any stationary source"}
OUTSIDE = {"type": "threshold", "question": "문턱값을 넘는가?", "test": "넘으면 적용 쪽",
           "citations": ["40 CFR 63.4490(a)"], "quote": "kilograms of organic HAP emitted per liter"}  # 63.4490은 안 넘겨준 조문
BAD_QUOTE = {"type": "exemption", "question": "면제인가?", "test": "면제면 비적용 쪽",
             "citations": ["40 CFR 63.4481(a)"], "quote": "you are exempt if you use less than 250 gallons"}  # 원문에 없는 문장


def _answer(gates, checklist, *, missing=()):
    return {"candidates": [{"subpart": "PPPP", "title": "Plastic Parts", "gates": copy.deepcopy(gates), "missing": list(missing)}],
            "checklist": copy.deepcopy(checklist)}


def test_good_answer_is_returned_unchanged_and_input_is_not_mutated():
    answer = _answer([OK_SOURCE, OK_MAJOR], [{"item": "접착제 여부", "gate": "affected_source"}, {"item": "HAP 배출량", "gate": "major_or_area"}])
    before = copy.deepcopy(answer)
    assert verify_answer(answer, GIVEN, TEXTS) == before
    assert answer == before


def test_gate_citing_a_section_outside_given_is_moved_to_missing():
    answer = _answer([OK_SOURCE, OUTSIDE], [{"item": "접착제 여부", "gate": "affected_source"}])
    out = verify_answer(answer, GIVEN, TEXTS)
    cand = out["candidates"][0]
    assert [g["type"] for g in cand["gates"]] == ["affected_source"]
    assert cand["missing"] == ["threshold: 문턱값을 넘는가?"]
    assert out["checklist"] == [{"item": "접착제 여부", "gate": "affected_source"}]


def test_gate_whose_quote_is_not_in_its_cited_sections_is_moved_to_missing():
    answer = _answer([BAD_QUOTE, OK_MAJOR], [{"item": "HAP 배출량", "gate": "major_or_area"}], missing=["이미 있던 빈칸"])
    out = verify_answer(answer, GIVEN, TEXTS)
    cand = out["candidates"][0]
    assert [g["type"] for g in cand["gates"]] == ["major_or_area"]
    assert cand["missing"] == ["이미 있던 빈칸", "exemption: 면제인가?"]  # 원래 있던 missing 뒤에 붙인다


def test_checklist_items_pointing_only_at_removed_gates_are_dropped():
    answer = _answer([OK_SOURCE, OUTSIDE, BAD_QUOTE],
                     [{"item": "접착제 여부", "gate": "affected_source"}, {"item": "문턱값", "gate": "threshold"}, {"item": "면제", "gate": "exemption"}])
    out = verify_answer(answer, GIVEN, TEXTS)
    assert out["checklist"] == [{"item": "접착제 여부", "gate": "affected_source"}]


def test_candidate_keeps_its_subpart_even_when_every_gate_is_removed():
    answer = _answer([OUTSIDE], [{"item": "문턱값", "gate": "threshold"}])
    out = verify_answer(answer, GIVEN, TEXTS)
    assert out["candidates"][0]["subpart"] == "PPPP" and out["candidates"][0]["gates"] == []
    assert out["candidates"][0]["missing"] == ["threshold: 문턱값을 넘는가?"] and out["checklist"] == []


def test_verified_answer_scores_g0_g1_g4_one():
    answer = _answer([OK_SOURCE, OUTSIDE, BAD_QUOTE, OK_MAJOR],
                     [{"item": "접착제 여부", "gate": "affected_source"}, {"item": "문턱값", "gate": "threshold"}])
    raw = score_answer_v2(answer, CASE, TEXTS)
    assert raw["g0_grounded"] < 1.0 and raw["g1_quote"] < 1.0 and raw["failed"] is True  # G4는 검증 전에도 1.0(모든 항목이 있는 관문을 가리킴)
    scores = score_answer_v2(verify_answer(answer, GIVEN, TEXTS), CASE, TEXTS)
    assert scores["g0_grounded"] == 1.0 and scores["g0_outside"] == []
    assert scores["g1_quote"] == 1.0 and scores["g1_mismatched"] == []
    assert scores["g4_checklist"] == 1.0 and scores["g2_subpart"] == 1 and scores["failed"] is False
