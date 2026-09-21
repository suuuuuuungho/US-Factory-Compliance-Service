"""Build first-pass CFR-reference and date-event rows."""

from __future__ import annotations

from typing import Any


REVIEW_STATUS = "검토 전"


def cfr_reference_rows(document_key: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep API CFR references at part granularity without interpretation."""

    rows: list[dict[str, Any]] = []
    for index, reference in enumerate(detail.get("cfr_references") or []):
        title = reference.get("title")
        part_value = reference.get("part")
        part = str(part_value) if part_value is not None else None
        citation = f"{title} CFR" + (f" {part}" if part is not None else "")
        rows.append({
            "document_key": document_key,
            "title": title,
            "part": part,
            "subpart": None,
            "section": None,
            "paragraph": None,
            "relation_type": "affects",
            "raw_citation": citation,
            "evidence_locator": f"api:cfr_references[{index}]",
            "review_status": REVIEW_STATUS,
        })
    return rows


def date_event_rows(document_key: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Represent only the API effective date as an event in this pass."""

    effective_on = detail.get("effective_on")
    if not effective_on:
        return []
    return [{
        "document_key": document_key,
        "event_kind": "effective",
        "event_date": effective_on,
        "applies_to": None,
        "raw_text": detail.get("dates"),
        "evidence_locator": "api:effective_on",
        "review_status": REVIEW_STATUS,
    }]
