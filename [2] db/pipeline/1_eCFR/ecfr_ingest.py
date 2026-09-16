"""Run the complete eCFR release ingestion workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ecfr_load import load_release
from ecfr_publish import publish_release
from ecfr_release import register_release


def run_ecfr_ingest(
    root: Path,
    as_of: str,
    *,
    client: Any,
    register_release: Callable[..., str] = register_release,
    load_release: Callable[..., None] = load_release,
    publish_release: Callable[..., None] = publish_release,
) -> str:
    """Register, load, and publish one eCFR release."""

    release_id = register_release(root, as_of, client=client)
    load_release(root, as_of, release_id, client=client)
    publish_release(release_id, client=client)
    return release_id


__all__ = ["run_ecfr_ingest"]
