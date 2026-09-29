"""SUU-304: full md를 항목별 md로 자른다 (full이 유일한 원본)."""

from pathlib import Path

import pytest

from md_check import check
from md_split import ITEMS, main, split, write_items

PROJECT = Path(__file__).parents[3] / "1) project"
FULL = PROJECT / "1_full" / "1_Project_full.md"

SAMPLE = """# 전체 문서

표지 첫 문단.

표지 둘째 문단.

## 가 장

> 가 핵심.

가 본문.

### 가 절

가 절 본문.

## 나 장

> 나 핵심.

```text
## 코드 안의 제목은 장이 아니다
```

## 다 장

> 다 핵심.

다 본문.
"""

SAMPLE_ITEMS = [
    ("2_첫 항목", ["다 장", "가 장"]),
    ("3_둘째 항목", ["나 장"]),
]


# ---------- 완료 기준 1: 장을 항목별로 묶는다 ----------
# 항목 문서 제목은 "Compliance AI · " + 폴더 이름에서 번호를 뺀 것.
# (그냥 "TDD 개발 자동화"로 하면 같은 이름의 장과 제목이 겹쳐 md_check 오류가 난다)

def test_split_groups_chapters_in_item_order():
    items = split(SAMPLE, SAMPLE_ITEMS)

    assert list(items) == ["2_첫 항목", "3_둘째 항목"]
    assert items["2_첫 항목"] == (
        "# Compliance AI · 첫 항목\n\n"
        "표지 첫 문단.\n\n표지 둘째 문단.\n\n"
        "## 다 장\n\n> 다 핵심.\n\n다 본문.\n\n"
        "## 가 장\n\n> 가 핵심.\n\n가 본문.\n\n### 가 절\n\n가 절 본문.\n"
    )


def test_cover_only_in_first_item():
    items = split(SAMPLE, SAMPLE_ITEMS)

    assert "표지" not in items["3_둘째 항목"]
    assert items["3_둘째 항목"].startswith("# Compliance AI · 둘째 항목\n\n## 나 장\n")


def test_heading_inside_code_fence_is_not_a_chapter():
    items = split(SAMPLE, SAMPLE_ITEMS)

    assert items["3_둘째 항목"] == (
        "# Compliance AI · 둘째 항목\n\n"
        "## 나 장\n\n> 나 핵심.\n\n```text\n## 코드 안의 제목은 장이 아니다\n```\n"
    )


def test_crlf_input_gives_same_result():
    assert split(SAMPLE.replace("\n", "\r\n"), SAMPLE_ITEMS) == split(SAMPLE, SAMPLE_ITEMS)


# ---------- 완료 기준 2: 빠진 장·없는 장은 오류 ----------

def test_chapter_in_no_item_raises():
    with pytest.raises(ValueError, match="나 장"):
        split(SAMPLE, [("2_첫 항목", ["가 장", "다 장"])])


def test_item_chapter_missing_in_full_raises():
    with pytest.raises(ValueError, match="없는 장"):
        split(SAMPLE, SAMPLE_ITEMS + [("4_셋째 항목", ["없는 장"])])


def test_chapter_in_two_items_raises():
    with pytest.raises(ValueError, match="가 장"):
        split(SAMPLE, SAMPLE_ITEMS + [("4_셋째 항목", ["가 장"])])


# ---------- 완료 기준 3: 폴더에 쓴다 ----------

def test_write_items_makes_folder_per_item(tmp_path):
    full = tmp_path / "1_full" / "1_Project_full.md"
    full.parent.mkdir()
    full.write_text(SAMPLE, encoding="utf-8")

    paths = write_items(full, SAMPLE_ITEMS)

    assert paths == [
        tmp_path / "2_첫 항목" / "2_첫 항목.md",
        tmp_path / "3_둘째 항목" / "3_둘째 항목.md",
    ]
    assert paths[1].read_text(encoding="utf-8") == split(SAMPLE, SAMPLE_ITEMS)["3_둘째 항목"]


def test_write_items_writes_lf(tmp_path):
    full = tmp_path / "1_full" / "1_Project_full.md"
    full.parent.mkdir()
    full.write_text(SAMPLE, encoding="utf-8")

    for path in write_items(full, SAMPLE_ITEMS):
        assert b"\r\n" not in path.read_bytes()


# ---------- 완료 기준 4: 실제 프로젝트 문서 ----------

def test_project_layout():
    assert (PROJECT / "0_summary" / "0_Project_summary.md").is_file()
    assert FULL.is_file()
    assert not (PROJECT / "0_Project_summary.md").exists()
    assert not (PROJECT / "1_Project_full.md").exists()


def test_project_items():
    assert ITEMS == [
        ("2_프로젝트 개요", ["어필 포인트 5가지", "프로젝트 흐름", "사용 기술 스택"]),
        ("3_문제 정의 및 해결", ["문제 정의", "서비스 피드백 요청 콜드메일", "내가 직접 정한 것"]),
        ("4_데이터 파이프라인 구축", ["활용한 데이터셋", "데이터 신뢰성"]),
        ("5_RAG 품질 개선", ["RAG 검색 품질 개선 과정", "RAG 답변 품질 개선 과정"]),
        ("6_TDD 개발 자동화", ["TDD 개발 자동화"]),
    ]


def test_project_items_pass_md_check():
    for name, text in split(FULL.read_text(encoding="utf-8")).items():
        assert check(text) == [], name


def test_saved_items_match_full():
    """full을 고친 뒤 /report(md_split)를 돌리지 않으면 여기서 빨강이 된다."""
    for name, text in split(FULL.read_text(encoding="utf-8")).items():
        saved = PROJECT / name / f"{name}.md"
        assert saved.read_text(encoding="utf-8") == text, f"{name}: /report로 다시 만드세요"


def test_main_prints_written_paths(tmp_path, capsys):
    full = tmp_path / "1_full" / "1_Project_full.md"
    full.parent.mkdir()
    full.write_text(SAMPLE, encoding="utf-8")

    assert main([str(full)], SAMPLE_ITEMS) == 0
    out = capsys.readouterr().out
    assert "2_첫 항목.md" in out and "3_둘째 항목.md" in out


def test_main_returns_1_on_bad_mapping(tmp_path, capsys):
    full = tmp_path / "1_full" / "1_Project_full.md"
    full.parent.mkdir()
    full.write_text(SAMPLE, encoding="utf-8")

    assert main([str(full)], [("2_첫 항목", ["가 장"])]) == 1
    assert "나 장" in capsys.readouterr().out
    assert not (tmp_path / "2_첫 항목").exists()
