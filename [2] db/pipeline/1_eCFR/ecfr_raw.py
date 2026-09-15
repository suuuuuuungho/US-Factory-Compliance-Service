"""Persist downloaded eCFR bytes and their provenance manifest."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _atomic_write(path: Path, data: bytes) -> None:
    """Write bytes to the required adjacent ``.part`` path, then replace."""

    part = Path(f"{path}.part")
    part.write_bytes(data)
    os.replace(str(part), str(path))


def save_raw(
    root: Path,
    as_of: date,
    name: str,
    body: bytes,
    *,
    source_url: str,
    final_url: str,
    http_status: int,
    media_type: str,
) -> dict[str, Any]:
    """Save one raw response and return its manifest entry.

    Entries with the same filename and content hash are idempotent: the
    existing entry is returned without rewriting either the data or manifest.
    """

    root = Path(root)
    raw_root = root / "raw" / as_of.isoformat()
    manifest_path = raw_root / "manifest.json"
    raw_root.mkdir(parents=True, exist_ok=True)

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = []

    digest = hashlib.sha256(body).hexdigest()
    for entry in manifest:
        if entry.get("name") == name and entry.get("sha256") == digest:
            return entry

    final_path = raw_root / digest / name
    final_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(final_path, body)

    entry: dict[str, Any] = {
        "name": name,
        "path": final_path.relative_to(root).as_posix(),
        "source_url": source_url,
        "final_url": final_url,
        "http_status": http_status,
        "media_type": media_type,
        "byte_size": len(body),
        "sha256": digest,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.append(entry)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    _atomic_write(manifest_path, manifest_bytes)
    return entry


__all__ = ["save_raw"]
