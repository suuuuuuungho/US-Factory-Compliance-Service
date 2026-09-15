"""SUU-48: ADI 검색 결과 HTML의 표를 회신 목록(한 행 = dict 하나)으로 바꾸고 서버 총건수를 같이 돌려준다.

fixture는 2026-09-15 Category=MACT 검색 결과(762행)에서 폼과 표만 잘라낸 것. 처음 30행 + 특수 행 9개 = 39행.
세션 값(CFID/CFTOKEN)은 fixture에서 지웠다. 서버 총건수 hidden 값 762는 그대로 둔다.
"""
import json
from pathlib import Path

import pytest

from adi_results import parse_results

FIXTURE = Path(__file__).parent / "fixtures" / "adi_results_sample.html"
FIELDS = [
    "source_system", "control_number", "title", "letter_date_raw",
    "categories", "office", "author", "source_url",
]
FILE_URL = "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id="


def rows():
    return parse_results(FIXTURE.read_bytes())["rows"]


def by_control(number):
    found = [r for r in rows() if r["control_number"] == number]
    assert len(found) == 1, number
    return found[0]


def test_every_row_becomes_one_dict_with_eight_fields():
    result = rows()
    assert len(result) == 39

    for row in result:
        assert list(row) == FIELDS, row.get("control_number")
        assert row["source_system"] == "adi"
        assert row["control_number"].strip() and row["title"].strip()
        assert row["letter_date_raw"].strip() and row["office"].strip()
        assert isinstance(row["categories"], list) and row["categories"]

    numbers = [r["control_number"] for r in result]
    assert len(numbers) == len(set(numbers))

    # 표 순서 그대로. Control Number 는 문자열 (숫자만인 것도, M/Z 붙은 것도)
    assert numbers[:3] == ["1800013", "1800038", "1800008"]
    assert numbers[30:32] == ["Z200004", "M200005"]

    first = result[0]
    assert first["title"] == "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks"
    assert first["letter_date_raw"] == "05/11/2018"
    assert first["office"] == "Region 5"
    assert first["author"] == "Sara Breneman"

    # 구형 항목의 가짜 날짜는 글자 그대로. 날짜로 바꾸지 않는다
    assert by_control("M960042")["letter_date_raw"] == "12/30/1899"
    # 작성자 빈 칸은 None
    assert by_control("M070018")["author"] is None
    assert sum(r["author"] is None for r in result) == 4


def test_source_url_has_no_session_token():
    # fixture 는 세션 값이 없는 상태. 실제 페이지처럼 CFID/CFTOKEN 을 끼워 넣어도 결과는 같아야 한다
    plain = FIXTURE.read_bytes()
    with_session = plain.replace(
        b"dsp_show_file_contents&id=",
        b"dsp_show_file_contents&CFID=33954140&CFTOKEN=3401b853ef12a7b1-6619394B-0E98-8E9A-69789F8FC837D7C1&id=",
    )
    assert with_session != plain

    for html in (plain, with_session):
        result = parse_results(html)["rows"]
        for row in result:
            assert row["source_url"] == FILE_URL + row["control_number"], row["control_number"]
        dumped = json.dumps(result)
        assert "CFID" not in dumped and "CFTOKEN" not in dumped


def test_categories_split_and_results_length_returned():
    result = parse_results(FIXTURE.read_bytes())

    assert by_control("M160020")["categories"] == ["GACT", "MACT", "NESHAP", "NSPS"]
    assert by_control("1800028")["categories"] == ["Federal Plan", "MACT", "NSPS"]
    assert by_control("M070018")["categories"] == ["MACT"]
    assert by_control("1800013")["categories"] == ["MACT", "NSPS"]

    # 서버가 말하는 총건수. 행 수(39)와 다르지만 그대로 돌려준다 — 비교는 수집 실행 티켓의 일
    assert list(result) == ["results_length", "rows"]
    assert result["results_length"] == 762
    assert isinstance(result["results_length"], int)


def test_missing_column_raises():
    html = FIXTURE.read_bytes()

    with pytest.raises(ValueError):
        parse_results(html.replace(b"<b>Control Number</b>", b"<b>Number</b>"))

    with pytest.raises(ValueError):
        parse_results(html.replace(b'name="results_length"', b'name="results_len"'))

    with pytest.raises(ValueError):
        parse_results(b"<html><body><p>no table here</p></body></html>")
