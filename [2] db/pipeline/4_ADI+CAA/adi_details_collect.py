"""Collect ADI detail metadata in chunks."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from adi_details import fetch_details
from adi_details_parse import parse_details


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run(root: Path, as_of: date, run: dict[str, Any]) -> None:
    path = root / "raw" / as_of.isoformat() / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(
    root: Path,
    results_html: bytes,
    results_source_url: str,
    control_numbers: list[str],
    *,
    fetch_details: Callable[..., dict[str, Any]] = fetch_details,
    today: date | None = None,
    chunk_size: int = 100,
) -> dict[str, Any]:
    """Fetch, parse, and save ADI details while isolating chunk failures."""

    root = Path(root)
    as_of = today or date.today()
    started_at = _now()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for start in range(0, len(control_numbers), chunk_size):
        chunk = control_numbers[start:start + chunk_size]
        try:
            response = fetch_details(
                results_html,
                results_source_url,
                chunk,
            )
        except Exception as error:
            failures.append(
                {
                    "control_numbers": chunk,
                    "reason": "fetch_error",
                    "detail": str(error),
                }
            )
            continue

        rows.extend(parse_details(response["body"]))

    raw_root = root / "raw" / as_of.isoformat()
    raw_root.mkdir(parents=True, exist_ok=True)
    (raw_root / "details.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "dataset": "adi_details",
        "as_of": as_of.isoformat(),
        "requested": len(control_numbers),
        "succeeded": len(rows),
        "failed": sum(len(failure["control_numbers"]) for failure in failures),
        "failures": failures,
        "started_at": started_at,
        "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run


__all__ = ["collect"]
