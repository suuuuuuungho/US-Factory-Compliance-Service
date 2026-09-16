"""Register one collected eCFR snapshot as a dataset release."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ecfr_parse import PARSER_VERSION


DATASET = "ecfr"
SCOPE_KEY = "40/63"


def _manifest_entry(manifest: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for entry in reversed(manifest):
        if entry.get("name") == name:
            return entry
    raise FileNotFoundError(f"{name} is missing from the raw manifest")


def _timestamp(now: datetime | None) -> str:
    value = now if now is not None else datetime.now(timezone.utc)
    return value.isoformat()


def register_release(
    root: Path,
    as_of: str,
    *,
    client: Any,
    now: datetime | None = None,
) -> str:
    """Register the raw files for ``as_of`` and return their release ID."""

    root = Path(root)
    manifest_path = root / "raw" / as_of / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    structure = _manifest_entry(manifest, "title-40-structure.json")
    xml = _manifest_entry(manifest, "title-40-part-63.xml")

    manifest_hash = hashlib.sha256(
        f'{structure["sha256"]}:{xml["sha256"]}'.encode()
    ).hexdigest()
    existing = (
        client.table("common_dataset_release")
        .select("release_id")
        .eq("dataset", DATASET)
        .eq("scope_key", SCOPE_KEY)
        .eq("manifest_hash", manifest_hash)
        .eq("parser_version", PARSER_VERSION)
        .execute()
        .data
    )
    if existing:
        return str(existing[0]["release_id"])

    timestamp = _timestamp(now)
    run_id = str(uuid4())
    client.table("common_ingest_run").insert(
        {
            "run_id": run_id,
            "dataset": DATASET,
            "scope": {"title": "40", "part": "63"},
            "status": "succeeded",
            "started_at": timestamp,
            "finished_at": timestamp,
            "counts": {"raw_objects": 2},
            "error_summary": None,
        }
    ).execute()

    object_ids: list[tuple[str, str]] = []
    for role, entry in (("structure", structure), ("xml", xml)):
        object_id = str(uuid4())
        client.table("common_raw_object").insert(
            {
                "object_id": object_id,
                "run_id": run_id,
                "source_url": entry["source_url"],
                "final_url": entry.get("final_url"),
                "storage_uri": entry["path"],
                "sha256": entry["sha256"],
                "byte_size": entry.get("byte_size"),
                "media_type": entry.get("media_type"),
                "fetched_at": entry["fetched_at"],
                "source_modified_at": entry.get("source_modified_at"),
                "etag": entry.get("etag"),
            }
        ).execute()
        object_ids.append((role, object_id))

    release_id = str(uuid4())
    client.table("common_dataset_release").insert(
        {
            "release_id": release_id,
            "dataset": DATASET,
            "scope_key": SCOPE_KEY,
            "run_id": run_id,
            "source_as_of": as_of,
            "manifest_hash": manifest_hash,
            "parser_version": PARSER_VERSION,
            "status": "staging",
            "published_at": None,
        }
    ).execute()

    for role, object_id in object_ids:
        client.table("common_release_object").insert(
            {"release_id": release_id, "object_id": object_id, "role": role}
        ).execute()

    return release_id


__all__ = ["DATASET", "SCOPE_KEY", "register_release"]
