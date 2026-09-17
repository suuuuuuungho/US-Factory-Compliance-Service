"""SUU-104: EPA 공식 Subpart 사전 페이지(HTML 표) → echo_code_map jsonl.

표본 HTML은 실제 페이지(2026-09-17)에서 그대로 따온 모양이다.
- 표가 4개(GHG/MACT/NESHAP/NSPS) 있고 머리글은 전부 Program Code / Program Subpart / Code Description
- 설명은 ``MACT Part 63 - Subpart JJJJJJ - 이름`` 꼴
- 실제 페이지에 깨진 행 7개가 있다: Subpart 칸이 ``CAAMACT`` 뿐이고 설명이 ``6B MACT Part 63 - ...`` 로 시작
"""
import json

from echo_codemap import parse_code_table, write_code_map

URL = "https://echo.epa.gov/tools/data-downloads/icis-air-download-summary/air-program-code-subpart-descriptions"


def table(rows):
    body = "".join(f"<tr>\n<td>{a}</td>\n<td>{b}</td>\n<td>{c}</td>\n</tr>" for a, b, c in rows)
    return (
        "<table><thead><tr><th scope=\"col\">Program Code</th><th scope=\"col\">Program Subpart</th>"
        "<th scope=\"col\">Code Description</th></tr></thead><tbody>" + body + "</tbody></table>"
    )


GOOD = "<html><body><h2>MACT</h2>" + table([
    ("CAAMACT", "CAAMACT6J", "MACT Part 63 - Subpart JJJJJJ - INDUSTRIAL, COMMERCIAL, AND INSTITUTIONAL BOILERS AREA SOURCES"),
    ("CAAMACT", "CAAMACTZZZZ", "MACT Part 63 - Subpart ZZZZ - STATIONARY RECIPROCATING INTERNAL COMBUSTION ENGINES (RICE)"),
    ("CAAMACT", "CAAMACT6H", "MACT Part 63 - Subpart HHHHHH - PAINT STRIP &amp; MISC SURFACE COATING OPERATIONS AT AREA SOURCES"),
]) + "<h2>NSPS</h2>" + table([
    ("CAANSPS", "CAANSPSA", "NSPS Part 60 - Subpart A - General Provisions"),
]) + "</body></html>"


def test_rows_from_all_tables_with_cfr_fields_filled():
    rows = parse_code_table(GOOD, version="2026-09-17", source_url=URL)

    assert len(rows) == 4  # 표 2개 모두 읽는다
    assert rows[0] == {
        "program_code": "CAAMACT",
        "raw_subpart_code": "CAAMACT6J",
        "raw_description": "MACT Part 63 - Subpart JJJJJJ - INDUSTRIAL, COMMERCIAL, AND INSTITUTIONAL BOILERS AREA SOURCES",
        "cfr_title": "40",
        "cfr_part": "63",
        "cfr_subpart": "JJJJJJ",
        "review_status": "ok",
        "dictionary_version": "2026-09-17",
        "source_url": URL,
    }
    assert rows[1]["cfr_subpart"] == "ZZZZ"  # 코드 끝 'ZZZZ' 가 아니라 설명에서 읽는다
    assert rows[2]["raw_description"].startswith("MACT Part 63 - Subpart HHHHHH - PAINT STRIP & MISC")  # &amp; 풀림
    assert (rows[3]["program_code"], rows[3]["cfr_part"], rows[3]["cfr_subpart"]) == ("CAANSPS", "60", "A")


BROKEN = table([
    ("CAAMACT", "CAAMACT6J", "MACT Part 63 - Subpart JJJJJJ - INDUSTRIAL, COMMERCIAL, AND INSTITUTIONAL BOILERS AREA SOURCES"),
    ("CAAMACT", "CAAMACT", "6B MACT Part 63 - Subpart BBBBBB - GASOLINE DISTRIBUTION BULK TERMINALS"),  # 실제 깨진 행
    ("CAAMACT", "CAAMACT", "6C MACT Part 63 - Subpart CCCCCC - GASOLINE DISPENSING FACILITIES"),  # 같은 코드, 다른 설명
    ("CAANESH", "CAANESHX", "NESHAP Asbestos demolition (no part given)"),  # Part·Subpart 없음
])


def test_unresolved_when_no_part_subpart_and_conflict_when_same_code_differs():
    rows = parse_code_table(BROKEN, version="v", source_url=URL)
    by = {(r["raw_subpart_code"], r["raw_description"]): r for r in rows}

    assert len(rows) == 4  # 행을 버리지 않는다
    assert by[("CAAMACT6J", rows[0]["raw_description"])]["review_status"] == "ok"

    nesh = by[("CAANESHX", "NESHAP Asbestos demolition (no part given)")]
    assert (nesh["cfr_title"], nesh["cfr_part"], nesh["cfr_subpart"]) == (None, None, None)
    assert nesh["review_status"] == "unresolved"

    dup = [r for r in rows if r["raw_subpart_code"] == "CAAMACT"]
    assert len(dup) == 2
    assert {r["review_status"] for r in dup} == {"conflict"}  # 둘 다 conflict — 하나로 단정하지 않는다


def test_write_code_map_puts_jsonl_under_code_map_version(tmp_path):
    rows = parse_code_table(GOOD, version="2026-09-17", source_url=URL)

    path = write_code_map(tmp_path, "2026-09-17", rows)

    assert path == tmp_path / "code_map" / "2026-09-17" / "echo_code_map.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert [json.loads(line) for line in lines] == rows
    assert "&amp;" not in lines[2] and "&" in lines[2]
