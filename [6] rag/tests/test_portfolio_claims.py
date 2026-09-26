"""SUU-281: 포트폴리오 `[1] docs/1) project/2_Portfolio.md`의 주장이 저장소 실측과 맞는지 검사한다.

옛 과장 문구가 없고, 임베더 비교(0단계)·정직한 합격선 문구·직접 판단 사례 3개가 들어 있어야 한다.
"""
from pathlib import Path

DOC = Path(__file__).parents[2] / "[1] docs" / "1) project" / "2_Portfolio.md"


def text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_old_overclaims_are_gone():
    t = text()
    for old in ("구조적으로 막았", "PostgreDB", "5단계 중 가장 크게"):
        assert old not in t, old


def test_embedder_stage_has_both_scores():
    stage = text().split("0) 임베더 선택", 1)[1].split("\n  1)", 1)[0]
    assert "0.297" in stage and "0.437" in stage


def test_pass_line_wording_is_honest():
    assert text().count("퇴보 방지선") >= 2


def test_own_judgement_section_lists_three_cases():
    sec = text().split("5. 실험 결과를 보고 직접 내린 결정", 1)[1].split("\n## ", 1)[0]
    for case in ("Subpart RRR", "Subpart A 고정 삽입", "관문(gates)"):
        assert case in sec, case
