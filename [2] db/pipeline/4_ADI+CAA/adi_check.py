"""Validate an ADI release after loading it."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adi_load import TABLES


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_release(root: Path, as_of: str, release_id: str, *, conn: Any) -> dict:
    parsed = Path(root) / "parsed" / as_of
    rows = {table: _rows(parsed / f"{table}.jsonl") for table in TABLES}
    versions = [row["version_id"] for row in rows["adi_document_version"]]
    documents = [row["document_id"] for row in rows["adi_document"]]
    counts, problems = {}, []
    keys = {"adi_document": ("document_id", documents), "adi_document_relation": ("from_document_id", documents),
            "adi_facility_candidate": ("document_id", documents)}
    with conn.cursor() as cur:
        for table in TABLES:
            if table in {"adi_source_entry", "adi_entry_document"}:
                cur.execute(f"select count(*) from {table} where release_id = %s", (release_id,))
            else:
                column, values = keys.get(table, ("version_id", versions))
                cur.execute(f"select count(*) from {table} where {column} = any(%s)", (values,))
            counts[table] = cur.fetchone()[0]
            if counts[table] != len(rows[table]):
                problems.append(f"{table}: db {counts[table]} != jsonl {len(rows[table])}")
        checks = (
            ("adi_entry_document", "version_id", "select count(*) from adi_entry_document c left join adi_document_version p using (version_id) where c.release_id = %s and p.version_id is null", (release_id,)),
            ("adi_page", "version_id", "select count(*) from adi_page c left join adi_document_version p using (version_id) where c.version_id = any(%s) and p.version_id is null", (versions,)),
            ("adi_cfr_reference", "current_node_key", "select count(*) from adi_cfr_reference c left join ecfr_node n on n.release_id = c.current_ecfr_release_id and n.node_key = c.current_node_key where c.version_id = any(%s) and c.current_node_key is not null and n.node_key is null", (versions,)),
        )
        for child, column, sql, params in checks:
            cur.execute(sql, params)
            if (count := cur.fetchone()[0]):
                problems.append(f"orphan {child}.{column}: {count}")
    return {"ok": not problems, "problems": problems, "counts": counts}


__all__ = ["check_release"]
