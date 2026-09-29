"""Run the complete ECHO release ingestion workflow: register → load → check → publish."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "1_eCFR"))
from ecfr_publish import publish_release  # noqa: E402  # dataset을 release 행에서 읽어 ECHO에도 그대로 쓴다 (SUU-125)
from echo_check import check_release  # noqa: E402
from echo_load import load_release  # noqa: E402
from echo_release import published_release_id, register_release  # noqa: E402
from echo_retire import retire_other_releases  # noqa: E402


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
    published_release_id: Callable[..., str | None] = published_release_id,
    register_release: Callable[..., str] = register_release,
    load_release: Callable[..., dict] = load_release,
    check_release: Callable[..., dict] = check_release,
    publish_release: Callable[..., None] = publish_release,
    retire_other_releases: Callable[..., list[str]] = retire_other_releases,
) -> dict[str, str]:
    """Register, load, check, publish, and retire one ECHO release."""

    existing = published_release_id(root, as_of, client=client)
    if existing:
        return {"release_id": existing, "status": "no_change"}

    release_id = register_release(root, as_of, client=client)
    load_release(root, as_of, release_id, code_map_version or _latest_as_of(Path(root) / "code_map"), conn=conn)
    result = check_release(root, as_of, release_id, conn=conn)
    if not result["ok"]:
        client.table("common_dataset_release").update({"status": "failed"}).eq("release_id", release_id).execute()
        raise CheckFailed(release_id, result["problems"])
    publish_release(release_id, client=client)
    retire_other_releases(release_id, client=client, conn=conn)
    return {"release_id": release_id, "status": "new"}


def format_result(result: dict[str, str]) -> str:
    """Format an ingest result for the workflow output parser."""

    return f"status={result['status']} release_id={result['release_id']}"


if __name__ == "__main__":
    import psycopg
    from supabase import create_client

    pipeline_root = Path(__file__).resolve().parents[2] / "3) ECHO"
    selected_as_of = sys.argv[1] if len(sys.argv) > 1 else _latest_as_of(pipeline_root / "parsed")
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        try:
            print(format_result(run_echo_ingest(pipeline_root, selected_as_of, client=client, conn=conn)))
        except CheckFailed as failed:
            print(f"release {failed.release_id} failed check:\n{failed}", file=sys.stderr)
            sys.exit(1)


__all__ = ["CheckFailed", "format_result", "run_echo_ingest"]
