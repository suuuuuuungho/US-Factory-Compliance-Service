"""Verify a loaded ECHO release against its jsonl, report.json and manifest before publishing."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from echo_parse import ORPHANS, TABLES

# 관계 이름 → (자식 표, 부모 표, join 조건, 부모 키 열). 부모 키가 NULL이면 고아.
_RELATIONS = {
    "echo_industry.pgm_sys_id": ("echo_industry", "echo_facility", "c.pgm_sys_id = p.pgm_sys_id", "pgm_sys_id"),
    "echo_program.pgm_sys_id": ("echo_program", "echo_facility", "c.pgm_sys_id = p.pgm_sys_id", "pgm_sys_id"),
    "echo_program_subpart.program": ("echo_program_subpart", "echo_program", "c.pgm_sys_id = p.pgm_sys_id and c.program_code = p.program_code", "pgm_sys_id"),
    "echo_pollutant.pgm_sys_id": ("echo_pollutant", "echo_facility", "c.pgm_sys_id = p.pgm_sys_id", "pgm_sys_id"),
    "echo_activity_facility.pgm_sys_id": ("echo_activity_facility", "echo_facility", "c.pgm_sys_id = p.pgm_sys_id", "pgm_sys_id"),
    "echo_activity_facility.activity": ("echo_activity_facility", "echo_activity", "c.activity_kind = p.activity_kind and c.activity_id = p.activity_id", "activity_id"),
    "echo_violation_facility.pgm_sys_id": ("echo_violation_facility", "echo_facility", "c.pgm_sys_id = p.pgm_sys_id", "pgm_sys_id"),
    "echo_violation_facility.violation": ("echo_violation_facility", "echo_violation", "c.violation_id = p.violation_id", "violation_id"),
    "echo_penalty.activity": ("echo_penalty", "echo_activity", "c.activity_kind = p.activity_kind and c.activity_id = p.activity_id", "activity_id"),
    "echo_pipeline_link.resolved": ("echo_pipeline_link", "echo_activity", "c.resolved_eval_kind = p.activity_kind and c.resolved_eval_id = p.activity_id", "activity_id"),
}


def _jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _one(cur, sql: str, release_id: str):
    cur.execute(sql, (release_id,))
    return cur.fetchone()[0]


def check_release(root: Path, as_of: str, release_id: str, *, conn: Any) -> dict:
    root = Path(root)
    parsed = root / "parsed" / as_of
    problems: list[str] = []
    counts: dict[str, Any] = {}

    with conn.cursor() as cur:
        for table in TABLES:
            rows = _jsonl(parsed / f"{table}.jsonl")
            expected = sum(1 for r in rows if table != "echo_source_row" or r["parse_status"] == "held")
            counts[table] = _one(cur, f"select count(*) from {table} where release_id = %s", release_id)
            if counts[table] != expected:
                problems.append(f"{table}: db {counts[table]} != jsonl {expected}")

        for name in ORPHANS:
            child, parent, on, key = _RELATIONS[name]
            orphans = _one(
                cur,
                f"select count(*) from {child} c left join {parent} p on p.release_id = c.release_id and {on}"
                f" where c.release_id = %s and p.{key} is null"
                + (" and c.resolved_eval_id is not null" if name == "echo_pipeline_link.resolved" else ""),
                release_id,
            )
            if orphans:
                problems.append(f"orphan {name}: {orphans}")

        db_sum = _one(cur, "select sum(amount) from echo_penalty where release_id = %s", release_id) or Decimal(0)
        jsonl_sum = sum((Decimal(r["amount"]) for r in _jsonl(parsed / "echo_penalty.jsonl") if r["amount"] is not None), Decimal(0))
        counts["penalty_sum"] = str(db_sum)
        if Decimal(db_sum) != jsonl_sum:
            problems.append(f"echo_penalty sum: db {db_sum} != jsonl {jsonl_sum}")

        broken = _one(
            cur,
            "select count(*) from echo_pipeline_link where release_id = %s and"
            " ((resolved_eval_kind is null) != (resolved_eval_id is null) or (resolved_ea_kind is null) != (resolved_ea_id is null))",
            release_id,
        )
        if broken:
            problems.append(f"echo_pipeline_link broken pairs: {broken}")

    report = json.loads((parsed / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "raw" / as_of / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        for member in entry["members"]:
            read = report["files"].get(member["name"], {}).get("read")
            if read != member["row_count"]:
                problems.append(f"{member['name']}: report {read} != manifest {member['row_count']}")

    return {"ok": not problems, "problems": problems, "counts": counts}


__all__ = ["check_release"]
