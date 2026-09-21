"""Check a loaded Federal Register release."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fr_parse import TABLES

CHILDREN = ("fr_identifier", "fr_cfr_reference", "fr_date_event")

def _expected(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

def check_release(root: Path, as_of: str, release_id: str, *, conn: Any) -> dict:
    parsed, problems, counts = Path(root) / "parsed" / as_of, [], {}
    with conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"select count(*) from {table} where release_id = %s", (release_id,)); counts[table] = cur.fetchone()[0]
            expected = _expected(parsed / f"{table}.jsonl")
            if counts[table] != expected: problems.append(f"{table}: db {counts[table]} != jsonl {expected}")
        for child in CHILDREN:
            cur.execute(f"select count(*) from {child} c left join fr_document p on p.release_id = c.release_id and p.document_key = c.document_key where c.release_id = %s and p.document_key is null", (release_id,))
            if (n := cur.fetchone()[0]): problems.append(f"orphan {child}.document_key: {n}")
        cur.execute("select count(*) from fr_document where release_id = %s and source_object_id is null", (release_id,))
        if (n := cur.fetchone()[0]): problems.append(f"fr_document source_object_id is null: {n}")
    report = json.loads((parsed / "quality_report.json").read_text(encoding="utf-8"))
    for table, count in counts.items():
        # A row-count mismatch already names the table; avoid reporting the same
        # broken load a second time through its quality report.
        if count == _expected(parsed / f"{table}.jsonl") and (expected := report.get("rows", {}).get(table)) != count:
            problems.append(f"quality_report {table}: report {expected} != db {count}")
    return {"ok": not problems, "problems": problems, "counts": counts}

__all__ = ["check_release"]
