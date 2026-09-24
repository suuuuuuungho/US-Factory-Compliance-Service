"""SUU-269: 데이터 계약 YAML(*.odcs.yaml)과 실제 DB 구조를 비교한다.

실행: python "[2] db/contracts/contract_check.py"   (환경 변수 SUPABASE_DB_URL 필요)
다르면 ::error:: 줄을 찍고 exit 1.
"""
import os
import sys
from pathlib import Path

import yaml

CONTRACTS = Path(__file__).resolve().parent

_COLUMNS_SQL = """
select c.relname, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
       coalesce(i.indisprimary, false)
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
left join pg_index i on i.indrelid = c.oid and i.indisprimary and a.attnum = any(i.indkey)
where n.nspname = 'public' and c.relkind = 'r'
"""


def _not_empty(quality: list | None) -> bool:
    return any(q.get("metric") == "rowCount" and q.get("mustBeGreaterThan") == 0 for q in quality or [])


def load_contracts(folder: Path) -> dict:
    """YAML 계약의 표·칸 구조를 읽는다."""
    tables = {}
    for path in sorted(Path(folder).glob("*.odcs.yaml")):
        for table in yaml.safe_load(path.read_text(encoding="utf-8"))["schema"]:
            tables[table["name"]] = {
                "columns": {p["name"]: {"type": p["physicalType"],
                                        "required": p.get("required", False),
                                        "primary_key": p.get("primaryKey", False)}
                            for p in table["properties"]},
                "not_empty": _not_empty(table.get("quality")),
            }
    return tables


def read_db(conn) -> dict:
    """DB public 스키마의 표·칸 구조와 비었는지(rows 0/1)를 읽는다."""
    from psycopg import sql

    tables = {}
    with conn.cursor() as cur:
        cur.execute(_COLUMNS_SQL)
        for table, column, type_, not_null, primary_key in cur.fetchall():
            tables.setdefault(table, {"columns": {}, "rows": 0})["columns"][column] = {
                "type": type_, "required": not_null, "primary_key": primary_key}
        for table in tables:
            cur.execute(sql.SQL("select exists(select 1 from {})").format(sql.Identifier(table)))
            tables[table]["rows"] = int(cur.fetchone()[0])
    return tables


def compare(expected: dict, actual: dict) -> list[str]:
    """계약(expected)과 DB(actual)의 차이를 사람이 읽는 글로 돌려준다."""
    errors = [f"{t}: YAML에는 있는데 DB에 없는 표" for t in sorted(expected.keys() - actual.keys())]
    errors += [f"{t}: DB에는 있는데 YAML에 없는 표" for t in sorted(actual.keys() - expected.keys())]
    for t in sorted(expected.keys() & actual.keys()):
        want, have = expected[t]["columns"], actual[t]["columns"]
        errors += [f"{t}.{c}: YAML에는 있는데 DB에 없는 칸" for c in sorted(want.keys() - have.keys())]
        errors += [f"{t}.{c}: DB에는 있는데 YAML에 없는 칸" for c in sorted(have.keys() - want.keys())]
        for c in sorted(want.keys() & have.keys()):
            diffs = [f"{k} YAML={want[c][k]} DB={have[c][k]}" for k in ("type", "required", "primary_key")
                     if want[c][k] != have[c][k]]
            if diffs:
                errors.append(f"{t}.{c}: " + ", ".join(diffs))
        if expected[t]["not_empty"] and actual[t]["rows"] == 0:
            errors.append(f"{t}: 비면 안 되는 표가 비어 있음")
    return errors


def main() -> int:
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("::error::SUPABASE_DB_URL 이 없다. GitHub Secret 또는 .env 를 확인한다")
        return 1
    import psycopg

    expected = load_contracts(CONTRACTS)
    with psycopg.connect(url) as conn:
        actual = read_db(conn)
    errors = compare(expected, actual)
    for e in errors:
        print(f"::error::{e}")
    if errors:
        return 1
    print(f"OK 표 {len(expected)}개 칸 {sum(len(t['columns']) for t in expected.values())}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
