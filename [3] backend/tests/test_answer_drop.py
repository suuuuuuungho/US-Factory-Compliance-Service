"""SUU-282: answer_question이 넘겨준 조문 밖의 인용을 지워서 돌려주고, 지운 내용은 issues에 남긴다.

색인·가짜 API는 test_answer.py 것을 그대로 쓴다.
"""
import json

from app.answer import answer_question

from tests.test_answer import GOOD_ANSWER, fake_apis, make_index

OUTSIDE_ANSWER = json.dumps({
    "candidates": [{"subpart": "PPPP", "title": "Surface Coating of Plastic Parts",
                    "criteria": [
                        {"criterion": "coats plastic parts", "citations": ["40 CFR 63.4481(a)", "40 CFR 63.9(b)"]},
                        {"criterion": "made up", "citations": ["40 CFR 63.9(b)"]},
                    ]}],
    "checklist": ["Is the facility a major source of HAP?"],
})


def test_answer_question_drops_outside_citation_and_notes_it():
    _, apis = fake_apis(OUTSIDE_ANSWER)
    out = answer_question("solvent welding", index=make_index(), **apis)
    criteria = out["answer"]["candidates"][0]["criteria"]
    assert [c["criterion"] for c in criteria] == ["coats plastic parts"]
    assert criteria[0]["citations"] == ["40 CFR 63.4481(a)"]
    assert any("section-63.9" in i for i in out["issues"])
    assert any("criterion dropped" in i for i in out["issues"])


def test_answer_question_unchanged_when_all_citations_inside():
    _, apis = fake_apis(GOOD_ANSWER)
    out = answer_question("solvent welding", index=make_index(), **apis)
    assert out["answer"] == json.loads(GOOD_ANSWER)
    assert out["issues"] == []
