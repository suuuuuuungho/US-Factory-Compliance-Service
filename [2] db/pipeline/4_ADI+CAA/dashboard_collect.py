"""Collect the CAA Dashboard page into the raw store."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from adi_dashboard import parse_dashboard
from dashboard_fetch import fetch_dashboard
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
    fetch_dashboard: Callable[..., dict[str, Any]] = fetch_dashboard,
    today: date | None = None,
) -> dict[str, Any]:
    """Fetch, validate, and save the CAA Dashboard page."""

    root = Path(root)
    as_of = today or date.today()
    started_at = _now()

    response = fetch_dashboard()
    rows = parse_dashboard(response["body"])
    row_count = len(rows)
    part_63_count = sum(
        1
        for row in rows
        if any(subpart["part"] == "63" for subpart in row["affected_subparts"])
    )

    entry = save_raw(
        root,
        as_of,
        "caa-dashboard.html",
        response["body"],
        source_url=response["source_url"],
        final_url=response["final_url"],
        http_status=response["http_status"],
        media_type=response["media_type"],
    )

    run: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "dataset": "caa_dashboard",
        "as_of": as_of.isoformat(),
        "status": "succeeded",
        "row_count": row_count,
        "part_63_count": part_63_count,
        "html_sha256": entry["sha256"],
        "started_at": started_at,
        "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run


if __name__ == "__main__":
    root = (
        Path(__file__).resolve().parents[2]
        / "4) ADI+CAA"
        / "caa_dashboard"
    )
    result = collect(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "succeeded" else 2)


__all__ = ["collect"]
