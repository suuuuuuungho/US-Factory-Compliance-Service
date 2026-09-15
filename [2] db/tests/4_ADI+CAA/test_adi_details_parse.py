"""SUU-57: ADI 상세 응답 HTML(결과 폼을 재제출한 응답)에서 행마다
control_number/title/letter_date_raw/author/categories/office/abstract 를 뽑는다.

fixture는 실제 cfpub.epa.gov/adi 에서 M200005(+1800013) 로 확인한 진짜 응답이다
(세션 값 CFID/CFTOKEN은 만료된 값이라 그대로 두었다 — 파싱은 세션 값을 쓰지 않는다).
"""
from __future__ import annotations

from pathlib import Path

from adi_details_parse import parse_details

SINGLE = Path(__file__).parent / "fixtures" / "adi_details_response_single.html"
BATCH = Path(__file__).parent / "fixtures" / "adi_details_response_batch.html"


def test_parses_single_real_detail_response():
    rows = parse_details(SINGLE.read_bytes())

    assert len(rows) == 1
    row = rows[0]
    assert list(row) == [
        "control_number", "title", "letter_date_raw",
        "author", "categories", "office", "abstract",
    ]
    assert row["control_number"] == "M200005"
    assert row["title"] == "Applicability Determination for a Lithium Ion Battery Manufacturing Facility"
    assert row["letter_date_raw"] == "04/08/2020"
    assert row["author"] == "Sara Breneman"
    assert row["categories"] == ["MACT", "NESHAP"]
    assert row["office"] == "Region 5"
    assert row["abstract"].startswith("Q: Does EPA determine that the lithium ion battery")
    assert "40 CFR 63.11607" in row["abstract"]


def test_parses_multiple_rows_from_batch_response_in_order():
    rows = parse_details(BATCH.read_bytes())

    assert len(rows) == 2
    assert [row["control_number"] for row in rows] == ["M200005", "1800013"]

    second = rows[1]
    assert second["title"] == "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks"
    assert second["letter_date_raw"] == "05/11/2018"
    assert second["categories"] == ["MACT", "NSPS"]
    assert second["office"] == "Region 5"
    assert second["abstract"].startswith("Q: Does EPA approve an Alternative Monitoring Plan")


def test_zero_determinations_response_returns_empty_list():
    html = (
        b'<table class="nostyle" width="800" align="center">'
        b'<tr><td align="center">The search returned zero determinations.</td></tr>'
        b'</table>'
    )
    assert parse_details(html) == []
