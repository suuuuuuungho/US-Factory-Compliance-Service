"""SUU-107: FCES_PCES·STACK_TESTS·TITLEV_CERTS 한 행 → echo_activity 1행 + echo_activity_facility 1행.

행은 실제 CSV (2026-09-17) 첫 행 그대로. 세 파일은 열이 다르다 (점검 10열, 시험 10열, 인증 7열).
"""
from datetime import date

import pytest

from echo_activities import activity_rows

INSPECTION = {
    "PGM_SYS_ID": "PR0000007212300011",
    "ACTIVITY_ID": "121929",
    "STATE_EPA_FLAG": "E",
    "ACTIVITY_TYPE_CODE": "INS",
    "ACTIVITY_TYPE_DESC": "Inspection/Evaluation",
    "COMP_MONITOR_TYPE_CODE": "PCE",
    "COMP_MONITOR_TYPE_DESC": "PCE On-Site",
    "ACTUAL_END_DATE": "05-04-2004",
    "PROGRAM_CODES": "",
    "ACTIVITY_PURPOSE_DESC": "Agency Priority",
}

STACK_TEST = {
    "PGM_SYS_ID": "NH0000003301700003",
    "ACTIVITY_ID": "123027",
    "COMP_MONITOR_TYPE_CODE": "CST",
    "COMP_MONITOR_TYPE_DESC": "Stack Test",
    "STATE_EPA_FLAG": "E",
    "ACTUAL_END_DATE": "06/24/2004",
    "POLLUTANT_CODES": "HAPS [HAZARDOUS AIR POLLUTANTS/AIR TOXICS]",
    "POLLUTANT_DESCS": "",
    "AIR_STACK_TEST_STATUS_CODE": "",
    "AIR_STACK_TEST_STATUS_DESC": "",
}

TITLEV = {
    "PGM_SYS_ID": "UT0000004903500210",
    "ACTIVITY_ID": "3600154556",
    "COMP_MONITOR_TYPE_CODE": "TVA",
    "COMP_MONITOR_TYPE_DESC": "TV ACC Receipt/Review",
    "STATE_EPA_FLAG": "S",
    "ACTUAL_END_DATE": "04/30/2015",
    "FACILITY_RPT_DEVIATION_FLAG": "Y",
}


def test_inspection_and_stack_test_dates_land_in_same_field_with_raw_kept():
    activity, _ = activity_rows("inspection", INSPECTION)
    assert activity == {
        "activity_kind": "inspection",
        "activity_id": "121929",
        "type_code": "INS",
        "type_desc": "Inspection/Evaluation",
        "lead_flag": "E",
        "monitor_code": "PCE",
        "monitor_desc": "PCE On-Site",
        "activity_date": date(2004, 5, 4),  # MM-DD-YYYY
        "raw_date": "05-04-2004",
        "attributes": {"PROGRAM_CODES": None, "ACTIVITY_PURPOSE_DESC": "Agency Priority"},
    }

    test, _ = activity_rows("stack_test", STACK_TEST)
    assert (test["activity_date"], test["raw_date"]) == (date(2004, 6, 24), "06/24/2004")  # MM/DD/YYYY 도 같은 필드
    assert (test["type_code"], test["type_desc"]) == (None, None)  # 시험 파일엔 ACTIVITY_TYPE_* 열이 없다

    nodate, _ = activity_rows("titlev", {**TITLEV, "ACTUAL_END_DATE": ""})
    assert (nodate["activity_date"], nodate["raw_date"]) == (None, "")  # 원문은 "" 그대로


def test_unmapped_columns_are_kept_in_attributes_and_blank_status_is_none():
    test, _ = activity_rows("stack_test", STACK_TEST)
    assert test["attributes"] == {
        "POLLUTANT_CODES": "HAPS [HAZARDOUS AIR POLLUTANTS/AIR TOXICS]",  # 쪼개지 않는다 (숫자 코드가 아니다)
        "POLLUTANT_DESCS": None,
        "AIR_STACK_TEST_STATUS_CODE": None,  # "" → None. 통과(PSS)로 바꾸지 않는다
        "AIR_STACK_TEST_STATUS_DESC": None,
    }

    passed, _ = activity_rows("stack_test", {**STACK_TEST, "AIR_STACK_TEST_STATUS_CODE": "NA"})
    assert passed["attributes"]["AIR_STACK_TEST_STATUS_CODE"] == "NA"  # 실제 코드 "NA"(46,522행)는 값이다

    cert, _ = activity_rows("titlev", TITLEV)
    assert cert["attributes"] == {"FACILITY_RPT_DEVIATION_FLAG": "Y"}
    assert (cert["monitor_code"], cert["lead_flag"]) == ("TVA", "S")


def test_activity_facility_shares_kind_id_and_pgm_sys_id():
    for kind, row in (("inspection", INSPECTION), ("stack_test", STACK_TEST), ("titlev", TITLEV)):
        activity, link = activity_rows(kind, row)
        assert link == {"activity_kind": kind, "activity_id": row["ACTIVITY_ID"], "pgm_sys_id": row["PGM_SYS_ID"]}
        assert (link["activity_kind"], link["activity_id"]) == (activity["activity_kind"], activity["activity_id"])
        assert "pgm_sys_id" not in activity  # 시설 연결은 activity_facility 에만

    with pytest.raises(ValueError):
        activity_rows("formal", INSPECTION)  # 처분은 SUU-108


def test_fake_date_becomes_none_but_raw_date_is_kept():
    # SUU-270: 실제 DB 에 있던 가짜 날짜. 날짜 칸은 비우고 원문은 raw_date 에 남는다
    activity, _ = activity_rows("inspection", {**INSPECTION, "ACTUAL_END_DATE": "01/01/8888"})
    assert activity["activity_date"] is None
    assert activity["raw_date"] == "01/01/8888"
