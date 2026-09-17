"""SUU-95: ECHO ZIP 무결성과 필수 CSV 검사, 멤버별 명세.

가짜 ZIP은 테스트 안에서 ``zipfile``로 만든다. 네트워크·저장 없음.
"""
import zipfile

import pytest

from echo_zip import ICIS_AIR_MEMBERS, PIPELINE_MEMBERS, ZipCheckError, inspect_zip

FACILITIES = (
    "PGM_SYS_ID,FACILITY_NAME,CITY\r\n"
    "0100000009003E0010,HIGHLAND PARK MARKET,SUFFIELD\r\n"
    '0100000009003E0011,"ACME, INC.\r\nSECOND LINE",HARTFORD\r\n'  # 셀 안 쉼표·줄바꿈
    "0100000009003E0012,EMPTY CITY,\r\n"
)
PROGRAMS = "PGM_SYS_ID,PROGRAM_CODE\r\nDE0000001000100090,CAASIP\r\n"


def make_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return path


def test_required_member_constants_match_survey():
    assert len(ICIS_AIR_MEMBERS) == 10
    assert "ICIS-AIR_FACILITIES.csv" in ICIS_AIR_MEMBERS
    assert "ICIS-AIR_VIOLATION_HISTORY.csv" in ICIS_AIR_MEMBERS
    assert PIPELINE_MEMBERS == ("PIPELINE_CAA_00_COMPLETE.csv",)


def test_returns_spec_per_member_with_header_and_exact_row_count(tmp_path):
    path = make_zip(
        tmp_path / "a.zip",
        {"ICIS-AIR_FACILITIES.csv": FACILITIES, "ICIS-AIR_PROGRAMS.csv": PROGRAMS, "README.txt": "hello"},
    )

    specs = inspect_zip(path, required=("ICIS-AIR_FACILITIES.csv", "ICIS-AIR_PROGRAMS.csv"))

    by_name = {s.name: s for s in specs}
    assert set(by_name) == {"ICIS-AIR_FACILITIES.csv", "ICIS-AIR_PROGRAMS.csv", "README.txt"}  # 추가 멤버도 보존

    fac = by_name["ICIS-AIR_FACILITIES.csv"]
    assert fac.byte_size == len(FACILITIES.encode("utf-8"))
    assert fac.header == ["PGM_SYS_ID", "FACILITY_NAME", "CITY"]
    assert fac.row_count == 3  # 헤더 제외. 셀 안 줄바꿈은 행으로 세지 않는다

    prog = by_name["ICIS-AIR_PROGRAMS.csv"]
    assert prog.header == ["PGM_SYS_ID", "PROGRAM_CODE"]
    assert prog.row_count == 1

    readme = by_name["README.txt"]
    assert readme.header is None  # CSV가 아니면 헤더·행 수를 세지 않는다
    assert readme.row_count is None
    assert readme.byte_size == 5


def test_strips_utf8_bom_from_header(tmp_path):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_PROGRAMS.csv": "﻿" + PROGRAMS})

    (spec,) = inspect_zip(path, required=("ICIS-AIR_PROGRAMS.csv",))

    assert spec.header == ["PGM_SYS_ID", "PROGRAM_CODE"]


def test_missing_required_member_names_what_is_missing(tmp_path):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_PROGRAMS.csv": PROGRAMS})

    with pytest.raises(ZipCheckError, match="ICIS-AIR_FACILITIES.csv"):
        inspect_zip(path, required=("ICIS-AIR_FACILITIES.csv", "ICIS-AIR_PROGRAMS.csv"))


def test_path_escaping_work_folder_is_rejected(tmp_path):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_PROGRAMS.csv": PROGRAMS, "../evil.csv": "x\r\n"})

    with pytest.raises(ZipCheckError, match=r"\.\./evil\.csv"):
        inspect_zip(path, required=("ICIS-AIR_PROGRAMS.csv",))


def test_crc_mismatch_is_rejected(tmp_path):
    path = tmp_path / "a.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("ICIS-AIR_PROGRAMS.csv", PROGRAMS)
    data = bytearray(path.read_bytes())
    offset = data.find(b"CAASIP")  # 저장 모드라 원문이 그대로 있다. 한 글자 망가뜨림
    data[offset] = ord("X")
    path.write_bytes(bytes(data))

    with pytest.raises(ZipCheckError, match="CRC"):
        inspect_zip(path, required=("ICIS-AIR_PROGRAMS.csv",))


def test_not_a_zip_is_rejected(tmp_path):
    path = tmp_path / "a.zip"
    path.write_bytes(b"<!DOCTYPE html><html></html>")

    with pytest.raises(ZipCheckError, match="ZIP"):
        inspect_zip(path, required=("ICIS-AIR_PROGRAMS.csv",))


def test_does_not_read_whole_member_into_memory(tmp_path, monkeypatch):
    path = make_zip(tmp_path / "a.zip", {"ICIS-AIR_PROGRAMS.csv": PROGRAMS})

    def _read(self, *args, **kwargs):
        raise AssertionError("ZipFile.read()는 멤버 전체를 메모리에 올린다. open()으로 흘려 읽어야 한다")

    monkeypatch.setattr(zipfile.ZipFile, "read", _read)

    (spec,) = inspect_zip(path, required=("ICIS-AIR_PROGRAMS.csv",))

    assert spec.row_count == 1
