"""Run Dashboard letter collection from a saved Dashboard page."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_dashboard import parse_dashboard
from dashboard_letters import fetch_letter
from dashboard_letters_collect import collect as letters_collect


def run(
    dashboard_root: Path,
    letters_root: Path,
    *,
    fetch_letter: Callable[..., dict[str, Any]] = fetch_letter,
    today: date | None = None,
) -> dict[str, Any]:
    """Collect each unique letter referenced by today's saved Dashboard run."""

    dashboard_root = Path(dashboard_root)
    as_of = today or date.today()

    run_path = dashboard_root / "raw" / as_of.isoformat() / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(
            f"no Dashboard run found for {as_of.isoformat()} in {dashboard_root}"
        )

    dashboard_run = json.loads(run_path.read_text(encoding="utf-8"))
    html_path = (
        dashboard_root
        / "raw"
        / as_of.isoformat()
        / dashboard_run["html_sha256"]
        / "caa-dashboard.html"
    )
    rows = parse_dashboard(html_path.read_bytes())
    canonical_urls = sorted(
        {row["canonical_url"] for row in rows if row["canonical_url"]}
    )

    return letters_collect(
        letters_root,
        canonical_urls,
        fetch_letter=fetch_letter,
        today=today,
    )


__all__ = ["run"]
