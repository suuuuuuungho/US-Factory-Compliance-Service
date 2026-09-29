"""SUU-296: 문서 md 규칙 검사기 (`[1] docs/4) workflow/3_doc_rules.md` 6절)."""

from pathlib import Path

import pytest

from md_check import check, fix, main

PROJECT = Path(__file__).parents[3] / "1) project"

# 규칙을 모두 지키는 최소 문서. 9줄. 케이스 본문은 11번째 줄부터 붙는다.
HEAD = "# 문서 제목\n\n표지 문단.\n\n## 첫 장\n\n> 핵심 문장입니다.\n\n본문 문단.\n"


def doc(body: str) -> str:
    return HEAD + "\n" + body


def body_line(k: int) -> int:
    """케이스 본문의 k번째 줄이 문서 전체에서 몇 번째 줄인지."""
    return 10 + k


# ---------- 완료 기준 1: 자동으로 고침 7가지 ----------

FIX_CASES = {
    "trailing_space": ("문단입니다.  \n", "문단입니다.\n"),
    "blank_lines": ("문단 하나.\n\n\n\n문단 둘.\n", "문단 하나.\n\n문단 둘.\n"),
    "tab": ("- 항목\n\t- 하위\n", "- 항목\n    - 하위\n"),
    "star_plus_bullet": ("* 하나\n+ 둘\n    * 셋\n", "- 하나\n- 둘\n    - 셋\n"),
    "heading_number_dot": ("## 1. 문제\n", "## 문제\n"),
    "heading_number_section": ("### 1.1 배경\n", "### 배경\n"),
    "heading_number_circled": ("## ① 포인트\n", "## 포인트\n"),
    "heading_number_sol": ("### Sol_1 해결\n", "### 해결\n"),
    "heading_number_ordinal": ("## 1st. 단계\n", "## 단계\n"),
    "renumber": ("1. 가\n3. 나\n3. 다\n", "1. 가\n2. 나\n3. 다\n"),
    "renumber_from_zero": ("0. 가\n1. 나\n", "1. 가\n2. 나\n"),
    "renumber_nested": (
        "1. 가\n    1. 가1\n    5. 가2\n2. 나\n    3. 나1\n",
        "1. 가\n    1. 가1\n    2. 가2\n2. 나\n    1. 나1\n",
    ),
    "renumber_new_block": ("1. 가\n\n5. 나\n", "1. 가\n\n1. 나\n"),
    "evidence_label": ("[근거] 40 CFR 70.6\n", "근거: 40 CFR 70.6\n"),
    "evidence_label_in_list": ("- 항목\n    - [근거] 70.5\n", "- 항목\n    - 근거: 70.5\n"),
}


@pytest.mark.parametrize("name", FIX_CASES)
def test_fix_auto_fixable(name):
    before, after = FIX_CASES[name]
    assert fix(before) == after


NO_FIX_CASES = {
    "word_starting_with_digit": "### 1인 개발이 가능했던 이유\n",
    "bold_line": "**Q.** 질문인가요?\n",
    "code_block": "```text\n문단  \n\t탭\n* 별\n1. 가\n3. 나\n```\n",
}


@pytest.mark.parametrize("name", NO_FIX_CASES)
def test_fix_leaves_valid_text_alone(name):
    text = NO_FIX_CASES[name]
    assert fix(text) == text


def test_main_fixes_file_and_keeps_crlf(tmp_path):
    path = tmp_path / "a.md"
    path.write_bytes(doc("문단.  \n\n\n다음 문단.\n").replace("\n", "\r\n").encode("utf-8"))

    assert main([str(path)]) == 0
    assert path.read_bytes() == doc("문단.\n\n다음 문단.\n").replace("\n", "\r\n").encode("utf-8")


# ---------- 완료 기준 2: 알려 주기만 함 11가지 ----------

