"""SUU-105: FACILITIES 한 행 → echo_facility 1행 + echo_industry 자식 행.

행은 실제 ICIS-AIR_FACILITIES.csv (2026-09-17) 첫 행·둘째 행 그대로다. 헤더 19열.
"""
import pytest

from echo_facility import facility_rows

HEADER = [
    "PGM_SYS_ID", "REGISTRY_ID", "FACILITY_NAME", "STREET_ADDRESS", "CITY", "COUNTY_NAME", "STATE", "ZIP_CODE",
    "EPA_REGION", "SIC_CODES", "NAICS_CODES", "FACILITY_TYPE_CODE", "AIR_POLLUTANT_CLASS_CODE",
    "AIR_POLLUTANT_CLASS_DESC", "AIR_OPERATING_STATUS_CODE", "AIR_OPERATING_STATUS_DESC", "CURRENT_HPV",
    "LOCAL_CONTROL_REGION_CODE", "LOCAL_CONTROL_REGION_NAME",
]
FIRST = dict(zip(HEADER, [
    "0100000009003E0010", "110070834547", "HIGHLAND PARK MARKET", "68 BRIDGE ST ", "SUFFIELD", "Hartford", "CT",
    "06078", "01", "", "445110", "", "", "", "", "", "No Violation Identified", "", "",
]))
SECOND = dict(zip(HEADER, [
    "020000003400300188", "110001980624", "RAGEN PRECISION INDUSTRIES INC", "9 PORETE AVE", "NORTH ARLINGTON",
    "Bergen", "NJ", "07032", "02", "3541 3545", "335311", "POF", "MIN", "Minor Emissions", "OPR", "Operating",
    "No Violation Identified", "", "",
]))


def test_first_real_row_keeps_leading_zeros_and_raw_text():
    facility, industries = facility_rows(FIRST)

    assert facility == {
        "pgm_sys_id": "0100000009003E0010",
        "registry_id": "110070834547",
        "name": "HIGHLAND PARK MARKET",
        "address": "68 BRIDGE ST ",  # 원문 그대로 (뒤 공백 포함)
        "city": "SUFFIELD",
        "county": "Hartford",
        "state": "CT",
        "zip": "06078",  # 선행 0 유지 — 숫자로 바꾸지 않는다
        "epa_region": "01",
        "facility_type": None,  # "" → None (NULL 허용 열)
        "source_class": None,
        "source_class_desc": None,
        "operating_status": None,
        "operating_status_desc": None,
        "current_hpv": "No Violation Identified",  # 원문 그대로
        "local_control_region_code": None,
        "local_control_region_name": None,
    }
    assert industries == [
        {"pgm_sys_id": "0100000009003E0010", "code_system": "NAICS", "code": "445110", "source_locator": "NAICS_CODES"},
    ]


def test_multi_value_codes_become_one_industry_row_each_and_empty_means_none():
    facility, industries = facility_rows(SECOND)

    assert (facility["facility_type"], facility["source_class"], facility["operating_status"]) == ("POF", "MIN", "OPR")
    assert industries == [
        {"pgm_sys_id": "020000003400300188", "code_system": "SIC", "code": "3541", "source_locator": "SIC_CODES"},
        {"pgm_sys_id": "020000003400300188", "code_system": "SIC", "code": "3545", "source_locator": "SIC_CODES"},
        {"pgm_sys_id": "020000003400300188", "code_system": "NAICS", "code": "335311", "source_locator": "NAICS_CODES"},
    ]

    _, none = facility_rows({**SECOND, "SIC_CODES": "", "NAICS_CODES": ""})
    assert none == []  # 업종이 없어도 시설은 만들고 자식만 0행


def test_column_alias_and_missing_pgm_sys_id():
    with_alias = {k: v for k, v in SECOND.items() if not k.startswith("LOCAL_CONTROL_REGION_")}
    with_alias["AIR_LOCAL_CONTROL_REGION_CODE"] = "R1"  # 사전(ICIS-Air) 쪽 이름
    with_alias["AIR_LOCAL_CONTROL_REGION_NAME"] = "Region One"

    facility, _ = facility_rows(with_alias)
    assert (facility["local_control_region_code"], facility["local_control_region_name"]) == ("R1", "Region One")

    facility, _ = facility_rows({**SECOND, "LOCAL_CONTROL_REGION_CODE": "R2"})  # CSV 쪽 이름
    assert facility["local_control_region_code"] == "R2"

    with pytest.raises(KeyError):
        facility_rows({k: v for k, v in FIRST.items() if k != "PGM_SYS_ID"})
