"""SUU-273: 실험용 선별셋 51건과 눈 검사 10건이 `[6] rag/eval/rag_eval_subset.json`에 고정되어 있는지 검사한다.

계획: `[1] docs/1) project/1_Project_full.md` "RAG 답변 품질 개선 과정" 절. 실험(1~6단계)은 51건으로, 최종 확인(7단계)만 102건으로 돌린다.
파일 모양: {"subset": [case_id × 51], "eye": [case_id × 10]}. 한 번 정하면 바꾸지 않는다.
"""
import json
from collections import Counter
from pathlib import Path

RAG = Path(__file__).parents[1]
SUBSET = RAG / "eval" / "rag_eval_subset.json"
CASES = RAG / "eval" / "rag_eval_case_v2.jsonl"
EYE_TEMPLATE = RAG / "eval" / "eye_check_template.md"


def load():
    cases = {}
    for line in CASES.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        cases[case["case_id"]] = case
    return json.loads(SUBSET.read_text(encoding="utf-8")), cases


def primary_subparts(case: dict) -> frozenset:
    gold = set(case["gold_subparts"])
    return frozenset((gold - {"A"}) or gold)


def test_subset_has_51_unique_case_ids_from_eval_set_v2():
    subset, cases = load()
    ids = subset["subset"]
    assert len(ids) == 51
    assert len(set(ids)) == 51
    assert all(i in cases for i in ids)


def test_subset_keeps_source_ratio_of_full_set():
    # 전체 102건 = ADI 69 · Dashboard 33 → 절반이면 ADI 34~35 · Dashboard 16~17
    subset, cases = load()
    by_source = Counter(cases[i]["source"] for i in subset["subset"])
    assert by_source["adi"] in (34, 35)
    assert by_source["dashboard"] in (16, 17)


def test_subset_spreads_over_many_gold_subparts():
    # 정답 Subpart(A 제외)가 한쪽에 몰리지 않는다: 같은 정답 조합은 최대 2건, 서로 다른 조합 40개 이상
    subset, cases = load()
    combos = Counter(primary_subparts(cases[i]) for i in subset["subset"])
    assert max(combos.values()) <= 2
    assert len(combos) >= 40


def test_eye_check_cases_are_10_inside_subset_with_distinct_gold_subparts():
    subset, cases = load()
    eye = subset["eye"]
    assert len(eye) == 10 and len(set(eye)) == 10
    assert set(eye) <= set(subset["subset"])
    combos = [primary_subparts(cases[i]) for i in eye]
    assert len(set(combos)) == 10  # 정답 Subpart가 서로 다르다
    by_source = Counter(cases[i]["source"] for i in eye)
    assert by_source["adi"] >= 1 and by_source["dashboard"] >= 1


def test_eye_check_template_lists_every_eye_case():
    subset, _ = load()
    text = EYE_TEMPLATE.read_text(encoding="utf-8")
    for case_id in subset["eye"]:
        assert case_id in text
    for column in ["뒷받침", "EPA 이유", "답할 수 있는"]:
        assert column in text, f"눈 검사 틀에 '{column}' 칸이 없다"
