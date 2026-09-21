"""Register Federal Register raw objects as one dataset release."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DATASET = "fr"
SCOPE_KEY = "part63_metadata"
PARSER_VERSION = "1"


def _timestamp(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _entries(root: Path) -> list[dict[str, Any]]:
    result = []
    raw = root / "raw"
    for year in sorted(raw.iterdir() if raw.exists() else [], key=lambda p: p.name):
        if not year.is_dir() or year.name == "lists":
            continue
        for folder in sorted(year.iterdir(), key=lambda p: p.name):
            manifest = folder / "manifest.json"
            if folder.is_dir() and manifest.exists():
                result.extend(json.loads(manifest.read_text(encoding="utf-8")))
    return result


def _chunks(values: list[Any], size: int):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def register_release(root: Path, as_of: str, *, client: Any, now: datetime | None = None) -> str:
    root = Path(root)
    entries = _entries(root)
    manifest_hash = hashlib.sha256(":".join(sorted(e["sha256"] for e in entries)).encode()).hexdigest()
    existing = (client.table("common_dataset_release").select("release_id").eq("dataset", DATASET)
        .eq("scope_key", SCOPE_KEY).eq("manifest_hash", manifest_hash).eq("parser_version", PARSER_VERSION).execute().data)
    if existing:
        return str(existing[0]["release_id"])

    timestamp, run_id = _timestamp(now), str(uuid4())
    client.table("common_ingest_run").insert({"run_id": run_id, "dataset": DATASET,
        "scope": {"as_of": as_of, "documents": len({Path(e["path"]).parts[2] for e in entries})},
        "status": "succeeded", "started_at": timestamp, "finished_at": timestamp,
        "counts": {"raw_objects": len(entries)}, "error_summary": None}).execute()

    known: dict[tuple[str, str], str] = {}
    for batch in _chunks(entries, 200):
        rows = (client.table("common_raw_object").select("object_id,source_url,sha256")
                .in_("sha256", [entry["sha256"] for entry in batch]).execute().data)
        known.update({(row["source_url"], row["sha256"]): str(row["object_id"]) for row in rows})
    fresh = []
    for entry in entries:
        key = (entry["source_url"], entry["sha256"])
        if key not in known:
            object_id = str(uuid4())
            known[key] = object_id
            fresh.append({"object_id": object_id, "run_id": run_id, "source_url": entry["source_url"],
                "final_url": entry.get("final_url"), "storage_uri": entry["path"], "sha256": entry["sha256"],
                "byte_size": entry.get("byte_size"), "media_type": entry.get("media_type"), "fetched_at": entry.get("fetched_at"),
                "source_modified_at": None, "etag": None})
    for batch in _chunks(fresh, 500):
        client.table("common_raw_object").insert(batch).execute()

    release_id = str(uuid4())
    client.table("common_dataset_release").insert({"release_id": release_id, "dataset": DATASET, "scope_key": SCOPE_KEY,
        "run_id": run_id, "source_as_of": as_of, "manifest_hash": manifest_hash, "parser_version": PARSER_VERSION,
        "status": "staging", "published_at": None}).execute()
    objects = [{"release_id": release_id, "object_id": known[(entry["source_url"], entry["sha256"])], "role": entry["kind"]} for entry in entries]
    for batch in _chunks(objects, 500):
        client.table("common_release_object").insert(batch).execute()
    return release_id


__all__ = ["DATASET", "PARSER_VERSION", "SCOPE_KEY", "register_release"]
