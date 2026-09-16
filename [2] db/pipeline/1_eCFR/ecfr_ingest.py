"""Run the complete eCFR release ingestion workflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

from supabase import create_client

from ecfr_load import load_release
from ecfr_publish import publish_release
from ecfr_release import register_release


def _latest_as_of(raw_root: Path) -> str:
    """Return the newest as-of directory name under ``raw_root``."""

    as_of_folders = [path.name for path in Path(raw_root).iterdir() if path.is_dir()]
    if not as_of_folders:
        raise FileNotFoundError(f"no as_of folders found under {raw_root}")
    return max(as_of_folders)


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


if __name__ == "__main__":
    pipeline_root = Path(__file__).resolve().parents[2] / "1) eCFR"
    raw_root = pipeline_root / "raw"
    selected_as_of = sys.argv[1] if len(sys.argv) > 1 else _latest_as_of(raw_root)
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SECRET_KEY"],
    )
    print(run_ecfr_ingest(pipeline_root, selected_as_of, client=client))


__all__ = ["run_ecfr_ingest"]
