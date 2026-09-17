"""Run the complete ECHO release ingestion workflow: register → load → check → publish."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

from ecfr_publish import publish_release  # dataset을 release 행에서 읽어 ECHO에도 그대로 쓴다 (SUU-125)
from echo_check import check_release
from echo_load import load_release
from echo_release import register_release


class CheckFailed(RuntimeError):
    """The loaded release did not pass check_release; it was marked failed and not published."""

    def __init__(self, release_id: str, problems: list[str]):
        super().__init__("\n".join(problems))
        self.release_id = release_id
        self.problems = problems


def _latest_as_of(parsed_root: Path) -> str:
    """Return the newest as-of directory name under ``parsed_root``."""

    folders = [path.name for path in Path(parsed_root).iterdir() if path.is_dir()]
    if not folders:
        raise FileNotFoundError(f"no as_of folders found under {parsed_root}")
    return max(folders)


def run_echo_ingest(
    root: Path,
    as_of: str,
    *,
    client: Any,
    conn: Any,
    code_map_version: str | None = None,
    register_release: Callable[..., str] = register_release,
    load_release: Callable[..., dict] = load_release,
    check_release: Callable[..., dict] = check_release,
    publish_release: Callable[..., None] = publish_release,
) -> str:
    """Register, load, check and publish one ECHO release; return its release_id."""

    release_id = register_release(root, as_of, client=client)
    load_release(root, as_of, release_id, code_map_version or as_of, conn=conn)
    result = check_release(root, as_of, release_id, conn=conn)
    if not result["ok"]:
        client.table("common_dataset_release").update({"status": "failed"}).eq("release_id", release_id).execute()
        raise CheckFailed(release_id, result["problems"])
    publish_release(release_id, client=client)
    return release_id


if __name__ == "__main__":
    import psycopg
    from supabase import create_client

    pipeline_root = Path(__file__).resolve().parents[2] / "3) ECHO"
    selected_as_of = sys.argv[1] if len(sys.argv) > 1 else _latest_as_of(pipeline_root / "parsed")
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        try:
            print(run_echo_ingest(pipeline_root, selected_as_of, client=client, conn=conn))
        except CheckFailed as failed:
            print(f"release {failed.release_id} failed check:\n{failed}", file=sys.stderr)
            sys.exit(1)


__all__ = ["CheckFailed", "run_echo_ingest"]
