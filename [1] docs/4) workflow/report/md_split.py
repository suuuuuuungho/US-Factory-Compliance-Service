"""Split the project full report into its item reports."""

from __future__ import annotations

import sys
from pathlib import Path


ITEMS: list[tuple[str, list[str]]] = [
    ("2_프로젝트 개요", ["어필 포인트 5가지", "프로젝트 흐름", "사용 기술 스택"]),
    ("3_문제 정의 및 해결", ["문제 정의", "서비스 피드백 요청 콜드메일", "내가 직접 정한 것"]),
    ("4_데이터 파이프라인 구축", ["활용한 데이터셋", "데이터 신뢰성"]),
    ("5_RAG 품질 개선", ["RAG 검색 품질 개선 과정", "RAG 답변 품질 개선 과정"]),
    ("6_TDD 개발 자동화", ["TDD 개발 자동화"]),
]


def _chapters(text: str) -> tuple[str, dict[str, str]]:
    """Return the cover and chapters, ignoring headings inside fenced code."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    body = lines[1:]
    starts: list[tuple[int, str]] = []
    fenced = False
    for index, line in enumerate(body):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            starts.append((index, line[3:].strip()))

    cover_end = starts[0][0] if starts else len(body)
    cover = "\n".join(body[:cover_end]).strip()
    chapters: dict[str, str] = {}
    for index, (start, title) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(body)
        chapters[title] = "\n".join(body[start:end]).strip()
    return cover, chapters


def split(text: str, items=ITEMS) -> dict[str, str]:
    """Return each item report, in the supplied item order."""
    cover, chapters = _chapters(text)
    requested = [title for _, titles in items for title in titles]
    duplicate = {title for title in requested if requested.count(title) > 1}
    missing = set(requested) - set(chapters)
    unassigned = set(chapters) - set(requested)
    problems = duplicate | missing | unassigned
    if problems:
        raise ValueError("장 매핑 오류: " + ", ".join(sorted(problems)))

    result: dict[str, str] = {}
    for index, (folder, titles) in enumerate(items):
        title = folder.split("_", 1)[1]
        parts = [f"# Compliance AI · {title}"]
        if index == 0 and cover:
            parts.append(cover)
        parts.extend(chapters[chapter] for chapter in titles)
        result[folder] = "\n\n".join(parts).strip() + "\n"
    return result


def write_items(full_path, items=ITEMS) -> list[Path]:
    """Write item reports next to the full-report folder."""
    full_path = Path(full_path)
    reports = split(full_path.read_text(encoding="utf-8"), items)
    paths: list[Path] = []
    for folder, text in reports.items():
        path = full_path.parent.parent / folder / f"{folder}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        paths.append(path)
    return paths


def main(argv: list[str], items=ITEMS) -> int:
    full_path = Path(argv[0]) if argv else Path("[1] docs/1) project/1_full/1_Project_full.md")
    try:
        paths = write_items(full_path, items)
    except ValueError as error:
        print(error)
        return 1
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
