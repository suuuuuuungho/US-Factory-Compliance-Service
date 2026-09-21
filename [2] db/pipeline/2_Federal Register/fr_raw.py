"""Durably store Federal Register raw responses and their manifests."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from fr_fetch import Fetched


_EXTENSIONS = {"detail": "json", "xml": "xml", "pdf": "pdf"}


def store_raw(root: Path, publication_date: str, document_number: str, fetched: Fetched, *, kind: str) -> dict:
    """Archive one response under its publication and content digest."""

    folder = Path(root) / "raw" / publication_date[:4] / f"{publication_date}_{document_number}"
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    for entry in manifest:
        if entry["sha256"] == fetched.sha256:
            return entry
    filename = f"{document_number}.{_EXTENSIONS[kind]}"
    final = folder / fetched.sha256 / filename
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(fetched.body)
    entry = {
        "kind": kind, "name": filename, "path": final.relative_to(root).as_posix(),
        "source_url": fetched.source_url, "final_url": fetched.final_url,
        "http_status": fetched.http_status, "media_type": fetched.media_type,
        "sha256": fetched.sha256, "byte_size": fetched.byte_size,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.append(entry)
    part = Path(str(manifest_path) + ".part")
    part.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(part, manifest_path)
    return entry
