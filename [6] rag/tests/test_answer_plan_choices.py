"""SUU-278·SUU-279: 계획 `[1] docs/3) rag/2_rag 구축 계획.md` [7] 선택 근거표가 채워져 있고 최종 결정과 맞는지 검사한다.

1단계(답 모양)는 관문 run 뒤 나열로 재결정했다(SUU-279). 5단계(검증문)·7단계(전체 확인)·8단계(최종 조합)는 숫자가 들어 있다.
2·3·4·6단계는 돌리지 않았으므로 "건너뜀"과 이유가 적혀 있다. 빈 괄호 "( )"가 남아 있으면 안 채운 것이다.
[0] 한 줄 요약과 [6] 8단계(서비스 연결)는 최종 모양(나열)을 말해야 한다.
"""
import re
from pathlib import Path

PLAN = Path(__file__).parents[2] / "[1] docs" / "3) rag" / "2_rag 구축 계획.md"
CRITERIA_RUN_51 = "2026-09-26_answer_criteria_gpt-5-mini_subset51"
GATES_RUN_51 = "2026-09-26_answer_gates_gpt-5-mini_subset51_out20k"
CRITERIA_RUN_102 = "2026-09-19_answer_v2_gpt-5-mini_top10"


def section(tag: str) -> str:
    text = PLAN.read_text(encoding="utf-8")
    return text.split(f"## [{tag}]", 1)[1].split("\n## ", 1)[0]


def choice_lines() -> dict[int, str]:
    lines = {}
    for m in re.finditer(r"^(\d)\) (.+)$", section("7"), re.M):
        lines[int(m.group(1))] = m.group(2)
    return lines


def test_plan_choice_table_has_eight_lines():
    assert set(choice_lines()) == {1, 2, 3, 4, 5, 6, 7, 8}


def test_stage_1_picked_criteria_and_keeps_both_runs():
    line = choice_lines()[1]
    assert "( )" not in line
    assert "고른 것: 나열" in line
    assert CRITERIA_RUN_51 in line and GATES_RUN_51 in line  # 떨어진 관문 run도 남긴다


def test_skipped_stages_say_so_with_a_reason():
    lines = choice_lines()
    for n in (2, 3, 4, 6):
        assert "건너뜀" in lines[n], n
        assert "( )" not in lines[n], n


def test_verification_and_full_check_are_filled():
    lines = choice_lines()
    for n in (5, 7):
        assert "( )" not in lines[n], n
    assert "102건" in lines[7]


def test_final_combination_is_criteria_on_the_102_case_run():
    line = choice_lines()[8]
    assert "( )" not in line
    assert "모양 나열" in line and "gpt-5-mini" in line and CRITERIA_RUN_102 in line
    assert "모양 관문" not in line


def test_summary_and_service_step_describe_the_criteria_shape():
    summary = section("0")
    assert "나열" in summary and "관문" not in summary
    step_8 = section("6").split("8단계. 서비스 연결", 1)[1].split("\n\n", 1)[0]
    assert "나열" in step_8 and "관문" not in step_8
