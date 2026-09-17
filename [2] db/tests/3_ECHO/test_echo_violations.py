"""SUU-109: VIOLATION_HISTORY 한 행 → echo_violation 1행 + echo_violation_facility 1행.

행은 실제 CSV (2026-09-17) 첫 행 그대로. 헤더 16열. 날짜 5열은 전부 MM-DD-YYYY.
"""
from datetime import date

from echo_violations import violation_rows

FIRST = {
    "PGM_SYS_ID": "DE0000001000100090",
    "ACTIVITY_ID": "3400309508",
    "AGENCY_TYPE_DESC": "State",
    "STATE_CODE": "DE",
    "AIR_LCON_CODE": "",
    "COMP_DETERMINATION_UID": "DE000A0000100010009000003",
    "ENF_RESPONSE_POLICY_CODE": "HPV",
    "PROGRAM_CODES": "CAASIP",
    "PROGRAM_DESCS": "State Implementation Plan for National Primary and Secondary Ambient Air Quality Standards",
    "POLLUTANT_CODES": "300000243",
    "POLLUTANT_DESCS": "VOLATILE ORGANIC COMPOUNDS (VOCS)",
    "EARLIEST_FRV_DETERM_DATE": "",
    "HPV_DAYZERO_DATE": "02-28-1997",
    "HPV_RESOLVED_DATE": "02-19-1998",
    "DSCV_PATHWAY_DATE": "",
    "NFTC_PATHWAY_DATE": "",
}


def test_first_real_row_splits_multi_values_into_lists():
    violation, link = violation_rows(FIRST)
    assert violation == {
        "violation_id": "3400309508",
        "determination_uid": "DE000A0000100010009000003",
        "policy_code": "HPV",
        "agency": "State",
        "state": "DE",
        "first_frv_date": None,  # "" → None
        "hpv_dayzero_date": date(1997, 2, 28),
        "resolved_date": date(1998, 2, 19),
        "programs": ["CAASIP"],
        "pollutants": ["300000243"],
        "raw_dates": {
            "EARLIEST_FRV_DETERM_DATE": "",
            "HPV_DAYZERO_DATE": "02-28-1997",
            "HPV_RESOLVED_DATE": "02-19-1998",
            "DSCV_PATHWAY_DATE": "",
            "NFTC_PATHWAY_DATE": "",
        },
        "attributes": {  # 열은 있지만 정규 필드가 없는 것들. 설명문은 공백으로 못 쪼갠다
            "AIR_LCON_CODE": None,
            "PROGRAM_DESCS": "State Implementation Plan for National Primary and Secondary Ambient Air Quality Standards",
            "POLLUTANT_DESCS": "VOLATILE ORGANIC COMPOUNDS (VOCS)",
        },
    }
    assert link == {"violation_id": "3400309508", "pgm_sys_id": "DE0000001000100090"}
    assert "pgm_sys_id" not in violation  # 시설 연결은 violation_facility 에만

    multi, _ = violation_rows({**FIRST, "PROGRAM_CODES": "CAANSPS CAASIP", "POLLUTANT_CODES": "7003 300000319 300000329"})
    assert multi["programs"] == ["CAANSPS", "CAASIP"]  # 실제 데이터의 공백 구분
    assert multi["pollutants"] == ["7003", "300000319", "300000329"]

    empty, _ = violation_rows({**FIRST, "PROGRAM_CODES": "", "POLLUTANT_CODES": ""})
    assert (empty["programs"], empty["pollutants"]) == ([], [])


def test_three_dates_are_parsed_separately_and_raw_kept():
    violation, _ = violation_rows({**FIRST, "EARLIEST_FRV_DETERM_DATE": "01-15-1997", "HPV_RESOLVED_DATE": ""})
    assert violation["first_frv_date"] == date(1997, 1, 15)
    assert violation["hpv_dayzero_date"] == date(1997, 2, 28)
    assert violation["resolved_date"] is None  # 해결 안 됨
    assert violation["raw_dates"]["EARLIEST_FRV_DETERM_DATE"] == "01-15-1997"
    assert violation["raw_dates"]["HPV_RESOLVED_DATE"] == ""  # 원문은 그대로

    frv, _ = violation_rows({**FIRST, "ENF_RESPONSE_POLICY_CODE": "FRV", "HPV_DAYZERO_DATE": ""})
    assert (frv["policy_code"], frv["hpv_dayzero_date"]) == ("FRV", None)  # FRV 는 기산일이 없는 게 정상


def test_pathway_dates_stay_raw_and_never_become_resolved_date():
    violation, _ = violation_rows({
        **FIRST, "HPV_RESOLVED_DATE": "", "DSCV_PATHWAY_DATE": "03-01-1998", "NFTC_PATHWAY_DATE": "04-01-1998",
    })
    assert violation["resolved_date"] is None  # 경로 날짜로 해결일을 채우지 않는다
    assert violation["raw_dates"]["DSCV_PATHWAY_DATE"] == "03-01-1998"
    assert violation["raw_dates"]["NFTC_PATHWAY_DATE"] == "04-01-1998"
    assert "dscv_pathway_date" not in violation and "nftc_pathway_date" not in violation
