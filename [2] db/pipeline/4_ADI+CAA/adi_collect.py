"""Collect one complete ADI result page into the raw store."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from adi_fetch import fetch_results
from adi_results import parse_results
from ecfr_raw import save_raw


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run(root: Path, as_of: date, run: dict[str, Any]) -> None:
    path = root / "raw" / as_of.isoformat() / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(
    root: Path,
    *,
    fetch_results: Callable[..., dict[str, Any]] = fetch_results,
    today: date | None = None,
) -> dict[str, Any]:
    """Fetch, save, and validate the complete ADI results page."""

    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    response = fetch_results()
    parsed = parse_results(response["body"])
    rows = parsed["rows"]
    row_count = len(rows)
    unique_control_numbers = len({row["control_number"] for row in rows})

    entry = save_raw(
        root,
        as_of,
        "adi-results.html",
        response["body"],
        source_url=response["source_url"],
        final_url=response["final_url"],
        http_status=response["http_status"],
        media_type=response["media_type"],
    )

    if parsed["results_length"] != row_count:
        status = "held"
        reason = "results_length_mismatch"
    elif row_count != unique_control_numbers:
        status = "held"
        reason = "duplicate_control_number"
    else:
        status = "succeeded"
        reason = None

    run: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "dataset": "adi",
        "as_of": as_of.isoformat(),
        "status": status,
        "reason": reason,
        "results_length": parsed["results_length"],
        "row_count": row_count,
        "unique_control_numbers": unique_control_numbers,
        "html_sha256": entry["sha256"],
        "started_at": started_at,
        "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "4) ADI+CAA"
    result = collect(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "succeeded" else 2)


__all__ = ["collect"]
