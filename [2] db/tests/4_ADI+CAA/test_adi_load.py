"""SUU-224: parsed/{as_of}/ jsonl 9개를 adi_* 표에 COPY 로 넣는다.

실제 Postgres 없음. psycopg 3 모양의 가짜 conn (fr_load 테스트 방식).
release_id 열이 있는 표(adi_source_entry·adi_entry_document)는 release_id 로, 없는 표는 jsonl 에 든 키 목록
(version_id / document_id, `= any(%s)`)으로 지우고 다시 넣는다 — 같은 파일은 어느 release 에서도 같은 version_id 라서
지우고 다시 넣으면 곧 갱신이다. 원본 연결은 sha256 → common_raw_object.object_id.
현재 eCFR·ECHO release 는 common_dataset_current 에서 읽어 current_ecfr_release_id·echo_release_id 를 채운다.
"""
from __future__ import annotations

import json
import re
import uuid

import pytest

from adi_load import TABLES, load_release

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
ECFR_RELEASE = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
ECHO_RELEASE = "0e0e0e0e-0e0e-4e0e-8e0e-0e0e0e0e0e0e"
RELEASE_TABLES = ("adi_source_entry", "adi_entry_document")
LINES = {"adi_source_entry": 275, "adi_document": 2, "adi_document_version": 2, "adi_entry_document": 3, "adi_page": 7,
         "adi_block": 6, "adi_cfr_reference": 4, "adi_document_relation": 1, "adi_facility_candidate": 1}


class _Copy:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write_row(self, row):
        self.sink.append(tuple(row))


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._pending = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        text = " ".join(sql.split())
        self.conn.executed.append((text, params))
        low = text.lower()
        if low.startswith("delete from"):
            m = re.match(r"delete from (\w+) where (\w+) = (%s|any\(%s\))$", low)
            assert m, sql
            table, column, form = m.groups()
            keys = set(params[0]) if form.startswith("any") else {params[0]}
            assert (column == "release_id") == (form == "%s"), sql
            if table in self.conn.tables:
                index = self.conn.columns[table].index(column)
                self.conn.tables[table] = [r for r in self.conn.tables[table] if r[index] not in keys]
        elif "common_raw_object" in low:
            assert params == (RELEASE_ID,)
            self._pending = list(self.conn.objects.items())  # (object_id, sha256)
        elif "common_dataset_current" in low:
            self._pending = list(self.conn.current.items())  # (dataset, release_id)
        return self

    def fetchall(self):
        rows, self._pending = self._pending, []
        return rows

    def copy(self, sql):
        m = re.match(r"\s*copy\s+(\w+)\s*\(([^)]*)\)\s+from\s+stdin", sql, re.I | re.S)
        assert m, sql
        table, columns = m.group(1), tuple(c.strip() for c in m.group(2).split(","))
        self.conn.columns[table] = columns
        return _Copy(self.conn.tables.setdefault(table, []))


class FakeConn:
    def __init__(self, objects, current):
        self.objects = objects  # object_id → sha256 (이 release 의 common_release_object)
        self.current = current  # dataset → release_id (common_dataset_current)
        self.tables: dict[str, list[tuple]] = {}
        self.columns: dict[str, tuple[str, ...]] = {}
        self.executed: list = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def _conn_for(adi, current=None):
    """adi_release 가 등록했을 원본 6개에 object_id 를 붙인다."""
    objects = {str(uuid.uuid4()): sha for _, sha in adi.objects.values()}
    return FakeConn(objects, {"ecfr": ECFR_RELEASE, "echo": ECHO_RELEASE} if current is None else current)


def _rows(conn, table):
    return [dict(zip(conn.columns[table], r)) for r in conn.tables[table]]


def test_copies_every_jsonl_row_of_nine_tables_parents_first(adi):
    conn = _conn_for(adi)

    counts = load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    assert TABLES == adi.tables
    assert {t: len(adi.rows(t)) for t in TABLES} == LINES
    assert counts == LINES
    assert {t: len(r) for t, r in conn.tables.items()} == LINES
    assert list(conn.tables)[:4] == ["adi_source_entry", "adi_document", "adi_document_version", "adi_entry_document"]  # 부모 먼저
    for table in RELEASE_TABLES:
        assert conn.columns[table][0] == "release_id" and all(r[0] == RELEASE_ID for r in conn.tables[table]), table
    for table in set(TABLES) - set(RELEASE_TABLES):
        assert "release_id" not in conn.columns[table], table
    assert conn.commits >= 1


