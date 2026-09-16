"""Publish a validated eCFR release and update its current pointer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _timestamp(now: datetime | None) -> str:
    value = now if now is not None else datetime.now(timezone.utc)
    return value.isoformat()


def publish_release(
    release_id: str,
    *,
    client: Any,
    now: datetime | None = None,
) -> None:
    """Mark ``release_id`` as published and make it the current release."""

    release = (
        client.table("common_dataset_release")
        .select("dataset,scope_key,source_as_of")
        .eq("release_id", release_id)
        .execute()
        .data[0]
    )
    timestamp = _timestamp(now)

    (
        client.table("common_dataset_release")
        .update({"status": "published", "published_at": timestamp})
        .eq("release_id", release_id)
        .execute()
    )

    client.table("common_dataset_current").upsert(
        {
            "dataset": release["dataset"],
            "scope_key": release["scope_key"],
            "release_id": release_id,
            "last_checked_at": timestamp,
            "latest_source_as_of": release["source_as_of"],
        },
        on_conflict="dataset,scope_key",
    ).execute()


__all__ = ["publish_release"]
