"""Parse stored Federal Register detail JSON into deterministic JSONL artifacts."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import shutil
from pathlib import Path
from typing import Any

from fr_documents import document_key, document_row, identifier_rows
from fr_references import cfr_reference_rows, date_event_rows


TABLES = ("fr_document", "fr_identifier", "fr_cfr_reference", "fr_date_event")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _folder_identity(folder: Path) -> tuple[str, str]:
    publication_date, document_number = folder.name.split("_", 1)
    return publication_date, document_number


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def parse_all(root: Path, as_of: str) -> dict[str, Any]:
    """Parse every stored document folder and retain unusable inputs as held."""

    root = Path(root)
    started_at = _now()
    raw = root / "raw"
    documents: list[tuple[str, str, Path]] = []
    if raw.exists():
        for year in sorted(raw.iterdir(), key=lambda path: path.name):
            if not year.is_dir() or year.name == "lists":
                continue
            for folder in sorted(year.iterdir(), key=lambda path: path.name):
                if folder.is_dir() and "_" in folder.name:
                    publication_date, document_number = _folder_identity(folder)
                    documents.append((publication_date, document_number, folder))
    documents.sort(key=lambda item: document_key(item[0], item[1]))

    rows: dict[str, list[dict[str, Any]]] = {table: [] for table in TABLES}
    held: list[dict[str, str]] = []
    succeeded = 0
    for publication_date, document_number, folder in documents:
        try:
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            detail_entry = next(
                (entry for entry in reversed(manifest) if entry.get("kind") == "detail"),
                None,
            )
            if detail_entry is None:
                raise ValueError("no detail")
            detail = json.loads((root / detail_entry["path"]).read_text(encoding="utf-8"))
            for field in ("document_number", "publication_date", "html_url"):
                if not detail.get(field):
                    raise ValueError(f"missing field: {field}")
            key = document_key(detail["publication_date"], detail["document_number"])
            rows["fr_document"].append(document_row(detail, manifest))
            rows["fr_identifier"].extend(identifier_rows(key, detail))
            rows["fr_cfr_reference"].extend(cfr_reference_rows(key, detail))
            rows["fr_date_event"].extend(date_event_rows(key, detail))
            succeeded += 1
        except json.JSONDecodeError as exc:
            held.append({"publication_date": publication_date, "document_number": document_number, "reason": f"broken json: {exc}"})
        except ValueError as exc:
            held.append({"publication_date": publication_date, "document_number": document_number, "reason": str(exc)})
        except (KeyError, OSError) as exc:
            held.append({"publication_date": publication_date, "document_number": document_number, "reason": str(exc)})

    for table in TABLES:
        rows[table].sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
    out = root / "parsed" / as_of
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for table in TABLES:
        _write_jsonl(out / f"{table}.jsonl", rows[table])
    report: dict[str, Any] = {
        "as_of": as_of,
        "status": "succeeded",
        "documents": len(documents),
        "succeeded": succeeded,
        "held": held,
        "rows": {table: len(rows[table]) for table in TABLES},
        "started_at": started_at,
        "finished_at": _now(),
    }
    (out / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2] / "2) Federal Register")
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args(argv)
    report = parse_all(args.root, args.as_of)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
