"""SUU-106: PROGRAMS·PROGRAM_SUBPARTS·POLLUTANTS 한 행 → echo_program / echo_program_subpart / echo_pollutant 행.

행은 실제 CSV (2026-09-17) 첫 행 그대로. code_map 은 SUU-104 `echo_code_map.jsonl` 행을 `raw_subpart_code` 로 묶은 dict.
"""
from datetime import date

from echo_programs import pollutant_row, program_row, subpart_row

PROGRAM = {
    "PGM_SYS_ID": "DE0000001000100090",
    "PROGRAM_CODE": "CAASIP",
    "PROGRAM_DESC": "State Implementation Plan for National Primary and Secondary Ambient Air Quality Standards",
    "AIR_OPERATING_STATUS_CODE": "CLS",
    "AIR_OPERATING_STATUS_DESC": "Permanently Closed",
    "BEGIN_DATE": "02/22/2017",
    "UPDATED_DATE": "02/21/2020",
}

SUBPART = {
    "PGM_SYS_ID": "AR0000000513900037",
    "PROGRAM_CODE": "CAANESH",
    "PROGRAM_DESC": "National Emission Standards for Hazardous Air Pollutants (40 CFR Part 61)",
    "AIR_PROGRAM_SUBPART_CODE": "CAANESHFF",
    "AIR_PROGRAM_SUBPART_DESC": "NESHAP Part 61 - Subpart FF - BENZENE WASTE OPERATIONS",
}

POLLUTANT = {
    "PGM_SYS_ID": "NH0000003300900014",
    "POLLUTANT_CODE": "300000322",
    "POLLUTANT_DESC": "TOTAL PARTICULATE MATTER",
    "SRS_ID": "1647643",
    "CHEMICAL_ABSTRACT_SERVICE_NMBR": "",
    "AIR_POLLUTANT_CLASS_CODE": "MIN",
    "AIR_POLLUTANT_CLASS_DESC": "Minor Emissions",
}


def code_map_entry(code, part, subpart, status="ok"):
    return {
        "program_code": code[:7], "raw_subpart_code": code, "raw_description": "x",
        "cfr_title": "40", "cfr_part": part, "cfr_subpart": subpart, "review_status": status,
        "dictionary_version": "2026-09-17", "source_url": "u",
    }


CODE_MAP = {
    "CAANESHFF": code_map_entry("CAANESHFF", "61", "FF"),
    "CAAMACTFF": code_map_entry("CAAMACTFF", "63", "FF"),  # 같은 글자 FF, 다른 Part
    "CAAMACT": code_map_entry("CAAMACT", "63", "BBBBBB", status="conflict"),  # 사전의 깨진 행
}


def test_program_row_parses_dates_and_keeps_raw():
    assert program_row(PROGRAM) == {
        "pgm_sys_id": "DE0000001000100090",
        "program_code": "CAASIP",
        "description": "State Implementation Plan for National Primary and Secondary Ambient Air Quality Standards",
        "status_code": "CLS",
        "status_desc": "Permanently Closed",
        "begin_date": date(2017, 2, 22),
        "updated_date": date(2020, 2, 21),
        "raw_dates": {"BEGIN_DATE": "02/22/2017", "UPDATED_DATE": "02/21/2020"},
    }

    blank = program_row({**PROGRAM, "AIR_OPERATING_STATUS_CODE": "", "AIR_OPERATING_STATUS_DESC": "", "BEGIN_DATE": ""})
    assert (blank["status_code"], blank["status_desc"], blank["begin_date"]) == (None, None, None)
    assert blank["raw_dates"]["BEGIN_DATE"] == ""  # 원문은 그대로 남는다


def test_subpart_row_takes_part_from_code_map_not_from_letters():
    assert subpart_row(SUBPART, CODE_MAP) == {
        "pgm_sys_id": "AR0000000513900037",
        "program_code": "CAANESH",
        "subpart_code": "CAANESHFF",
        "subpart_desc": "NESHAP Part 61 - Subpart FF - BENZENE WASTE OPERATIONS",
        "cfr_title": 40,
        "cfr_part": "61",
        "cfr_subpart": "FF",
        "mapping_status": "mapped",
    }

    mact = subpart_row({**SUBPART, "PROGRAM_CODE": "CAAMACT", "AIR_PROGRAM_SUBPART_CODE": "CAAMACTFF"}, CODE_MAP)
    assert (mact["cfr_part"], mact["cfr_subpart"]) == ("63", "FF")  # 글자는 같아도 Part 가 다르다

    unknown = subpart_row({**SUBPART, "PROGRAM_CODE": "CAAGACT", "AIR_PROGRAM_SUBPART_CODE": "CAAGACTZZZZZZ"}, CODE_MAP)
    assert (unknown["cfr_title"], unknown["cfr_part"], unknown["cfr_subpart"]) == (None, None, None)
    assert unknown["mapping_status"] == "unresolved"  # 사전에 없음 — 코드 글자로 추측하지 않는다

    conflict = subpart_row({**SUBPART, "PROGRAM_CODE": "CAAMACT", "AIR_PROGRAM_SUBPART_CODE": "CAAMACT"}, CODE_MAP)
    assert (conflict["cfr_title"], conflict["cfr_part"], conflict["cfr_subpart"]) == (None, None, None)
    assert conflict["mapping_status"] == "conflict"  # 사전이 둘 이상을 말하면 하나로 단정하지 않는다


def test_pollutant_row_uses_code_as_key_or_row_based_temporary_key():
    assert pollutant_row(POLLUTANT, 1) == {
        "pgm_sys_id": "NH0000003300900014",
        "pollutant_key": "300000322",
        "pollutant_code": "300000322",
        "description": "TOTAL PARTICULATE MATTER",
        "srs_id": "1647643",
        "cas_number": None,  # "" → None
        "class_code": "MIN",
        "class_desc": "Minor Emissions",
        "source_locator": "ICIS-AIR_POLLUTANTS.csv:1",
        "review_status": "ok",
    }

    nocode = pollutant_row({**POLLUTANT, "POLLUTANT_CODE": ""}, 977624)
    assert nocode["pollutant_key"] == "row:977624"  # 코드가 없으면 행번호 기준 임시 키
    assert nocode["pollutant_code"] is None
    assert nocode["review_status"] == "unresolved"
    assert nocode["source_locator"] == "ICIS-AIR_POLLUTANTS.csv:977624"
