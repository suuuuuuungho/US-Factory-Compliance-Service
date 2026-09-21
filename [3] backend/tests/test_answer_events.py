"""SUU-177: answer_question이 on_event로 진행 단계를 알린다. search → found(sections) → answer.

색인·가짜 API는 test_answer.py 것을 그대로 쓴다.
"""
from app.answer import answer_question

from tests.test_answer import GOOD_ANSWER, fake_apis, make_index


def test_without_on_event_result_is_unchanged():
    _, apis = fake_apis(GOOD_ANSWER)
    out = answer_question("solvent welding", index=make_index(), **apis)
    assert out["answer"]["candidates"][0]["subpart"] == "PPPP"
    assert len(out["sections"]) == 10
    assert out["issues"] == []


def test_on_event_gets_search_found_answer_in_order():
    _, apis = fake_apis(GOOD_ANSWER)
    events = []
    out = answer_question("solvent welding", index=make_index(), on_event=events.append, **apis)

    assert [e["stage"] for e in events] == ["search", "found", "answer"]
    assert events[0] == {"stage": "search"}
    assert events[1]["sections"] == out["sections"]  # 찾은 조문 10개, 최종 결과와 같은 모양
    assert len(events[1]["sections"]) == 10
    assert events[1]["sections"][0] == {"section_key": "section-63.4481", "subpart": "PPPP"}
    assert events[2] == {"stage": "answer"}