REPORT_CASES = {
    # 코드: (케이스 본문, 문제가 있는 본문 줄 번호)
    "heading_too_long": ("### " + "가" * 21 + "\n\n문단.\n", 1),
    "missing_callout": ("## 둘째 장\n\n본문만 있습니다.\n", 1),
    "heading_level": ("#### 소절\n\n문단.\n", 1),
    "heading_level_h5": ("### 절\n\n문단.\n\n##### 너무 깊음\n\n문단.\n", 5),
    "duplicate_heading": ("### 같은 제목\n\n문단.\n\n### 같은 제목\n\n문단.\n", 5),
    "q_without_a": ("**Q.** 질문인가요?\n\n답 없이 문단.\n", 1),
    "list_depth3": ("- 하나\n    - 둘\n        - 셋\n", 3),
    "circled_multi_chapter": (
        "① 첫째 장 포인트.\n\n## 둘째 장\n\n> 핵심 문장.\n\n② 둘째 장 포인트.\n",
        7,
    ),
    "paragraph_linebreak": ("첫 줄입니다.\n이어진 둘째 줄입니다.\n", 2),
    "multi_emphasis": ("**하나** 그리고 **둘**.\n", 1),
    "stray_quote": ("> 장 중간의 인용.\n", 1),
    "manual_numbering": ("1) 손 번호.\n", 1),
    "manual_numbering_paren": ("(1) 손 번호.\n", 1),
    "manual_numbering_korean": ("가. 손 번호.\n", 1),
    "manual_numbering_step": ("STEP 1 손 번호.\n", 1),
    "bracket_label": ("[문제] 라벨.\n", 1),
    "horizontal_rule": ("---\n", 1),
}

# 케이스 이름 → 보고 코드 (같은 코드를 여러 모양으로 확인한다)
REPORT_CODE = {
    "heading_level_h5": "heading_level",
    "manual_numbering_paren": "manual_numbering",
    "manual_numbering_korean": "manual_numbering",
    "manual_numbering_step": "manual_numbering",
}


def test_valid_doc_has_no_issues():
    assert check(HEAD) == []


@pytest.mark.parametrize("name", REPORT_CASES)
def test_check_reports_with_line(name):
    body, k = REPORT_CASES[name]
    code = REPORT_CODE.get(name, name)

    found = {(i.line, i.code) for i in check(doc(body))}

    assert (body_line(k), code) in found


OK_CASES = {
    "heading_20_chars": "### " + "가" * 20 + "\n\n문단.\n",
    "word_starting_with_digit": "### 1인 개발이 가능했던 이유\n\n문단.\n",
    "q_and_a": "**Q.** 질문인가요?\n\n**A.** 답입니다.\n",
    "circled_one_chapter": "① 첫째.\n\n② 둘째.\n",
    "list_depth2": "- 하나\n    - 둘\n",
    "table": "| 원문 | 뜻 |\n|---|---|\n| a | 가 |\n",
    "evidence": "근거: 40 CFR 70.6(c)(5)\n",
    "code_block": "```text\n[의회] 법\n---\n① 줄\n  들여쓰기\n```\n",
}


@pytest.mark.parametrize("name", OK_CASES)
def test_check_allows_valid_blocks(name):
    assert check(doc(OK_CASES[name])) == []


def test_title_limit_is_30():
    ok = HEAD.replace("# 문서 제목", "# " + "가" * 30)
    bad = HEAD.replace("# 문서 제목", "# " + "가" * 31)

    assert check(ok) == []
    assert (1, "heading_too_long") in {(i.line, i.code) for i in check(bad)}


def test_main_reports_without_touching_file(tmp_path):
    path = tmp_path / "a.md"
    original = doc("[문제] 라벨.\n").encode("utf-8")
    path.write_bytes(original)

    assert main([str(path)]) != 0
    assert path.read_bytes() == original


# ---------- 완료 기준 3: 지금 문서는 오류 0개 ----------

@pytest.mark.parametrize("name", ["0_Project_summary.md", "1_Project_full.md"])
def test_project_docs_pass(name):
    text = (PROJECT / name).read_text(encoding="utf-8")

    assert check(text) == []
    assert fix(text) == text