def test_entries_and_versions_link_raw_objects_by_sha256(adi):
    conn = _conn_for(adi)
    ids_by_sha: dict[str, set] = {}
    for oid, sha in conn.objects.items():
        ids_by_sha.setdefault(sha, set()).add(oid)

    load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    entries = {(e["source_system"], e["source_key"]): e for e in _rows(conn, "adi_source_entry")}
    assert "text_status" not in conn.columns["adi_source_entry"]  # jsonl 에만 있는 키. 표에는 없다
    assert entries[("adi", "1800013")]["source_object_id"] in ids_by_sha[adi.objects["adi_list"][1]]
    assert entries[("adi", "1800038")]["source_object_id"] in ids_by_sha[adi.objects["adi_list"][1]]  # PDF 없는 항목도 목록 원본은 있다
    dashboard = next(e for e in entries.values() if e["source_system"] == "caa_dashboard")
    assert dashboard["source_object_id"] in ids_by_sha[adi.objects["dashboard_list"][1]]
    assert json.loads(entries[("adi", "1800013")]["categories"]) == ["MACT", "NSPS"]  # jsonb: JSON 문자열
    assert entries[("adi", "1800013")]["control_number"] == "1800013" and dashboard["control_number"] is None

    versions = {v["sha256"]: v for v in _rows(conn, "adi_document_version")}
    assert versions[adi.objects["M170010"][1]]["object_id"] in ids_by_sha[adi.objects["M170010"][1]]
    assert versions[adi.objects["1800013"][1]]["object_id"] in ids_by_sha[adi.objects["1800013"][1]]  # 공유 파일: 둘 중 하나
    assert versions[adi.objects["M170010"][1]]["signed_on"] is None and versions[adi.objects["M170010"][1]]["signed_on_raw"] == "11/12/2015"


def test_current_ecfr_and_echo_releases_fill_the_composite_fk_columns(adi):
    conn = _conn_for(adi)

    load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    refs = {r["raw_citation"]: r for r in _rows(conn, "adi_cfr_reference")}
    assert refs["40 CFR 63.2"]["current_node_key"] == "40/63/subpart-A/section-63.2"
    assert refs["40 CFR 63.2"]["current_ecfr_release_id"] == ECFR_RELEASE
    assert refs["40 CFR 63.9999"]["current_node_key"] is None and refs["40 CFR 63.9999"]["current_ecfr_release_id"] is None
    assert refs["40 CFR 60.4200"]["current_ecfr_release_id"] is None
    assert all(r["historical_ecfr_release_id"] is None and r["historical_node_key"] is None for r in refs.values())
    assert refs["40 CFR 63.2"]["title"] == 40 and refs["40 CFR 63.2"]["review_status"] == "검토 전"

    candidates = _rows(conn, "adi_facility_candidate")
    assert [(c["echo_release_id"], c["echo_pgm_sys_id"]) for c in candidates] == [(ECHO_RELEASE, "IN0000123")]
    assert candidates[0]["document_id"] == adi.rows("adi_facility_candidate")[0]["document_id"]


def test_missing_current_ecfr_or_echo_release_raises_instead_of_loading_half(adi):
    """common_dataset_current 에 ecfr·echo 가 없으면 복합 FK 를 채울 수 없다. 조용히 NULL 로 넣지 않는다."""
    conn = _conn_for(adi, current={"ecfr": ECFR_RELEASE})

    with pytest.raises(LookupError, match="echo"):
        load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    assert conn.commits == 0


def test_loading_the_same_release_twice_does_not_grow_any_table(adi):
    conn = _conn_for(adi)

    load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)
    first = {t: len(r) for t, r in conn.tables.items()}
    load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    assert {t: len(r) for t, r in conn.tables.items()} == first == LINES
    deletes = [re.match(r"delete from (\w+)", s.lower()).group(1) for s, _ in conn.executed if s.lower().startswith("delete from")]
    assert set(deletes) == set(TABLES)
    first_run = deletes[: len(TABLES)]
    # 자식을 먼저, 부모를 나중에 지운다
    assert first_run.index("adi_document") > first_run.index("adi_document_version") > max(first_run.index(t) for t in ("adi_page", "adi_block", "adi_cfr_reference", "adi_entry_document"))
    assert first_run.index("adi_cfr_reference") < first_run.index("adi_block")
    assert first_run.index("adi_document_relation") < first_run.index("adi_document") and first_run.index("adi_facility_candidate") < first_run.index("adi_document")
    assert first_run.index("adi_entry_document") < first_run.index("adi_source_entry")


def test_session_drops_statement_timeout_and_fk_triggers_before_any_write(adi):
    """SUU-127 교훈: pooler 기본 2분 제한과 행마다 FK 검사를 끄고 시작한다. 고아 FK 는 adi_check 가 본다."""
    conn = _conn_for(adi)

    load_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    statements = [s.lower() for s, _ in conn.executed]
    assert "set statement_timeout = 0" in statements
    assert "set session_replication_role = replica" in statements
    first_write = next(i for i, s in enumerate(statements) if s.startswith("delete from"))
    assert statements.index("set statement_timeout = 0") < first_write
    assert statements.index("set session_replication_role = replica") < first_write
