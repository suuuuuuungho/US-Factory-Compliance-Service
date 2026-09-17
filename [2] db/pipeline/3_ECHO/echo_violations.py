"""Convert ECHO violation CSV rows into violation and facility-link records."""

from echo_values import is_missing, parse_date, split_codes


_DATE_COLUMNS = (
    "EARLIEST_FRV_DETERM_DATE",
    "HPV_DAYZERO_DATE",
    "HPV_RESOLVED_DATE",
    "DSCV_PATHWAY_DATE",
    "NFTC_PATHWAY_DATE",
)


def _nullable(value: str) -> str | None:
    """Return ``None`` for ECHO missing-value markers."""
    return None if is_missing(value) else value


def violation_rows(row: dict[str, str]) -> tuple[dict, dict]:
    """Convert one violation CSV row into violation and facility-link records."""
    raw_dates = {key: row[key] for key in _DATE_COLUMNS}
    violation = {
        "violation_id": row["ACTIVITY_ID"],
        "determination_uid": _nullable(row["COMP_DETERMINATION_UID"]),
        "policy_code": _nullable(row["ENF_RESPONSE_POLICY_CODE"]),
        "agency": _nullable(row["AGENCY_TYPE_DESC"]),
        "state": _nullable(row["STATE_CODE"]),
        "first_frv_date": parse_date(raw_dates["EARLIEST_FRV_DETERM_DATE"]),
        "hpv_dayzero_date": parse_date(raw_dates["HPV_DAYZERO_DATE"]),
        "resolved_date": parse_date(raw_dates["HPV_RESOLVED_DATE"]),
        "programs": split_codes(row["PROGRAM_CODES"]),
        "pollutants": split_codes(row["POLLUTANT_CODES"]),
        "raw_dates": raw_dates,
        "attributes": {
            "AIR_LCON_CODE": _nullable(row["AIR_LCON_CODE"]),
            "PROGRAM_DESCS": _nullable(row["PROGRAM_DESCS"]),
            "POLLUTANT_DESCS": _nullable(row["POLLUTANT_DESCS"]),
        },
    }
    link = {
        "violation_id": row["ACTIVITY_ID"],
        "pgm_sys_id": row["PGM_SYS_ID"],
    }
    return violation, link
