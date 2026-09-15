"""Collect PDF response documents for CAA Dashboard canonical URLs."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dashboard_letters import fetch_letter
from ecfr_raw import save_raw


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run(root: Path, as_of: date, run: dict[str, Any]) -> None:
    path = root / "raw" / as_of.isoformat() / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(
    root: Path,
    canonical_urls: list[str],
    *,
    fetch_letter: Callable[..., dict[str, Any]] = fetch_letter,
    today: date | None = None,
) -> dict[str, Any]:
    """Fetch each Dashboard letter, saving PDFs and recording failures."""

    root = Path(root)
    as_of = today or date.today()
    started_at = _now()
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for canonical_url in canonical_urls:
        try:
            letter = fetch_letter(canonical_url)
        except Exception as error:
            failures.append(
                {
                    "canonical_url": canonical_url,
                    "reason": "fetch_error",
                    "detail": str(error),
                }
            )
            continue

        if not letter["is_pdf"]:
            failures.append(
                {"canonical_url": canonical_url, "reason": "not_pdf"}
            )
            continue

        name = f"{hashlib.sha256(canonical_url.encode()).hexdigest()}.pdf"
        entry = save_raw(
            root,
            as_of,
            name,
            letter["body"],
            source_url=letter["source_url"],
            final_url=letter["final_url"],
            http_status=letter["http_status"],
            media_type=letter["media_type"],
        )
        successes.append(
            {
                "canonical_url": canonical_url,
                "sha256": entry["sha256"],
                "path": entry["path"],
            }
        )

    failure_reasons: dict[str, int] = {}
    for failure in failures:
        reason = failure["reason"]
        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    run: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "dataset": "caa_dashboard_letters",
        "as_of": as_of.isoformat(),
        "requested": len(canonical_urls),
        "succeeded": len(successes),
        "failed": len(failures),
        "failure_reasons": failure_reasons,
        "failures": failures,
        "started_at": started_at,
        "finished_at": _now(),
    }
    _write_run(root, as_of, run)
    return run


__all__ = ["collect"]
