"""Extract deterministic ADI document, version, link, and page rows."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

from adi_letters_text import extract_pages


PARSER_VERSION = "1"


def document_id(sha256: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"adi-document:{sha256}"))


def version_id(sha256: str, parser_version: str = PARSER_VERSION) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"adi-version:{sha256}:{parser_version}"))


def build_documents(
    files: list[dict[str, Any]], *, reader_factory: Callable[[bytes], Any] | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Extract each unique PDF and retain unreadable files as held entries."""

    output: dict[str, list[dict[str, Any]]] = {
        "adi_document": [], "adi_document_version": [], "adi_entry_document": [], "adi_page": [], "held": []
    }
    by_sha: dict[str, list[dict[str, Any]]] = {}
    for file in files:
        by_sha.setdefault(file["sha256"], []).append(file)

    for sha256 in sorted(by_sha):
        group = sorted(by_sha[sha256], key=lambda item: (item["source_key"], item["source_system"]))
        try:
            body = Path(group[0]["path"]).read_bytes()
            kwargs = {"reader_factory": reader_factory} if reader_factory is not None else {}
            extracted = extract_pages(body, **kwargs)
        except Exception as error:
            for file in group:
                output["held"].append({
                    "source_system": file["source_system"], "source_key": file["source_key"],
                    "sha256": sha256, "reason": str(error) or type(error).__name__,
                })
            continue

        doc_id, ver_id = document_id(sha256), version_id(sha256)
        output["adi_document"].append({"document_id": doc_id, "canonical_identity": f"sha256:{sha256}"})
        dated = next((file for file in group if file.get("letter_date_raw")), None)
        statuses = {page["status"] for page in extracted}
        ok_text = [page["text"] for page in extracted if page["status"] == "ok"]
        quality = "no_text" if not ok_text else ("ok" if statuses == {"ok"} else "partial")
        output["adi_document_version"].append({
            "version_id": ver_id, "document_id": doc_id, "sha256": sha256, "signed_on": None,
            "signed_on_raw": dated.get("letter_date_raw") if dated else None,
            "date_source": "adi_list" if dated else None,
            "text_content": "\n\n".join(ok_text), "extraction_method": "pypdf",
            "parser_version": PARSER_VERSION, "quality_status": quality, "legal_status": "unknown",
        })
        for file in group:
            output["adi_entry_document"].append({
                "source_system": file["source_system"], "source_key": file["source_key"],
                "version_id": ver_id, "match_method": "fetched_from_entry", "match_status": "confirmed",
            })
        for page in extracted:
            output["adi_page"].append({
                "version_id": ver_id, "page_no": page["page_no"], "text_content": page["text"],
                "extraction_method": "pypdf", "ocr_confidence": None, "status": page["status"],
                "failure_reason": page.get("reason") if page["status"] == "failed" else None,
                "review_status": "검토 전",
            })
    return output

