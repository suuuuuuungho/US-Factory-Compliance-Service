"""Load parsed ECHO jsonl files into the echo_* tables with COPY FROM STDIN."""

from __future__ import annotations

import json
from itertools import chain
from pathlib import Path
from typing import Any

from echo_parse import TABLES

JSONB_COLUMNS = {"raw_payload", "raw_dates", "attributes", "programs", "pollutants", "flags"}
CODE_MAP_COLUMNS = (
    "dictionary_version", "program_code", "raw_subpart_code", "raw_description",
    "cfr_title", "cfr_part", "cfr_subpart", "source_url", "review_status",
)


def _iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _value(column: str, value: Any) -> Any:
    if value is None:
        return None
    if column in JSONB_COLUMNS:
        return json.dumps(value, ensure_ascii=False)
    return value


def _source_objects(cur, release_id: str) -> dict[str, str]:
    cur.execute(
        "select o.object_id, o.sha256 from common_raw_object o"
        " join common_release_object r using (object_id) where r.release_id = %s",
        (release_id,),
    )
    return {sha256: str(object_id) for object_id, sha256 in cur.fetchall()}


def _rows(table: str, path: Path, objects: dict[str, str]):
    """Yield (columns, values) for one table; columns come from the first row's keys."""
    for row in _iter_jsonl(path):
        if table == "echo_source_row":
            if row["parse_status"] != "held":
                continue  # 정상 행은 ZIP + source_row_no로 되짚는다
            sha256 = row.pop("source_object_sha256")
            row["source_object_id"] = objects.get(sha256)
        yield row


def load_release(root: Path, as_of: str, release_id: str, code_map_version: str, *, conn: Any) -> dict[str, int]:
    """Replace the echo_* rows of ``release_id`` with the parsed files of ``as_of``."""

    root = Path(root)
    parsed = root / "parsed" / as_of
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in reversed(TABLES):  # 자식 표부터 지운다 (FK)
            cur.execute(f"delete from {table} where release_id = %s", (release_id,))
        objects = _source_objects(cur, release_id)
        for table in TABLES:
            counts[table] = 0
            rows = _rows(table, parsed / f"{table}.jsonl", objects)
            first = next(rows, None)
            if first is None:
                continue
            columns = ("release_id", *first)  # 열 = jsonl 키 순서
            with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
                for row in chain([first], rows):
                    copy.write_row((release_id, *(_value(column, row[column]) for column in columns[1:])))
                    counts[table] += 1

        counts["echo_code_map"] = 0
        placeholders = ", ".join(["%s"] * len(CODE_MAP_COLUMNS))
        for row in _iter_jsonl(root / "code_map" / code_map_version / "echo_code_map.jsonl"):
            row["cfr_title"] = int(row["cfr_title"]) if row.get("cfr_title") not in (None, "") else None
            cur.execute(
                f"insert into echo_code_map ({', '.join(CODE_MAP_COLUMNS)}) values ({placeholders}) on conflict do nothing",
                tuple(row.get(column) for column in CODE_MAP_COLUMNS),
            )
            counts["echo_code_map"] += 1
    conn.commit()
    return counts


__all__ = ["load_release"]
