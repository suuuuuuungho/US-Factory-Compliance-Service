"""SUU-46: ADI·CAA Dashboard 회신 30건을 읽어 만든 RAG 평가 정답지 `[6] rag/eval/rag_eval_case.jsonl` 검사.

정답지는 사람이 읽어 쓴 데이터 파일이라 구현 모듈이 없다. 파일이 규칙대로 채워졌는지만 본다.
조문 존재 여부는 SUU-44 결과(nodes.jsonl, 2026-09-11)에서 뽑아 둔 fixture와 대조한다.
"""
import json
import re
from collections import Counter
from pathlib import Path

RAG = Path(__file__).parents[1]
CASES = RAG / "eval" / "rag_eval_case.jsonl"
INDEX = json.loads((RAG / "tests" / "fixtures" / "ecfr_part63_index_2026-09-11.json").read_text(encoding="utf-8"))

FIELDS = ["case_id", "question", "gold_subparts", "gold_citations", "source", "source_ref", "notes"]
CITATION = re.compile(r"^40 CFR (63\.\d+)(\([A-Za-z0-9]+\))*$")
SUBPART = re.compile(r"^[A-Z]{1,7}$")
MIN_CASES = 30
MAX_PER_SUBPART = 3


def load_cases():
    lines = CASES.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_has_thirty_cases_with_all_fields():
    cases = load_cases()
    assert len(cases) >= MIN_CASES

    for case in cases:
        assert list(case) == FIELDS, case.get("case_id")
        assert case["case_id"] and isinstance(case["case_id"], str)
        assert case["question"].strip()
        assert case["gold_subparts"] and all(isinstance(s, str) for s in case["gold_subparts"])
        assert case["gold_citations"] and all(isinstance(c, str) for c in case["gold_citations"])
        assert case["source"] in {"adi", "dashboard"}
        assert case["source_ref"].strip()
        assert case["notes"].strip()

    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_question_does_not_leak_answer():
    for case in load_cases():
        question = case["question"]
        # 조문 번호 (63.1, 63.11607, 63.2(a) …) 는 질문에 없다
        assert not re.search(r"\b63\.\d", question), case["case_id"]
        for code in case["gold_subparts"]:
            # "Subpart PPPP" 처럼 이름을 부르지 않는다
            assert not re.search(rf"\bsubpart\s+{code}\b", question, re.IGNORECASE), case["case_id"]
            # 코드 자체도 단어로 나오지 않는다 (한 글자 코드 A, B 는 영어 단어와 겹쳐서 위 검사만 한다)
            if len(code) >= 2:
                assert not re.search(rf"\b{code}\b", question), case["case_id"]


def test_gold_exists_in_part63_and_subparts_spread():
    cases = load_cases()
    sections = set(INDEX["sections"])
    subparts = set(INDEX["subparts"])

    for case in cases:
        for citation in case["gold_citations"]:
            match = CITATION.match(citation)
            assert match, (case["case_id"], citation)
            assert match.group(1) in sections, (case["case_id"], citation)
        for code in case["gold_subparts"]:
            assert SUBPART.match(code), (case["case_id"], code)
            assert code in subparts, (case["case_id"], code)

    # gold_subparts[0] = 질문 대상 주 Subpart. 한 업종에 몰리지 않는다
    primary = Counter(c["gold_subparts"][0] for c in cases)
    assert max(primary.values()) <= MAX_PER_SUBPART, primary.most_common(3)
