"""Convert ECHO formal and informal actions into activity records."""

from echo_values import is_missing, parse_amount, parse_date


_DATE_COLUMNS = {
    "formal": "SETTLEMENT_ENTERED_DATE",
    "informal": "ACHIEVED_DATE",
}
_MAPPED_COLUMNS = {
    "PGM_SYS_ID",
    "ACTIVITY_ID",
    "STATE_EPA_FLAG",
    "ACTIVITY_TYPE_CODE",
    "ACTIVITY_TYPE_DESC",
    "SETTLEMENT_ENTERED_DATE",
    "ACHIEVED_DATE",
    "PENALTY_AMOUNT",
}


def _nullable(value: str) -> str | None:
    """Return ``None`` for ECHO missing-value markers."""
    return None if is_missing(value) else value


def action_rows(
    kind: str, row: dict[str, str], source_row_no: int
) -> tuple[dict, dict, dict | None]:
    """Convert one action CSV row into activity, link, and penalty records."""
    if kind not in _DATE_COLUMNS:
        raise ValueError(f"Unknown ECHO action kind: {kind}")

    date_column = _DATE_COLUMNS[kind]
    raw_date = row[date_column]
    activity = {
        "activity_kind": kind,
        "activity_id": row["ACTIVITY_ID"],
        "type_code": _nullable(row.get("ACTIVITY_TYPE_CODE", "")),
        "type_desc": _nullable(row.get("ACTIVITY_TYPE_DESC", "")),
        "lead_flag": _nullable(row["STATE_EPA_FLAG"]),
        "monitor_code": None,
        "monitor_desc": None,
        "activity_date": parse_date(raw_date),
        "raw_date": raw_date,
        "attributes": {
            key: _nullable(value)
            for key, value in row.items()
            if key not in _MAPPED_COLUMNS
        },
    }
    link = {
        "activity_kind": kind,
        "activity_id": row["ACTIVITY_ID"],
        "pgm_sys_id": row["PGM_SYS_ID"],
    }
    if kind == "informal":
        return activity, link, None

    raw_amount = row["PENALTY_AMOUNT"]
    penalty = {
        "penalty_key": f"formal:{source_row_no}",
        "activity_kind": kind,
        "activity_id": row["ACTIVITY_ID"],
        "amount": parse_amount(raw_amount),
        "amount_kind": "penalty",
        "currency": "USD",
        "amount_scope": "row",
        "raw_amount": raw_amount,
        "source_locator": f"ICIS-AIR_FORMAL_ACTIONS.csv:{source_row_no}",
    }
    return activity, link, penalty
