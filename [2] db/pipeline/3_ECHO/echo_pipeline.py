"""Convert PIPELINE_CAA_00_COMPLETE CSV rows into pipeline-link records."""

import hashlib


_ID_COLUMNS = (
    "EVAL_ACTIVITY_ID",
    "VIOL_ACTIVITY_ID",
    "EA_ACTIVITY_ID",
    "EA_FEA_ACTIVITY_ID",
)
_FLAG_COLUMNS = (
    "PIPELINE_FLAG",
    "OFFICIAL_FLAG",
    "EVAL_FLAG",
    "VIOL_FLAG",
    "FOUND_VIOLATION",
    "EA_FLAG",
    "FEA_ISSUE_DATE_FLAG",
)


def _nullable(value: str) -> str | None:
    """Return ``None`` only for an empty CSV field."""
    return None if value == "" else value


def _actual_id(value: str) -> bool:
    """Return whether an activity ID can refer to a real activity."""
    return value not in ("", "-9999")


def _resolve(
    kinds: tuple[str, ...], activity_id: str, known_activities: set[tuple[str, str]]
) -> tuple[str | None, str | None]:
    """Return the first matching activity kind and ID."""
    for kind in kinds:
        if (kind, activity_id) in known_activities:
            return kind, activity_id
    return None, None


def pipeline_row(
    row: dict[str, str], source_row_no: int, known_activities: set[tuple[str, str]]
) -> dict:
    """Convert one pipeline CSV row into an evidence link record."""
    eval_id = row["EVAL_ACTIVITY_ID"]
    violation_id = row["VIOL_ACTIVITY_ID"]
    ea_id = row["EA_ACTIVITY_ID"]
    eval_kind, resolved_eval_id = (
        _resolve(("inspection", "stack_test", "titlev"), eval_id, known_activities)
        if _actual_id(eval_id)
        else (None, None)
    )
    resolved_violation_id = (
        violation_id if _actual_id(violation_id) and ("violation", violation_id) in known_activities else None
    )
    ea_kind, resolved_ea_id = (
        _resolve(("formal", "informal"), ea_id, known_activities)
        if _actual_id(ea_id)
        else (None, None)
    )
    actual = (_actual_id(eval_id), _actual_id(violation_id), _actual_id(ea_id))
    resolved = (resolved_eval_id is not None, resolved_violation_id is not None, resolved_ea_id is not None)
    status = "none" if not any(actual) else "resolved" if all(
        not needs_resolution or found for needs_resolution, found in zip(actual, resolved)
    ) else "unresolved"
    used_columns = {"SOURCE_ID", *_ID_COLUMNS, *_FLAG_COLUMNS}
    return {
        "link_key": hashlib.sha256("\x1f".join(row.values()).encode("utf-8")).hexdigest(),
        "pgm_sys_id": row["SOURCE_ID"],
        "eval_activity_id": _nullable(eval_id),
        "violation_activity_id": _nullable(violation_id),
        "ea_activity_id": _nullable(ea_id),
        "ea_fea_activity_id": _nullable(row["EA_FEA_ACTIVITY_ID"]),
        "flags": {column: _nullable(row[column]) for column in _FLAG_COLUMNS},
        "synthetic_violation": eval_id == "-9999",
        "resolution_status": status,
        "resolved_eval_kind": eval_kind,
        "resolved_eval_id": resolved_eval_id,
        "resolved_violation_id": resolved_violation_id,
        "resolved_ea_kind": ea_kind,
        "resolved_ea_id": resolved_ea_id,
        "source_row_no": source_row_no,
        "attributes": {column: _nullable(value) for column, value in row.items() if column not in used_columns},
    }
