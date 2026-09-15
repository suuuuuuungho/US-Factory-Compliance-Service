"""Run ADI letter collection from a saved ADI results page."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from adi_letters import fetch_letter
from adi_letters_collect import collect as letters_collect
from adi_results import parse_results


def run(
    adi_root: Path,
    letters_root: Path,
    *,
    fetch_letter: Callable[..., dict[str, Any]] = fetch_letter,
    today: date | None = None,
) -> dict[str, Any]:
    """Collect each unique letter referenced by today's saved ADI run."""

    adi_root = Path(adi_root)
    as_of = today or date.today()

    run_path = adi_root / "raw" / as_of.isoformat() / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(
            f"no ADI run found for {as_of.isoformat()} in {adi_root}"
        )

    adi_run = json.loads(run_path.read_text(encoding="utf-8"))
    html_path = (
        adi_root
        / "raw"
        / as_of.isoformat()
        / adi_run["html_sha256"]
        / "adi-results.html"
    )
    rows = parse_results(html_path.read_bytes())["rows"]
    control_numbers = sorted({row["control_number"] for row in rows})

    return letters_collect(
        letters_root,
        control_numbers,
        fetch_letter=fetch_letter,
        today=today,
    )


__all__ = ["run"]
