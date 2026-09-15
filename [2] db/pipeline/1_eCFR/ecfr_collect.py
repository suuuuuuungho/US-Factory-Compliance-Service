"""Run one consistent eCFR Title 40 / Part 63 raw collection."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ecfr_fetch import ensure_xml, fetch, part_xml_url, structure_url
from ecfr_raw import save_raw
from ecfr_structure import count_by_type, find_part
from ecfr_titles import fetch_titles, parse_title_status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run(root: Path, as_of: str, run: dict[str, Any]) -> None:
    path = root / "raw" / as_of / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(
    root: Path,
    *,
    fetch_titles: Callable[..., dict[str, Any]] = fetch_titles,
    fetch: Callable[[str], Any] = fetch,
) -> dict[str, Any]:
    """Collect structure and Part 63 XML only from a stable eCFR snapshot."""

    root = Path(root)
    started_at = _now()
    before = parse_title_status(fetch_titles())
    as_of = before.up_to_date_as_of.isoformat()
    run: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "dataset": "ecfr",
        "as_of": as_of,
        "import_in_progress": before.import_in_progress,
        "status": "held",
        "reason": None,
        "counts": None,
        "structure_sha256": None,
        "xml_sha256": None,
        "started_at": started_at,
        "finished_at": None,
    }

    if before.import_in_progress:
        run["reason"] = "import_in_progress"
        run["finished_at"] = _now()
        _write_run(root, as_of, run)
        return run

    structure_response = fetch(structure_url(before.up_to_date_as_of))
    structure = json.loads(structure_response.body)
    counts = count_by_type(find_part(structure, "63"))

    xml_response = fetch(part_xml_url(before.up_to_date_as_of))
    xml_body = ensure_xml(xml_response.body)

    structure_entry = save_raw(
        root,
        before.up_to_date_as_of,
        "title-40-structure.json",
        structure_response.body,
        source_url=structure_response.source_url,
        final_url=structure_response.final_url,
        http_status=structure_response.http_status,
        media_type=structure_response.media_type,
    )
    xml_entry = save_raw(
        root,
        before.up_to_date_as_of,
        "title-40-part-63.xml",
        xml_body,
        source_url=xml_response.source_url,
        final_url=xml_response.final_url,
        http_status=xml_response.http_status,
        media_type=xml_response.media_type,
    )

    after = parse_title_status(fetch_titles())
    run["import_in_progress"] = after.import_in_progress
    run["counts"] = counts
    run["structure_sha256"] = structure_entry["sha256"]
    run["xml_sha256"] = xml_entry["sha256"]
    if after.import_in_progress or after.up_to_date_as_of != before.up_to_date_as_of:
        run["reason"] = "import_in_progress" if after.import_in_progress else "as_of_changed"
    else:
        run["status"] = "succeeded"
    run["finished_at"] = _now()
    _write_run(root, as_of, run)
    return run


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "1) eCFR"
    result = collect(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "succeeded" else 2)


__all__ = ["collect"]
