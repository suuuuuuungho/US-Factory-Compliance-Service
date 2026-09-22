"""Register ADI and CAA Dashboard raw artifacts as one release."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DATASET = "adi"
SCOPE_KEY = "adi+caa_dashboard"
PARSER_VERSION = "1"


def _chunks(values: list[Any], size: int):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _timestamp(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _entries(root: Path, raw_as_of: str) -> list[dict[str, Any]]:
    entries = []
    for manifest in sorted(root.glob(f"**/raw/{raw_as_of}/manifest.json")):
        dataset_root = manifest.parent.parents[1]
        for entry in json.loads(manifest.read_text(encoding="utf-8")):
            entries.append({**entry, "storage_uri": (dataset_root / entry["path"]).relative_to(root).as_posix()})
    return entries


def register_release(root: Path, as_of: str, *, client: Any, now: datetime | None = None) -> str:
    root = Path(root)
    report = json.loads((root / "parsed" / as_of / "quality_report.json").read_text(encoding="utf-8"))
    raw_as_of = report["raw_as_of"]
    entries = _entries(root, raw_as_of)
    manifest_hash = hashlib.sha256(":".join(sorted(entry["sha256"] for entry in entries)).encode()).hexdigest()
    existing = (client.table("common_dataset_release").select("release_id").eq("dataset", DATASET)
                .eq("scope_key", SCOPE_KEY).eq("manifest_hash", manifest_hash)
                .eq("parser_version", PARSER_VERSION).execute().data)
    if existing:
        return str(existing[0]["release_id"])

    timestamp, run_id = _timestamp(now), str(uuid4())
    client.table("common_ingest_run").insert({
        "run_id": run_id, "dataset": DATASET,
        "scope": {"as_of": as_of, "raw_as_of": raw_as_of,
                  "manifests": len(list(root.glob(f"**/raw/{raw_as_of}/manifest.json")))},
        "status": "succeeded", "started_at": timestamp, "finished_at": timestamp,
        "counts": {"raw_objects": len(entries)}, "error_summary": None,
    }).execute()

    known: dict[tuple[str, str], str] = {}
    for batch in _chunks(entries, 200):
        rows = (client.table("common_raw_object").select("object_id,source_url,sha256")
                .in_("sha256", [entry["sha256"] for entry in batch]).execute().data)
        known.update({(row["source_url"], row["sha256"]): str(row["object_id"]) for row in rows})
    fresh = []
    for entry in entries:
        key = (entry["source_url"], entry["sha256"])
        if key not in known:
            known[key] = str(uuid4())
            fresh.append({"object_id": known[key], "run_id": run_id, "source_url": entry["source_url"],
                          "final_url": entry.get("final_url"), "storage_uri": entry["storage_uri"],
                          "sha256": entry["sha256"], "byte_size": entry.get("byte_size"),
                          "media_type": entry.get("media_type"), "fetched_at": entry.get("fetched_at"),
                          "source_modified_at": None, "etag": None})
    for batch in _chunks(fresh, 500):
        client.table("common_raw_object").insert(batch).execute()

    release_id = str(uuid4())
    client.table("common_dataset_release").insert({
        "release_id": release_id, "dataset": DATASET, "scope_key": SCOPE_KEY, "run_id": run_id,
        "source_as_of": as_of, "manifest_hash": manifest_hash, "parser_version": PARSER_VERSION,
        "status": "staging", "published_at": None,
    }).execute()
    links = [{"release_id": release_id, "object_id": known[(entry["source_url"], entry["sha256"])],
              "role": "list" if entry["name"].endswith(".html") else "letter"} for entry in entries]
    for batch in _chunks(links, 500):
        client.table("common_release_object").insert(batch).execute()
    return release_id


__all__ = ["DATASET", "PARSER_VERSION", "SCOPE_KEY", "register_release"]
