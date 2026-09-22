"""Parse stored ADI and CAA Dashboard raw artifacts into deterministic JSONL."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import shutil
from pathlib import Path
from typing import Any

from adi_dashboard import parse_dashboard
from adi_documents import build_documents
from adi_entries import adi_entry_rows, dashboard_entry_rows
from adi_results import parse_results


TABLES = ("adi_source_entry", "adi_document", "adi_document_version", "adi_entry_document", "adi_page")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_raw_folder(root: Path) -> str:
    folders = [path.name for path in (root / "raw").iterdir() if path.is_dir() and (path / "run.json").exists()]
    if not folders:
        raise ValueError("no raw list folder")
    return max(folders)


def _list_input(root: Path, relative_root: str, raw_as_of: str, name: str) -> tuple[bytes, str]:
    base = root / relative_root / "raw" / raw_as_of
    run = _read_json(base / "run.json")
    sha256 = run["html_sha256"]
    return (base / sha256 / name).read_bytes(), sha256


def _manifest_files(root: Path, relative_root: str, raw_as_of: str, source_system: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for manifest in sorted((root / relative_root).glob(f"**/raw/{raw_as_of}/manifest.json")):
        base = manifest.parent
        dataset_root = base.parents[1]
        for entry in _read_json(manifest):
            if not entry.get("name", "").endswith(".pdf"):
                continue
            if source_system == "adi":
                source_key = entry["name"][:-4]
            else:
                source_key = entry.get("source_url") or entry.get("final_url")
            # 같은 파일이 두 manifest에 있으면(수집을 두 번 한 경우) 한 번만 센다.
            if (source_key, entry["sha256"]) in seen:
                continue
            seen.add((source_key, entry["sha256"]))
            files.append({
                "source_system": source_system, "source_key": source_key, "sha256": entry["sha256"],
                "path": dataset_root / entry["path"] if "path" in entry else base / entry["sha256"] / entry["name"],
            })
    return files


def parse_all(root: Path, as_of: str, *, raw_as_of: str | None = None, reader_factory=None) -> dict[str, Any]:
    root = Path(root)
    raw_as_of = raw_as_of or _latest_raw_folder(root)
    started_at = _now()
    adi_html, adi_sha = _list_input(root, "", raw_as_of, "adi-results.html")
    dash_html, dash_sha = _list_input(root, "caa_dashboard", raw_as_of, "caa-dashboard.html")
    details_path = root / "adi_details" / "raw" / raw_as_of / "details.json"
    details = _read_json(details_path) if details_path.exists() else []
    details_by_key = {row["control_number"]: row for row in details}
    entries = adi_entry_rows(parse_results(adi_html)["rows"], details_by_key, adi_sha)
    entries.extend(dashboard_entry_rows(parse_dashboard(dash_html), dash_sha))

    files = _manifest_files(root, "adi_letters", raw_as_of, "adi")
    dashboard_files = _manifest_files(root, "dashboard_letters", raw_as_of, "caa_dashboard")
    dashboard_by_url = {entry["canonical_url"]: entry["source_key"] for entry in entries if entry["source_system"] == "caa_dashboard" and entry["canonical_url"]}
    for file in dashboard_files:
        if file["source_key"] in dashboard_by_url:
            file["source_key"] = dashboard_by_url[file["source_key"]]
    files.extend(file for file in dashboard_files if file["source_key"] in dashboard_by_url.values())
    entry_by_key = {(entry["source_system"], entry["source_key"]): entry for entry in entries}
    for file in files:
        file["letter_date_raw"] = entry_by_key[(file["source_system"], file["source_key"])].get("letter_date_raw")
    documents = build_documents(files, reader_factory=reader_factory)
    held = documents.pop("held")
    linked = {(row["source_system"], row["source_key"]) for row in documents["adi_entry_document"]}
    held_keys = {(row["source_system"], row["source_key"]) for row in held}
    for entry in entries:
        key = (entry["source_system"], entry["source_key"])
        entry["text_status"] = "ok" if key in linked else ("text_failed" if key in held_keys else "text_missing")

    rows: dict[str, list[dict[str, Any]]] = {"adi_source_entry": entries, **documents}
    for table in TABLES:
        rows[table].sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
    out = root / "parsed" / as_of
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for table in TABLES:
        (out / f"{table}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows[table]), encoding="utf-8")
    report = {
        "as_of": as_of, "raw_as_of": raw_as_of, "status": "succeeded", "entries": len(entries),
        "succeeded": len(entries) - len(held), "held": held, "files": len(files),
        "details_missing": len([entry for entry in entries if entry["source_system"] == "adi" and entry["source_key"] not in details_by_key]),
        "rows": {table: len(rows[table]) for table in TABLES}, "started_at": started_at, "finished_at": _now(),
    }
    (out / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2] / "4) ADI+CAA")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--raw-as-of")
    args = parser.parse_args(argv)
    print(json.dumps(parse_all(args.root, args.as_of, raw_as_of=args.raw_as_of), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
