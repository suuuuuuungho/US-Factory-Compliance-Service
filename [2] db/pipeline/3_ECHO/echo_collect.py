"""Collect, validate, and store the two ECHO ZIP downloads."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
from urllib.error import URLError

from echo_fetch import fetch_to_file
from echo_raw import store_raw
from echo_zip import ICIS_AIR_MEMBERS, PIPELINE_MEMBERS, ZipCheckError, inspect_zip


ICIS_AIR_URL = "https://echo.epa.gov/files/echodownloads/ICIS-AIR_downloads.zip"
PIPELINE_URL = "https://echo.epa.gov/files/echodownloads/pipeline_caa_downloads.zip"
DOWNLOADS = (
    (ICIS_AIR_URL, "ICIS-AIR_downloads.zip", ICIS_AIR_MEMBERS),
    (PIPELINE_URL, "pipeline_caa_downloads.zip", PIPELINE_MEMBERS),
)


def collect(
    root: Path,
    *,
    as_of: date | None = None,
    fetch_to_file=fetch_to_file,
    inspect_zip=inspect_zip,
    store_raw=store_raw,
) -> dict:
    """Fetch and validate both ZIPs before storing either one."""

    as_of = as_of or date.today()
    started_at = datetime.now(timezone.utc).isoformat()
    work = root / "work"
    checked = []
    try:
        for url, name, required in DOWNLOADS:
            fetched = fetch_to_file(url, work / name)
            members = inspect_zip(fetched.path, required=required)
            checked.append((fetched, members))
    except (ZipCheckError, ValueError, OSError, URLError) as exc:
        if work.exists():
            for path in work.glob("*.zip"):
                path.unlink(missing_ok=True)
        return {
            "status": "failed", "as_of": as_of.isoformat(),
            "reason": f"{name}: {exc}", "zips": [], "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    summaries = []
    for fetched, members in checked:
        store_raw(root, as_of, fetched, members)
        summaries.append({
            "name": fetched.path.name, "sha256": fetched.sha256,
            "byte_size": fetched.byte_size, "member_count": len(members),
            "row_count": sum(m.row_count for m in members if m.row_count is not None),
        })
    return {
        "status": "succeeded", "as_of": as_of.isoformat(), "reason": None,
        "zips": summaries, "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the ECHO collector and print its JSON summary."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2] / "3) ECHO")
    args = parser.parse_args(argv)
    run = collect(Path(args.root))
    print(json.dumps(run, indent=2, ensure_ascii=False))
    return 0 if run["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
