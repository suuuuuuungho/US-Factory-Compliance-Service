"""SUU-221: ADI 목록 행·Dashboard 목록 행 → adi_source_entry 행.

목록 원본값(SUU-48/47 파서 출력)과 상세(SUU-57 details.json)만 합친다. 본문에서 뽑은 값은 넣지 않는다.
- ADI: source_key = control_number. 상세가 없으면 abstract None (held 아님).
- Dashboard: control_number 없음 → source_key 는 행 내용으로 만든 결정적 키. 236행 전부 유일해야 한다.
- scope_status: ADI 는 Categories 에 MACT/NESHAP/GACT 가 있으면 part63_candidate, Dashboard 는 Affected Subpart 에 'Part 63' 이 있으면 part63_candidate. 아니면 out_of_scope.
"""
from __future__ import annotations

from pathlib import Path

from adi_dashboard import parse_dashboard
from adi_entries import adi_entry_rows, dashboard_entry_rows, dashboard_source_key
from adi_results import parse_results

FIXTURES = Path(__file__).parent / "fixtures"
LIST_SHA = "b8fc8cc073831d46097655e49940cafb322c1a2764c4d1230cac211c24a7ea26"
DASH_SHA = "8561a6fd6ae4a752d71c1e6b3ebfa52983013c7987c41b3f49045b4974f3e8d9"

ADI_ROWS = parse_results((FIXTURES / "adi_results_sample.html").read_bytes())["rows"]  # 39행
DASH_ROWS = parse_dashboard((FIXTURES / "adi_dashboard_sample.html").read_bytes())  # 236행

DETAILS = {
    "1800013": {
        "control_number": "1800013",
        "title": "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks",
        "letter_date_raw": "05/11/2018",
        "author": "Sara Breneman",
        "categories": ["MACT", "NSPS"],
        "office": "Region 5",
        "abstract": "Q: Does EPA approve an Alternative Monitoring Plan? A: Yes.",
    }
}


def test_adi_rows_become_entries_and_details_fill_abstract():
    rows = adi_entry_rows(ADI_ROWS, DETAILS, LIST_SHA)

    assert len(rows) == 39
    by_key = {r["source_key"]: r for r in rows}
    assert set(by_key) == {r["control_number"] for r in ADI_ROWS}

    row = by_key["1800013"]
    assert row["source_system"] == "adi"
    assert row["control_number"] == "1800013"
    assert row["facility_name"] is None
    assert row["title"] == "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks"
    assert row["letter_date_raw"] == "05/11/2018"
    assert row["categories"] == ["MACT", "NSPS"]
    assert row["office"] == "Region 5"
    assert row["author"] == "Sara Breneman"
    assert row["recipient"] is None
    assert row["abstract"] == "Q: Does EPA approve an Alternative Monitoring Plan? A: Yes."
    assert row["source_url"] == "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=1800013"
    assert row["canonical_url"] == row["source_url"]  # ADI 원문 링크는 세션 없이 고정
    assert row["list_sha256"] == LIST_SHA
    assert row["link_text"] is None
    assert row["affected_subpart_raw"] is None

    # 상세가 없는 행(SUU-114 에서 12건)은 abstract 만 비고 행은 남는다
    other = by_key["1800038"]
    assert other["abstract"] is None
    assert other["title"] == "Applicability Determination for Three Internal Combustion Engines at a Compressor Station"


def test_adi_scope_status_comes_from_categories():
    rows = adi_entry_rows(
        [
            dict(ADI_ROWS[0], control_number="A1", categories=["MACT", "NSPS"]),
            dict(ADI_ROWS[0], control_number="A2", categories=["NESHAP"]),
            dict(ADI_ROWS[0], control_number="A3", categories=["GACT"]),
            dict(ADI_ROWS[0], control_number="A4", categories=["NSPS", "Asbestos"]),
            dict(ADI_ROWS[0], control_number="A5", categories=[]),
        ],
        {},
        LIST_SHA,
    )

    assert [r["scope_status"] for r in rows] == [
        "part63_candidate", "part63_candidate", "part63_candidate", "out_of_scope", "out_of_scope",
    ]


def test_dashboard_rows_get_unique_stable_source_keys():
    rows = dashboard_entry_rows(DASH_ROWS, DASH_SHA)

    assert len(rows) == 236
    keys = [r["source_key"] for r in rows]
    assert len(set(keys)) == 236  # 같은 PDF 를 가리키는 행이 있어도(230 고유 URL) 항목 키는 유일
    assert keys == [dashboard_source_key(r) for r in DASH_ROWS]  # 같은 입력 → 같은 키
    assert all(r["source_system"] == "caa_dashboard" for r in rows)
    assert all(r["control_number"] is None for r in rows)
    assert all(r["categories"] == [] for r in rows)
    assert all(r["list_sha256"] == DASH_SHA for r in rows)


def test_dashboard_row_keeps_original_fields_and_scope():
    rows = dashboard_entry_rows(DASH_ROWS, DASH_SHA)
    king = next(r for r in rows if r["facility_name"] == "King Systems Corporation")

    assert king["title"] == "Applicability Determination for Surface Coating Of Miscellaneous Plastic Parts and Products"
    assert king["affected_subpart_raw"] == "Part 63, PPPP: Surface Coating of Miscellaneous Plastic Parts and Products"
    assert king["link_text"] == "2020-06-16"
    assert king["letter_date_raw"] is None  # link_text 는 날짜 열이 아니다(계획서 1-1)
    assert king["canonical_url"] == "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"
    assert king["abstract"] is None
    assert king["scope_status"] == "part63_candidate"

    hyliion = next(r for r in rows if r["facility_name"] == "Hyliion Inc.")
    assert hyliion["scope_status"] == "out_of_scope"  # Part 60 만

    # canonical_url 이 없는 행(EPA 호스트가 아닌 링크)도 항목으로 남는다
    no_link = [r for r in rows if r["canonical_url"] is None]
    assert len(no_link) == 1
    assert no_link[0]["source_key"]
