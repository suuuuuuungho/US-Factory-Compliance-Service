"""SUU-206: Part 63 목록 API를 next_page_url 이 없어질 때까지 따라가며 행을 모은다.

네트워크 없음. fetch 를 가짜로 넣어 fixtures/list_page{1,2,3}.json 을 돌려준다.
"""
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fr_list import collect_list, list_url

FIXTURES = Path(__file__).parent / "fixtures"
END = date(2026, 9, 21)


def _pages():
    return [json.loads((FIXTURES / f"list_page{i}.json").read_text(encoding="utf-8")) for i in (1, 2, 3)]


def fake_fetch(calls: list):
    """첫 요청은 page1, 그 뒤는 직전 페이지의 next_page_url 과 똑같아야 다음 페이지를 준다."""
    pages = _pages()
    expected = [list_url(END)] + [p["next_page_url"] for p in pages[:-1]]

    def _fetch(url: str) -> bytes:
        calls.append(url)
        index = expected.index(url)  # 지어낸 URL이면 ValueError
        return json.dumps(pages[index]).encode("utf-8")

    return _fetch


def test_list_url_has_part63_range_and_oldest_order():
    query = parse_qs(urlparse(list_url(END)).query)
    assert query["conditions[cfr][title]"] == ["40"]
    assert query["conditions[cfr][part]"] == ["63"]
    assert query["conditions[publication_date][gte]"] == ["1994-01-01"]
    assert query["conditions[publication_date][lte]"] == ["2026-09-21"]
    assert query["order"] == ["oldest"]
    assert query["per_page"] == ["1000"]


def test_follows_next_page_url_until_end_and_row_total_matches_count(tmp_path):
    calls: list[str] = []

    result = collect_list(tmp_path / "fr", END, fetch=fake_fetch(calls))

    assert len(calls) == 3
    assert calls[0] == list_url(END)
    pages = _pages()
    assert calls[1] == pages[0]["next_page_url"]
    assert calls[2] == pages[1]["next_page_url"]
    assert result["count"] == 5
    assert result["pages"] == 3
    assert len(result["rows"]) == 5


def test_keeps_same_document_number_with_different_dates(tmp_path):
    result = collect_list(tmp_path / "fr", END, fetch=fake_fetch([]))

    keys = [(r["publication_date"], r["document_number"]) for r in result["rows"]]
    assert ("2003-05-27", "03-5521") in keys
    assert ("2003-08-28", "03-5521") in keys
    assert len(keys) == len(set(keys))


def test_writes_rows_as_jsonl_under_lists_folder(tmp_path):
    root = tmp_path / "fr"
    collect_list(root, END, fetch=fake_fetch([]))

    path = root / "raw" / "lists" / "2026-09-21" / "documents.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [r["document_number"] for r in rows] == ["94-752", "03-5521", "03-5521", "2026-03638", "2026-09999"]
    assert rows[0]["title"].startswith("Public Meeting")


def test_row_count_mismatch_with_api_count_is_an_error(tmp_path):
    pages = _pages()
    pages[2]["results"] = []  # 마지막 페이지가 비어 4행만 옴

    def _fetch(url):
        return json.dumps(pages.pop(0)).encode("utf-8")

    try:
        collect_list(tmp_path / "fr", END, fetch=_fetch)
    except ValueError as exc:
        assert "5" in str(exc) and "4" in str(exc)
    else:
        raise AssertionError("count 5 vs 4 rows should raise ValueError")
