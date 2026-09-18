"""SUU-138: 상위 조문으로 판정 기준표(후보 Subpart + 기준 + 근거 조문) 답을 만들고 채점한다. 최종 판정은 없다."""
from ecfr_answer import SECTION_CHARS, build_answer_prompt, parse_answer, score_answer

SECTIONS = [
    {"section_key": "section-63.4481", "subpart": "PPPP", "text": "a" * 20000},
    {"section_key": "section-63.4581", "subpart": "PPPP", "text": "Definitions."},
]
QUESTION = "We bond polymer parts with methylene chloride."


def test_prompt_has_question_sections_and_no_verdict_rule():
    prompt = build_answer_prompt(QUESTION, SECTIONS)
    assert QUESTION in prompt
    assert "section-63.4481 (Subpart PPPP)" in prompt and "Definitions." in prompt
    assert "a" * SECTION_CHARS in prompt and "a" * (SECTION_CHARS + 1) not in prompt  # 조문 전문은 상한까지만
    assert "Do NOT" in prompt and "applies" in prompt  # 판정하지 말라는 지시


def test_parse_answer_reads_fenced_json_and_falls_back_to_empty():
    text = 'Here:\n```json\n{"candidates": [{"subpart": "PPPP", "name": "Plastic parts", "criteria": [{"citation": "63.4481(a)", "check": "coats plastic parts"}], "you_should_check": ["annual usage"]}]}\n```'
    answer = parse_answer(text)
    assert answer["candidates"][0]["subpart"] == "PPPP"
    assert answer["candidates"][0]["criteria"][0]["citation"] == "63.4481(a)"
    assert parse_answer("no json here") == {"candidates": []}
    assert parse_answer('{"candidates": "oops"}') == {"candidates": []}


def test_score_answer_subpart_citation_recall_and_grounding():
    answer = {"candidates": [
        {"subpart": "PPPP", "criteria": [{"citation": "63.4481(a)"}, {"citation": "§ 63.4490(b)"}, {"citation": "63.9999"}]},
        {"subpart": "MMMM", "criteria": [{"citation": "40 CFR 63.3881"}]},
    ]}
    s = score_answer(answer, gold_subparts=["PPPP"], gold_citations=["40 CFR 63.4481(a)", "40 CFR 63.4581", "40 CFR 63.4490"],
                     context_keys=["section-63.4481", "section-63.4490", "section-63.3881"])
    assert s["subpart_hit"] is True           # 정답 Subpart가 후보에 있다
    assert s["citation_recall"] == 2 / 3      # 정답 조문 3개 중 63.4481·63.4490 인용, 63.4581 빠짐
    assert s["citation_grounded"] == 3 / 4    # 인용 4개 중 63.9999는 준 조문 밖
    assert s["n_criteria"] == 4

    empty = score_answer({"candidates": []}, gold_subparts=["PPPP"], gold_citations=["40 CFR 63.4481"], context_keys=[])
    assert empty == {"subpart_hit": False, "citation_recall": 0.0, "citation_grounded": 0.0, "n_criteria": 0}
