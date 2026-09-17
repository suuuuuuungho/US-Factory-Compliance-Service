"""Store validated ECHO ZIP downloads with a durable manifest."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import shutil
from typing import Sequence

from echo_fetch import Fetched
from echo_zip import MemberSpec


def store_raw(
    root: Path, as_of: date, fetched: Fetched, members: Sequence[MemberSpec]
) -> dict:
    """Move a validated ZIP under *root* and record its immutable metadata."""

    raw_root = root / "raw" / as_of.isoformat()
    manifest_path = raw_root / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else []
    )
    for entry in manifest:
        if entry["sha256"] == fetched.sha256:
            fetched.path.unlink(missing_ok=True)
            return entry

    final = raw_root / fetched.sha256 / fetched.path.name
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(fetched.path), str(final))
    entry = {
        "name": fetched.path.name,
        "path": final.relative_to(root).as_posix(),
        "source_url": fetched.source_url,
        "final_url": fetched.final_url,
        "http_status": fetched.http_status,
        "media_type": fetched.media_type,
        "etag": fetched.etag,
        "last_modified": fetched.last_modified,
        "sha256": fetched.sha256,
        "byte_size": fetched.byte_size,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "members": [asdict(member) for member in members],
    }
    manifest.append(entry)
    part = Path(str(manifest_path) + ".part")
    part.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(part), str(manifest_path))
    return entry
