"""Turn collected ADI and CAA Dashboard lists into source-entry rows."""

from __future__ import annotations

import hashlib
from typing import Any


def adi_entry_rows(
    rows: list[dict[str, Any]], details_by_control_number: dict[str, dict[str, Any]], list_sha256: str
) -> list[dict[str, Any]]:
    """Build ADI source rows, using details only to supplement list metadata."""

    result: list[dict[str, Any]] = []
    for source in rows:
        control_number = source["control_number"]
        detail = details_by_control_number.get(control_number, {})
        categories = detail.get("categories", source.get("categories", []))
        result.append(
            {
                "source_system": "adi",
                "source_key": control_number,
                "control_number": control_number,
                "facility_name": None,
                "title": detail.get("title", source.get("title")),
                "categories": categories,
                "office": detail.get("office", source.get("office")),
                "author": detail.get("author", source.get("author")),
                "recipient": None,
                "letter_date_raw": detail.get("letter_date_raw", source.get("letter_date_raw")),
                "link_text": None,
                "affected_subpart_raw": None,
                "abstract": detail.get("abstract"),
                "source_url": source.get("source_url"),
                "canonical_url": source.get("source_url"),
                "list_sha256": list_sha256,
                "scope_status": "part63_candidate"
                if set(categories) & {"MACT", "NESHAP", "GACT"}
                else "out_of_scope",
                "text_status": "text_missing",
            }
        )
    return result


def dashboard_source_key(row: dict[str, Any]) -> str:
    """Return the stable base key for a Dashboard row."""

    fields = (
        row.get("facility_name") or "",
        row.get("title") or "",
        row.get("affected_subpart_raw") or "",
        row.get("source_url") or "",
    )
    return hashlib.sha256("\t".join(fields).encode("utf-8")).hexdigest()[:16]


def dashboard_entry_rows(rows: list[dict[str, Any]], list_sha256: str) -> list[dict[str, Any]]:
    """Build Dashboard source rows, suffixing otherwise identical source keys."""

    seen: dict[str, int] = {}
    result: list[dict[str, Any]] = []
    for source in rows:
        base_key = dashboard_source_key(source)
        seen[base_key] = seen.get(base_key, 0) + 1
        source_key = base_key if seen[base_key] == 1 else f"{base_key}#{seen[base_key]}"
        affected = source.get("affected_subpart_raw") or ""
        result.append(
            {
                "source_system": "caa_dashboard",
                "source_key": source_key,
                "control_number": None,
                "facility_name": source.get("facility_name"),
                "title": source.get("title"),
                "categories": [],
                "office": None,
                "author": None,
                "recipient": None,
                "letter_date_raw": None,
                "link_text": source.get("link_text"),
                "affected_subpart_raw": source.get("affected_subpart_raw"),
                "abstract": None,
                "source_url": source.get("source_url"),
                "canonical_url": source.get("canonical_url"),
                "list_sha256": list_sha256,
                "scope_status": "part63_candidate" if "Part 63" in affected else "out_of_scope",
                "text_status": "text_missing",
            }
        )
    return result

