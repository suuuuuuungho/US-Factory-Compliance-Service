"""문서 md 규칙 검사기 (`[1] docs/4) workflow/3_doc_rules.md` 6절).

쉬운 것은 fix()가 고치고, 문장을 바꿔야 하는 것은 check()가 줄 번호와 함께 알려 준다.
사용: python md_check.py <md 파일>...
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^(#+) (.*)$")
LIST_ITEM = re.compile(r"^( *)(-|\d+\.) ")
NUMBERED = re.compile(r"^( *)\d+\. (.*)$")
HEADING_NUMBER = re.compile(
    r"^(#+) (?:\d+(?:\.\d+)+\.?|\d+[.)]|[①-⑩]|Sol_\d+\.?|\d+(?:st|nd|rd|th)\.?)\s+"
)
MANUAL_NUMBER = re.compile(
    r"^\s*(?:- )?(?:\(\d+\)|\d+\)|[가나다라마바사아자차카타파하]\.|[a-z]\.|STEP \d+|Sol_\d+|\d+(?:st|nd|rd|th)\.)(?:\s|$)"
)
BRACKET_LABEL = re.compile(r"^\s*(?:- )?\[[^\]]+\](?!\()")
RULE_LINE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
QA_MARK = re.compile(r"\*\*[QA]\.\*\*")


@dataclass
class Issue:
    line: int
    code: str
    message: str


def fix(text: str) -> str:
    out: list[str] = []
    counters: dict[int, int] = {}
    in_code = False
    for line in text.split("\n"):
        if FENCE.match(line):
            in_code = not in_code
            counters = {}
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue

        line = line.replace("\t", "    ").rstrip()
        line = re.sub(r"^(\s*(?:- )?)\[근거\]\s*", r"\1근거: ", line)
        line = re.sub(r"^(\s*)[*+] ", r"\1- ", line)
        line = HEADING_NUMBER.sub(r"\1 ", line)

        item = LIST_ITEM.match(line)
        if not item:
            counters = {}
        else:
            indent = len(item.group(1))
            counters = {k: v for k, v in counters.items() if k <= indent}
            numbered = NUMBERED.match(line)
            if numbered:
                counters[indent] = counters.get(indent, 0) + 1
                line = f"{numbered.group(1)}{counters[indent]}. {numbered.group(2)}"
            else:
                counters.pop(indent, None)

        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out)


def _is_paragraph(line: str) -> bool:
    return bool(line) and not (
        line.startswith(("#", "|", ">")) or LIST_ITEM.match(line) or FENCE.match(line)
    )


def check(text: str) -> list[Issue]:
    issues: list[Issue] = []

    def add(n: int, code: str, message: str) -> None:
        issues.append(Issue(n, code, message))

    seen: set[str] = set()
    level = 0
    chapter = 0
    circled_chapter = None
    circled_reported: set[int] = set()
    expect_callout = None  # 핵심 문장을 기다리는 ## 제목 줄 번호
    expect_answer = None  # **A.**를 기다리는 **Q.** 줄 번호
    in_code = False
    prev = ""

    for n, line in enumerate(text.split("\n"), 1):
        if in_code:
            if FENCE.match(line):
                in_code = False
                prev = ""
            continue

        if line.strip():
            if expect_callout is not None and not line.startswith("> "):
                add(expect_callout, "missing_callout", "장이 핵심 문장(>)으로 시작하지 않습니다")
            if expect_answer is not None and not line.startswith("**A.**"):
                add(expect_answer, "q_without_a", "**Q.** 다음 블록이 **A.**가 아닙니다")
            is_callout = expect_callout is not None and line.startswith("> ")
            expect_callout = None
            expect_answer = None
        else:
            prev = ""
            continue

        if FENCE.match(line):
            in_code = True
            continue

        heading = HEADING.match(line)
        if heading:
            depth, title = len(heading.group(1)), heading.group(2).strip()
            limit = 30 if depth == 1 else 20
            if len(title) > limit:
                add(n, "heading_too_long", f"제목이 {len(title)}자입니다 ({limit}자 이하)")
            if depth >= 5 or (level and depth > level + 1):
                add(n, "heading_level", "제목 단계를 건너뛰었거나 #####를 썼습니다")
            if title in seen:
                add(n, "duplicate_heading", f"같은 제목이 또 있습니다: {title}")
            seen.add(title)
            level = depth
            if depth == 2:
                chapter += 1
                expect_callout = n
            prev = line
            continue

        if line.startswith(">") and not is_callout:
            add(n, "stray_quote", "핵심 문장이 아닌 곳에 >를 썼습니다")
        if line.startswith("**Q.**"):
            expect_answer = n
        if re.match(r"^ {8,}(?:-|\d+\.) ", line):
            add(n, "list_depth3", "목록은 2단계까지만 씁니다")
        if re.match(r"^[①-⑩]", line):
            if circled_chapter is None:
                circled_chapter = chapter
            elif chapter != circled_chapter and chapter not in circled_reported:
                circled_reported.add(chapter)
                add(n, "circled_multi_chapter", "원 숫자는 한 장에서만 씁니다")
        if _is_paragraph(line) and _is_paragraph(prev):
            add(n, "paragraph_linebreak", "문단 안에서 줄을 바꿨습니다")
        if QA_MARK.sub("", line).count("**") >= 4:
            add(n, "multi_emphasis", "한 블록에 강조가 두 곳 이상입니다")
        if MANUAL_NUMBER.match(line):
            add(n, "manual_numbering", "손으로 만든 번호입니다. 1. 또는 -를 씁니다")
        if BRACKET_LABEL.match(line):
            add(n, "bracket_label", "대괄호 라벨로 시작합니다. 표나 제목으로 바꿉니다")
        if RULE_LINE.match(line):
            add(n, "horizontal_rule", "--- 구분선은 쓰지 않습니다")
        prev = line

    if expect_callout is not None:
        add(expect_callout, "missing_callout", "장이 핵심 문장(>)으로 시작하지 않습니다")
    if expect_answer is not None:
        add(expect_answer, "q_without_a", "**Q.** 다음 블록이 **A.**가 아닙니다")
    return issues


def main(paths: list[str]) -> int:
    failed = False
    for p in paths:
        path = Path(p)
        text = path.read_bytes().decode("utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n")
        fixed = fix(text)
        if fixed != text:
            path.write_bytes(fixed.replace("\n", newline).encode("utf-8"))
            print(f"{p}: 자동으로 고쳤습니다")
        for issue in check(fixed):
            failed = True
            print(f"{p}:{issue.line}: {issue.message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
