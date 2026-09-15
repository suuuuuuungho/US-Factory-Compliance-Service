"""SUU-47: CAA Dashboard 페이지 HTML의 표를 회신 목록(한 행 = dict 하나)으로 바꾼다.

fixture는 2026-09-15 실제 페이지에서 표만 잘라낸 것. Safe Links 안의 직원 이메일만 staff@epa.gov 로 바꿨다.
"""
import json
import re
from pathlib import Path

import pytest

from adi_dashboard import parse_dashboard

FIXTURE = Path(__file__).parent / "fixtures" / "adi_dashboard_sample.html"
FIELDS = [
    "source_system", "facility_name", "title", "affected_subpart_raw",
    "link_text", "source_url", "canonical_url", "affected_subparts",
]
KING_PDF = "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"
HYLIION_PDF = "https://www.epa.gov/system/files/documents/2025-09/hyliion-response_9-11-25.pdf"


def rows():
    return parse_dashboard(FIXTURE.read_bytes())


def by_facility(name):
    found = [r for r in rows() if r["facility_name"] == name]
    assert len(found) == 1, name
    return found[0]


def test_every_row_becomes_one_dict_with_eight_fields():
    result = rows()
    assert len(result) == 236

    for row in result:
        assert list(row) == FIELDS, row.get("facility_name")
        assert row["source_system"] == "caa_dashboard"
        assert row["facility_name"].strip() and row["title"].strip() and row["affected_subpart_raw"].strip()
        assert isinstance(row["affected_subparts"], list)

    # 표 순서 그대로: 첫 행은 Hyliion
    assert result[0]["facility_name"] == "Hyliion Inc."
    assert result[0]["title"] == "Regulatory Interpretation for Stationary Internal Combustion Engines"
    # 링크 칸 글자는 날짜가 아니라 파일명일 수도 있다. 칸 안 글자를 공백 하나로 이어 붙인 것
    assert result[0]["link_text"] == "Hyliion Response_9-11-25 (pdf) (176.91 KB)"

    king = by_facility("King Systems Corporation")
    assert king["title"] == "Applicability Determination for Surface Coating Of Miscellaneous Plastic Parts and Products"
    assert king["affected_subpart_raw"] == "Part 63, PPPP: Surface Coating of Miscellaneous Plastic Parts and Products"
    assert king["link_text"] == "2020-06-16"

    assert sum(any(p["part"] == "63" for p in r["affected_subparts"]) for r in result) == 132
    assert sum(len(r["affected_subparts"]) > 1 for r in result) == 42


def test_safe_links_resolve_to_epa_url_without_tracking_data():
    result = rows()

    # Safe Links: url 값을 풀어 canonical_url. source_url 은 추적 매개변수를 뗀 Safe Links 주소
    king = by_facility("King Systems Corporation")
    assert king["canonical_url"] == KING_PDF
    assert king["source_url"] == "https://gcc02.safelinks.protection.outlook.com/?url=" + (
        "https%3A%2F%2Fwww.epa.gov%2Fsystem%2Ffiles%2Fdocuments%2F2022-05%2FKing%2520Systems%2520Corp%2520Response_6-16-20.pdf"
    )

    # 이미 epa.gov 주소면 둘 다 그대로
    hyliion = by_facility("Hyliion Inc.")
    assert hyliion["source_url"] == HYLIION_PDF
    assert hyliion["canonical_url"] == HYLIION_PDF

    # 깨진 SharePoint 상대 주소: 행은 남기고 canonical_url 만 None
    westrock = by_facility("Westrock, Florence Mill")
    assert westrock["source_url"] == "/%3Ab%3A/s/R4/APTMD/EWyW-tIAqSRAunGrhcGLi7wBsFxO_ChCv0ZqhIRnI5Tbpg?e=SIhi4U"
    assert westrock["canonical_url"] is None

    resolved = [r["canonical_url"] for r in result if r["canonical_url"] is not None]
    assert len(resolved) == 235
    assert all(url.startswith("https://www.epa.gov/") for url in resolved)

    # 직원 이메일이 든 data, 서명 sdata, reserved 는 결과 어디에도 없다
    dumped = json.dumps(result)
    assert "%40epa.gov" not in dumped and "@epa.gov" not in dumped
    assert "sdata=" not in dumped and "data=" not in dumped and "reserved=" not in dumped


def test_affected_subpart_splits_into_part_subpart_pairs():
    result = rows()

    hyliion = by_facility("Hyliion Inc.")
    assert hyliion["affected_subparts"] == [
        {"part": "60", "subpart": "IIII"},
        {"part": "60", "subpart": "JJJJ"},
    ]
    assert by_facility("King Systems Corporation")["affected_subparts"] == [{"part": "63", "subpart": "PPPP"}]

    pairs = [p for r in result for p in r["affected_subparts"]]
    assert len(pairs) == 281
    for pair in pairs:
        assert list(pair) == ["part", "subpart"]
        assert pair["part"] in {"60", "61", "62", "63"}
        assert re.fullmatch(r"[A-Za-z]{1,7}", pair["subpart"]), pair
    # Part 60 에는 Db, Ja 처럼 소문자가 섞인 코드가 있다. 대문자로 바꾸지 않는다
    assert {"part": "60", "subpart": "Db"} in pairs


def test_missing_column_raises():
    html = FIXTURE.read_bytes()

    with pytest.raises(ValueError):
        parse_dashboard(html.replace(b"<th>Affected Subpart</th>", b"<th>Subpart</th>"))

    with pytest.raises(ValueError):
        parse_dashboard(b"<html><body><p>no table here</p></body></html>")
