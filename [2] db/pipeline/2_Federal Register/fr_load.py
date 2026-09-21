"""COPY parsed Federal Register rows into a release."""

from __future__ import annotations

import json
from itertools import chain
from pathlib import Path
from typing import Any
from uuid import uuid4

from fr_parse import TABLES

JSONB_COLUMNS = {"agencies", "docket_ids", "regulation_id_numbers", "raw_metadata"}
CHILDREN = ("fr_identifier", "fr_cfr_reference", "fr_date_event")


def _jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _objects(cur, release_id: str) -> dict[str, str]:
    cur.execute("select o.object_id, o.sha256 from common_raw_object o join common_release_object r using (object_id) where r.release_id = %s", (release_id,))
    return {sha: str(object_id) for object_id, sha in cur.fetchall()}


def _manifest_objects(root: Path) -> dict[str, tuple[str | None, str | None]]:
    result = {}
    for year in (root / "raw").iterdir():
        if not year.is_dir() or year.name == "lists": continue
        for folder in year.iterdir():
            manifest = folder / "manifest.json"
            if manifest.exists():
                entries = json.loads(manifest.read_text(encoding="utf-8"))
                result[folder.name.replace("_", "/", 1)] = (
                    next((e["sha256"] for e in reversed(entries) if e.get("kind") == "xml"), None),
                    next((e["sha256"] for e in reversed(entries) if e.get("kind") == "pdf"), None))
    return result


def _value(column: str, value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if value is not None and column in JSONB_COLUMNS else value


def load_release(root: Path, as_of: str, release_id: str, *, conn: Any) -> dict[str, int]:
    root, parsed = Path(root), Path(root) / "parsed" / as_of
    counts = {}
    with conn.cursor() as cur:
        cur.execute("set statement_timeout = 0")
        cur.execute("set session_replication_role = replica")
        for table in (*CHILDREN, "fr_document"):
            cur.execute(f"delete from {table} where release_id = %s", (release_id,))
        objects, manifests = _objects(cur, release_id), _manifest_objects(root)
        for table in TABLES:
            rows = _jsonl(parsed / f"{table}.jsonl")
            first = next(rows, None)
            counts[table] = 0
            if first is None: continue
            row_keys = tuple(first)
            columns = ("release_id", *( ("reference_id",) if table == "fr_cfr_reference" else ("event_id",) if table == "fr_date_event" else ()), *row_keys,
                       *(("source_object_id", "body_object_id", "pdf_object_id") if table == "fr_document" else ()))
            with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
                for row in chain([first], rows):
                    extra = []
                    if table == "fr_document":
                        xml, pdf = manifests.get(row["document_key"], (None, None))
                        row = {**row, "source_object_id": objects.get(row["content_hash"]), "body_object_id": objects.get(xml), "pdf_object_id": objects.get(pdf)}
                    if table == "fr_cfr_reference": extra = [str(uuid4())]
                    if table == "fr_date_event": extra = [str(uuid4())]
                    copy.write_row((release_id, *extra, *(_value(c, row.get(c)) for c in row_keys), *( [row["source_object_id"], row["body_object_id"], row["pdf_object_id"]] if table == "fr_document" else [])))
                    counts[table] += 1
    conn.commit()
    return counts


__all__ = ["load_release"]
