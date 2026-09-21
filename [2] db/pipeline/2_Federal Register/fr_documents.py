"""Build Federal Register document and identifier rows from detail responses."""

from __future__ import annotations

from typing import Any


def document_key(publication_date: str, document_number: str) -> str:
    """Return the stable public identity for a Federal Register document."""

    return f"{publication_date}/{document_number}"


def document_row(detail: dict[str, Any], manifest: list[dict[str, Any]]) -> dict[str, Any]:
    """Copy the API document fields into the first-pass document shape."""

    kinds = {entry.get("kind") for entry in manifest}
    if "xml" in kinds:
        body_status = "xml"
    elif "pdf" in kinds:
        body_status = "pdf_only"
    else:
        body_status = "missing"

    detail_entry = next(
        (entry for entry in reversed(manifest) if entry.get("kind") == "detail"),
        {},
    )
    return {
        "document_key": document_key(detail.get("publication_date"), detail.get("document_number")),
        "publication_date": detail.get("publication_date"),
        "document_number": detail.get("document_number"),
        "canonical_url": detail.get("html_url"),
        "title": detail.get("title"),
        "abstract": detail.get("abstract"),
        "type_raw": detail.get("type"),
        "action": detail.get("action"),
        "subtype": detail.get("subtype"),
        "agencies": detail.get("agencies"),
        "citation": detail.get("citation"),
        "volume": detail.get("volume"),
        "start_page": detail.get("start_page"),
        "end_page": detail.get("end_page"),
        "effective_on": detail.get("effective_on"),
        "comments_close_on": detail.get("comments_close_on"),
        "signing_date": detail.get("signing_date"),
        "docket_ids": detail.get("docket_ids"),
        "regulation_id_numbers": detail.get("regulation_id_numbers"),
        "full_text_xml_url": detail.get("full_text_xml_url"),
        "pdf_url": detail.get("pdf_url"),
        "content_hash": detail_entry.get("sha256"),
        "raw_metadata": detail,
        "scope_status": "part63_list",
        "body_status": body_status,
    }


def identifier_rows(document_key: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured docket and RIN identifiers in API order."""

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, Any]] = set()
    for docket in detail.get("dockets") or []:
        value = docket.get("id") if isinstance(docket, dict) else None
        key = ("docket", value)
        if value is not None and key not in seen:
            rows.append({"document_key": document_key, "identifier_kind": "docket", "identifier_value": value})
            seen.add(key)
    for value in detail.get("regulation_id_numbers") or []:
        key = ("rin", value)
        if value is not None and key not in seen:
            rows.append({"document_key": document_key, "identifier_kind": "rin", "identifier_value": value})
            seen.add(key)
    return rows
