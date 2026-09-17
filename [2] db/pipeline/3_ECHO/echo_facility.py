"""Convert ECHO facility CSV rows into facility and industry records."""

from echo_values import is_missing, split_codes


ALIASES = {
    "local_control_region_code": (
        "LOCAL_CONTROL_REGION_CODE", "AIR_LOCAL_CONTROL_REGION_CODE",
    ),
    "local_control_region_name": (
        "LOCAL_CONTROL_REGION_NAME", "AIR_LOCAL_CONTROL_REGION_NAME",
    ),
}


def _nullable(value: str) -> str | None:
    """Return ``None`` for ECHO's missing-value markers."""

    return None if is_missing(value) else value


def _aliased(row: dict[str, str], field: str) -> str | None:
    """Return the first available CSV spelling for an aliased field."""

    for column in ALIASES[field]:
        if column in row:
            return _nullable(row[column])
    return None


def facility_rows(row: dict[str, str]) -> tuple[dict, list[dict]]:
    """Convert one FACILITIES row into a facility and its industry records."""

    pgm_sys_id = row["PGM_SYS_ID"]
    facility = {
        "pgm_sys_id": pgm_sys_id,
        "registry_id": _nullable(row["REGISTRY_ID"]),
        "name": row["FACILITY_NAME"], "address": row["STREET_ADDRESS"],
        "city": row["CITY"], "county": row["COUNTY_NAME"],
        "state": row["STATE"], "zip": row["ZIP_CODE"],
        "epa_region": row["EPA_REGION"],
        "facility_type": _nullable(row["FACILITY_TYPE_CODE"]),
        "source_class": _nullable(row["AIR_POLLUTANT_CLASS_CODE"]),
        "source_class_desc": _nullable(row["AIR_POLLUTANT_CLASS_DESC"]),
        "operating_status": _nullable(row["AIR_OPERATING_STATUS_CODE"]),
        "operating_status_desc": _nullable(row["AIR_OPERATING_STATUS_DESC"]),
        "current_hpv": _nullable(row["CURRENT_HPV"]),
        "local_control_region_code": _aliased(row, "local_control_region_code"),
        "local_control_region_name": _aliased(row, "local_control_region_name"),
    }
    industries = []
    for column, code_system in (("SIC_CODES", "SIC"), ("NAICS_CODES", "NAICS")):
        industries.extend({"pgm_sys_id": pgm_sys_id, "code_system": code_system,
                           "code": code, "source_locator": column}
                          for code in split_codes(row[column]))
    return facility, industries
