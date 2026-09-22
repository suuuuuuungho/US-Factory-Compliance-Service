"""COPY a parsed ADI release into its database tables."""
from __future__ import annotations

import json
from itertools import chain
from pathlib import Path
from typing import Any

from adi_enrich import TABLES as ENRICH_TABLES
from adi_parse import TABLES as PARSE_TABLES

TABLES = PARSE_TABLES + ENRICH_TABLES
RELEASE_TABLES = {"adi_source_entry", "adi_entry_document"}
JSONB_COLUMNS = {"categories"}
# jsonl에 None으로 들어 있지만 적재기가 채우는 열. jsonl 키로는 넣지 않고 아래에서 덧붙인다.
REFERENCE_LINK_COLUMNS = ("historical_ecfr_release_id", "historical_node_key", "current_ecfr_release_id", "current_node_key")


def _jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _value(column: str, value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if column in JSONB_COLUMNS and value is not None else value


def _delete_existing(cur, release_id: str, versions: list[str], documents: list[str]) -> None:
    for table, column, values in (
        ("adi_facility_candidate", "document_id", documents),
        ("adi_document_relation", "from_document_id", documents),
        ("adi_cfr_reference", "version_id", versions),
        ("adi_block", "version_id", versions),
        ("adi_page", "version_id", versions),
        ("adi_entry_document", "release_id", release_id),
        ("adi_document_version", "version_id", versions),
        ("adi_document", "document_id", documents),
        ("adi_source_entry", "release_id", release_id),
    ):
        if column == "release_id":
            cur.execute(f"delete from {table} where {column} = %s", (values,))
        else:
            cur.execute(f"delete from {table} where {column} = any(%s)", (values,))


def load_release(root: Path, as_of: str, release_id: str, *, conn: Any) -> dict[str, int]:
    parsed = Path(root) / "parsed" / as_of
    rows_by_table = {table: list(_jsonl(parsed / f"{table}.jsonl")) for table in TABLES}
    versions = [row["version_id"] for row in rows_by_table["adi_document_version"]]
    documents = [row["document_id"] for row in rows_by_table["adi_document"]]
    with conn.cursor() as cur:
        cur.execute("select dataset, release_id from common_dataset_current where dataset in ('ecfr', 'echo')")
        current = dict(cur.fetchall())
        for dataset in ("ecfr", "echo"):
            if dataset not in current:
                raise LookupError(f"common_dataset_current has no {dataset} release")
        cur.execute("set statement_timeout = 0")
        cur.execute("set session_replication_role = replica")
        _delete_existing(cur, release_id, versions, documents)
        cur.execute("select o.object_id, o.sha256 from common_raw_object o join common_release_object r using (object_id) where r.release_id = %s order by o.sha256, o.source_url", (release_id,))
        objects = {}
        for object_id, sha256 in cur.fetchall():
            objects.setdefault(sha256, str(object_id))
        counts = {}
        for table in TABLES:
            rows = rows_by_table[table]
            counts[table] = len(rows)
            if not rows:
                continue
            keys = tuple(key for key in rows[0] if not (table == "adi_source_entry" and key == "text_status")
                         and not (table == "adi_cfr_reference" and key in REFERENCE_LINK_COLUMNS))
            columns = (("release_id",) if table in RELEASE_TABLES else ()) + keys
            if table == "adi_source_entry": columns += ("source_object_id",)
            elif table == "adi_document_version": columns += ("object_id",)
            elif table == "adi_cfr_reference": columns += REFERENCE_LINK_COLUMNS
            elif table == "adi_facility_candidate": columns += ("echo_release_id",)
            with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
                for row in rows:
                    values = [release_id] if table in RELEASE_TABLES else []
                    values.extend(_value(key, row.get(key)) for key in keys)
                    if table == "adi_source_entry": values.append(objects.get(row["list_sha256"]))
                    elif table == "adi_document_version": values.append(objects.get(row["sha256"]))
                    elif table == "adi_cfr_reference":
                        values.extend((None, None, current["ecfr"] if row.get("current_node_key") else None, row.get("current_node_key")))
                    elif table == "adi_facility_candidate": values.append(current["echo"])
                    copy.write_row(values)
    conn.commit()
    return counts


__all__ = ["TABLES", "load_release"]
