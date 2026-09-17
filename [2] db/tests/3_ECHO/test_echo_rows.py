"""SUU-102: ZIP 안 CSV를 압축 풀지 않고 한 행씩 (행번호, dict) 로 읽는다.

가짜 ZIP은 테스트 안에서 ``zipfile`` 로 만든다. 값 변환 없음 — 문자열 그대로.
"""
import zipfile

import pytest

from echo_rows import iter_rows
from echo_zip import inspect_zip

FACILITIES = (
    "PGM_SYS_ID,FACILITY_NAME,CITY\r\n"
    "0100000009003E0010,HIGHLAND PARK MARKET,SUFFIELD\r\n"
    '0100000009003E0011,"ACME, INC.\r\nSECOND LINE",HARTFORD\r\n'  # 셀 안 쉼표·줄바꿈
    "0100000009003E0012,EMPTY CITY,\r\n"
)


def make_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def test_row_numbers_start_at_one_and_count_matches_inspect_zip(tmp_path):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_FACILITIES.csv": FACILITIES})

    rows = list(iter_rows(path, "ICIS-AIR_FACILITIES.csv"))

    (spec,) = inspect_zip(path, required=("ICIS-AIR_FACILITIES.csv",))
    assert len(rows) == spec.row_count == 3
    assert [no for no, _ in rows] == [1, 2, 3]  # 헤더 다음 첫 데이터 행이 1
    assert rows[0][1] == {"PGM_SYS_ID": "0100000009003E0010", "FACILITY_NAME": "HIGHLAND PARK MARKET", "CITY": "SUFFIELD"}
    assert rows[2][1]["CITY"] == ""  # 빈 문자열은 빈 문자열 그대로


def test_keeps_newline_inside_cell_and_strips_bom(tmp_path):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_FACILITIES.csv": "﻿" + FACILITIES})

    rows = list(iter_rows(path, "ICIS-AIR_FACILITIES.csv"))

    assert list(rows[0][1]) == ["PGM_SYS_ID", "FACILITY_NAME", "CITY"]  # BOM 없는 열 이름
    assert rows[1][1]["FACILITY_NAME"] == "ACME, INC.\r\nSECOND LINE"  # 줄바꿈이 값 안에 그대로
    assert rows[1][1]["CITY"] == "HARTFORD"


def test_bad_utf8_raises_and_whole_member_is_never_read(tmp_path, monkeypatch):
    bad = b"PGM_SYS_ID,FACILITY_NAME\r\nX1,CAF\xc9\r\n"  # \xc9 = latin-1 'É', UTF-8 로는 깨진 바이트
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_FACILITIES.csv": bad})

    def _read(self, *args, **kwargs):
        raise AssertionError("ZipFile.read()는 멤버 전체를 메모리에 올린다. open()으로 흘려 읽어야 한다")

    monkeypatch.setattr(zipfile.ZipFile, "read", _read)

    with pytest.raises(UnicodeDecodeError):
        list(iter_rows(path, "ICIS-AIR_FACILITIES.csv"))
