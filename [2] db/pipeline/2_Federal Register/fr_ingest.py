"""Run the Federal Register release workflow."""
from __future__ import annotations
import os, sys
from pathlib import Path
from typing import Any, Callable
from ecfr_publish import publish_release
from fr_check import check_release
from fr_load import load_release
from fr_release import published_release_id, register_release

class CheckFailed(RuntimeError):
    def __init__(self, release_id: str, problems: list[str]):
        super().__init__("\n".join(problems)); self.release_id, self.problems = release_id, problems

def _latest_as_of(parsed_root: Path) -> str:
    folders = [p.name for p in Path(parsed_root).iterdir() if p.is_dir()]
    if not folders: raise FileNotFoundError(f"no as_of folders found under {parsed_root}")
    return max(folders)

def run_fr_ingest(root: Path, as_of: str, *, client: Any, conn: Any, published_release_id: Callable[..., str | None] = published_release_id, register_release: Callable[..., str] = register_release, load_release: Callable[..., dict] = load_release, check_release: Callable[..., dict] = check_release, publish_release: Callable[..., None] = publish_release) -> dict[str, str]:
    existing = published_release_id(root, as_of, client=client)
    if existing:
        return {"release_id": existing, "status": "no_change"}
    release_id = register_release(root, as_of, client=client)
    load_release(root, as_of, release_id, conn=conn)
    result = check_release(root, as_of, release_id, conn=conn)
    if not result["ok"]:
        client.table("common_dataset_release").update({"status": "failed"}).eq("release_id", release_id).execute()
        raise CheckFailed(release_id, result["problems"])
    publish_release(release_id, client=client)
    return {"release_id": release_id, "status": "new"}


def format_result(result: dict[str, str]) -> str:
    return f"status={result['status']} release_id={result['release_id']}"

if __name__ == "__main__":
    import psycopg
    from supabase import create_client
    pipeline_root = Path(__file__).resolve().parents[2] / "2) Federal Register"
    selected = sys.argv[1] if len(sys.argv) > 1 else _latest_as_of(pipeline_root / "parsed")
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        try: print(format_result(run_fr_ingest(pipeline_root, selected, client=client, conn=conn)))
        except CheckFailed as failed: print(f"release {failed.release_id} failed check:\n{failed}", file=sys.stderr); sys.exit(1)

__all__ = ["CheckFailed", "_latest_as_of", "format_result", "run_fr_ingest"]
