"""SUU-278: 계획 `[1] docs/3) rag/2_rag 구축 계획.md` [7] 선택 근거표가 채워져 있는지 검사한다.

1단계(답 모양)는 관문 채택, 5단계(검증문)·7단계(전체 확인)·8단계(최종 조합)는 숫자가 들어 있다.
2·3·4·6단계는 돌리지 않았으므로 "건너뜀"과 이유가 적혀 있다. 빈 괄호 "( )"가 남아 있으면 안 채운 것이다.
"""
import re
from pathlib import Path

PLAN = Path(__file__).parents[2] / "[1] docs" / "3) rag" / "2_rag 구축 계획.md"


def choice_lines() -> dict[int, str]:
    text = PLAN.read_text(encoding="utf-8")
    block = text.split("## [7]", 1)[1].split("\n## ", 1)[0]
    lines = {}
    for m in re.finditer(r"^(\d)\) (.+)$", block, re.M):
        lines[int(m.group(1))] = m.group(2)
    return lines


def test_plan_choice_table_has_eight_lines():
    assert set(choice_lines()) == {1, 2, 3, 4, 5, 6, 7, 8}


def test_stage_1_picked_gates_by_the_rule():
    line = choice_lines()[1]
    assert "( )" not in line
    assert "고른 것: 관문" in line or "고른 것: B 관문" in line


def test_skipped_stages_say_so_with_a_reason():
    lines = choice_lines()
    for n in (2, 3, 4, 6):
        assert "건너뜀" in lines[n], n
        assert "( )" not in lines[n], n


def test_verification_full_check_and_final_combination_are_filled():
    lines = choice_lines()
    for n in (5, 7, 8):
        assert "( )" not in lines[n], n
    assert "102건" in lines[7] and "gpt-5-mini" in lines[8]
