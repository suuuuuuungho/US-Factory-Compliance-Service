"""SUU-222: 회신 본문(adi_page 행) → adi_block 행.

줄 앞머리 표식(Q:/A:/Letter:/Conditions/Sincerely)으로 블록을 나눈다. 표식이 하나도 없으면 kind=body 1개.
블록은 원문(status ok 페이지를 "\\n\\n"으로 이은 글자)을 빈틈없이 나눈다: 블록 글자를 순서대로 이으면 원문과 같다.
fixture 의 `<<<PAGE>>>` 줄은 페이지 경계다.
"""
from __future__ import annotations

from pathlib import Path

from adi_blocks import split_blocks

FIXTURES = Path(__file__).parent / "fixtures"
VERSION_ID = "11111111-1111-5111-8111-111111111111"


def _pages(name: str) -> list[dict]:
    text = (FIXTURES / name).read_text(encoding="utf-8").rstrip("\n")
    return [
        {"version_id": VERSION_ID, "page_no": no, "text_content": chunk.strip("\n"), "status": "ok"}
        for no, chunk in enumerate(text.split("<<<PAGE>>>"), start=1)
    ]


def _original(pages: list[dict]) -> str:
    return "\n\n".join(page["text_content"] for page in pages if page["status"] == "ok")


def test_qa_letter_splits_into_kinds_in_order_and_rejoins_to_original():
    pages = _pages("adi_letter_qa.txt")

    blocks = split_blocks(VERSION_ID, pages)

    assert [block["kind"] for block in blocks] == ["header", "question", "answer", "body", "condition", "signature"]
    assert [block["block_no"] for block in blocks] == [1, 2, 3, 4, 5, 6]
    assert "".join(block["text_content"] for block in blocks) == _original(pages)
    assert blocks[1]["text_content"].startswith("Q: Will EPA authorize")
    assert blocks[2]["text_content"].startswith("A: Yes.")
    assert blocks[5]["text_content"].startswith("Sincerely,")
    assert all(block["version_id"] == VERSION_ID and block["review_status"] == "검토 전" for block in blocks)
    assert all(block["source_locator"] for block in blocks)


def test_negative_answer_keeps_no_and_kinds_order():
    pages = _pages("adi_letter_negative.txt")

    blocks = split_blocks(VERSION_ID, pages)

    assert [block["kind"] for block in blocks] == ["header", "question", "answer", "body", "signature"]
    answer = blocks[2]["text_content"]
    assert answer.startswith("A: No.")
    assert "should be denied" in answer
    assert "".join(block["text_content"] for block in blocks) == _original(pages)


def test_plain_letter_is_one_body_block():
    pages = _pages("adi_letter_body.txt")

    blocks = split_blocks(VERSION_ID, pages)

    assert len(blocks) == 1
    assert blocks[0]["kind"] == "body"
    assert blocks[0]["block_no"] == 1
    assert blocks[0]["page_no"] == 1
    assert blocks[0]["text_content"] == _original(pages)


def test_block_page_no_is_the_page_where_the_block_starts_and_empty_pages_are_skipped():
    pages = _pages("adi_letter_qa.txt")
    pages.insert(1, {"version_id": VERSION_ID, "page_no": 2, "text_content": "", "status": "empty"})
    pages[2]["page_no"] = 3

    blocks = split_blocks(VERSION_ID, pages)

    by_kind = {block["kind"]: block for block in blocks}
    assert by_kind["header"]["page_no"] == 1
    assert by_kind["question"]["page_no"] == 1
    assert by_kind["condition"]["page_no"] == 3
    assert by_kind["signature"]["page_no"] == 3
    assert "".join(block["text_content"] for block in blocks) == _original(pages)


def test_version_without_text_has_no_blocks():
    assert split_blocks(VERSION_ID, []) == []
    assert split_blocks(VERSION_ID, [{"version_id": VERSION_ID, "page_no": 1, "text_content": "", "status": "failed"}]) == []
