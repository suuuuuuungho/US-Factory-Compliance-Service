"""Convert ECHO activity CSV rows into activity and facility-link records."""

from echo_values import is_missing, parse_date


_KINDS = {"inspection", "stack_test", "titlev"}
_MAPPED_COLUMNS = {
    "PGM_SYS_ID", "ACTIVITY_ID", "STATE_EPA_FLAG", "ACTIVITY_TYPE_CODE",
    "ACTIVITY_TYPE_DESC", "COMP_MONITOR_TYPE_CODE", "COMP_MONITOR_TYPE_DESC",
    "ACTUAL_END_DATE",
}


def _nullable(value: str) -> str | None:
    """Return ``None`` for ECHO missing-value markers."""
    return None if is_missing(value) else value


def activity_rows(kind: str, row: dict[str, str]) -> tuple[dict, dict]:
    """Convert one activity CSV row into activity and facility-link records."""
    if kind not in _KINDS:
        raise ValueError(f"Unknown ECHO activity kind: {kind}")

    raw_date = row["ACTUAL_END_DATE"]
    activity = {
        "activity_kind": kind,
        "activity_id": row["ACTIVITY_ID"],
        "type_code": _nullable(row.get("ACTIVITY_TYPE_CODE", "")),
        "type_desc": _nullable(row.get("ACTIVITY_TYPE_DESC", "")),
        "lead_flag": _nullable(row["STATE_EPA_FLAG"]),
        "monitor_code": _nullable(row["COMP_MONITOR_TYPE_CODE"]),
        "monitor_desc": _nullable(row["COMP_MONITOR_TYPE_DESC"]),
        "activity_date": parse_date(raw_date),
        "raw_date": raw_date,
        "attributes": {key: _nullable(value) for key, value in row.items()
                       if key not in _MAPPED_COLUMNS},
    }
    link = {"activity_kind": kind, "activity_id": row["ACTIVITY_ID"],
            "pgm_sys_id": row["PGM_SYS_ID"]}
    return activity, link
