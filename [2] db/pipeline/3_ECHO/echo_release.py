"""Register one collected ECHO snapshot (two ZIPs) as a dataset release."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


DATASET = "echo"
SCOPE_KEY = "icis_air_national+caa_pipeline"
PARSER_VERSION = "1"  # 파서 규칙이 바뀌면 올린다 — 같은 ZIP이라도 새 release가 된다

_ROLES = (("icis_air", "ICIS-AIR_downloads.zip"), ("pipeline", "pipeline_caa_downloads.zip"))


def _manifest_entry(manifest: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for entry in reversed(manifest):
        if entry.get("name") == name:
            return entry
    raise FileNotFoundError(f"{name} is missing from the raw manifest")


def _timestamp(now: datetime | None) -> str:
    value = now if now is not None else datetime.now(timezone.utc)
    return value.isoformat()


def _http_date(value: str | None) -> str | None:
    return parsedate_to_datetime(value).isoformat() if value else None


def register_release(
    root: Path,
    as_of: str,
    *,
    client: Any,
    now: datetime | None = None,
) -> str:
    """Register the two raw ZIPs for ``as_of`` and return their release ID."""

    root = Path(root)
    manifest = json.loads((root / "raw" / as_of / "manifest.json").read_text(encoding="utf-8"))
    entries = [(role, _manifest_entry(manifest, name)) for role, name in _ROLES]

    manifest_hash = hashlib.sha256(":".join(entry["sha256"] for _, entry in entries).encode()).hexdigest()
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
            "scope": {"zips": [name for _, name in _ROLES]},
            "status": "succeeded",
            "started_at": timestamp,
            "finished_at": timestamp,
            "counts": {"raw_objects": len(entries)},
            "error_summary": None,
        }
    ).execute()

    object_ids: list[tuple[str, str]] = []
    for role, entry in entries:
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
                "source_modified_at": _http_date(entry.get("last_modified")),
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


__all__ = ["DATASET", "PARSER_VERSION", "SCOPE_KEY", "register_release"]
