"""Run ADI detail collection from a saved ADI results page."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_details import fetch_details
from adi_details_collect import collect as details_collect
from adi_results import parse_results


def run(
    adi_root: Path,
    details_root: Path,
    *,
    fetch_details: Callable[..., dict[str, Any]] = fetch_details,
    today: date | None = None,
) -> dict[str, Any]:
    """Collect details for each unique control number in today's saved ADI run."""

    adi_root = Path(adi_root)
    as_of = today or date.today()

    run_dir = adi_root / "raw" / as_of.isoformat()
    run_path = run_dir / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(
            f"no ADI run found for {as_of.isoformat()} in {adi_root}"
        )

    adi_run = json.loads(run_path.read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    entry = next(
        item for item in manifest if item["sha256"] == adi_run["html_sha256"]
    )

    html_path = run_dir / adi_run["html_sha256"] / "adi-results.html"
    results_html = html_path.read_bytes()
    rows = parse_results(results_html)["rows"]
    control_numbers = sorted({row["control_number"] for row in rows})

    return details_collect(
        details_root,
        results_html,
        entry["final_url"],
        control_numbers,
        fetch_details=fetch_details,
        today=today,
    )


__all__ = ["run"]
