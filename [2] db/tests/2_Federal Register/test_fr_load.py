"""SUU-209: parsed/{as_of}/ jsonl 4개를 release_id 를 붙여 fr_* 표에 COPY 로 넣는다.

실제 Postgres 없음. psycopg 3 모양의 가짜 conn (SUU-123 방식). 원본 연결(source/body/pdf_object_id)은
common_raw_object 의 sha256 → object_id 로 잇는다. uuid PK(reference_id·event_id)는 적재 때 만든다.
"""
import json
import re
import uuid

from fr_load import load_release

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
TABLES = ["fr_document", "fr_identifier", "fr_cfr_reference", "fr_date_event"]


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
            table = re.match(r"delete from (\w+)", low).group(1)
            if table in self.conn.tables:
                self.conn.tables[table] = [r for r in self.conn.tables[table] if r[0] != params[0]]
        if "common_raw_object" in low:
            assert params == (RELEASE_ID,)
            self._pending = list(self.conn.objects.items())  # (object_id, sha256)
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
    def __init__(self, objects):
        self.objects = objects  # object_id → sha256 (이 release 의 common_release_object)
        self.tables: dict[str, list[tuple]] = {}
        self.columns: dict[str, tuple[str, ...]] = {}
        self.executed: list = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def _conn_for(fr):
    """fr_release 가 등록했을 원본 8개에 object_id 를 붙인다."""
    objects = {}
    for kinds in fr.objects.values():
        for _, sha in kinds.values():
            objects[str(uuid.uuid4())] = sha
    return FakeConn(objects)


def _rows(conn, table):
    return [dict(zip(conn.columns[table], r)) for r in conn.tables[table]]


def test_copies_every_jsonl_row_with_release_id_and_makes_uuid_keys(fr):
    conn = _conn_for(fr)

    counts = load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    expected = {t: len(fr.rows(t)) for t in TABLES}
    assert expected == {"fr_document": 3, "fr_identifier": 4, "fr_cfr_reference": 3, "fr_date_event": 2}
    assert counts == expected
    assert {t: len(r) for t, r in conn.tables.items()} == expected
    for table in TABLES:
        assert conn.columns[table][0] == "release_id" and all(r[0] == RELEASE_ID for r in conn.tables[table]), table
    assert list(conn.tables)[0] == "fr_document"  # 부모 표를 먼저 COPY

    refs = _rows(conn, "fr_cfr_reference")
    events = _rows(conn, "fr_date_event")
    assert len({uuid.UUID(r["reference_id"]) for r in refs}) == 3
    assert len({uuid.UUID(e["event_id"]) for e in events}) == 2
    assert conn.commits >= 1


def test_document_rows_link_source_body_pdf_objects_by_sha256(fr):
    conn = _conn_for(fr)
    by_sha = {sha: oid for oid, sha in conn.objects.items()}

    load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    docs = {d["document_key"]: d for d in _rows(conn, "fr_document")}
    rule = docs["2026-02-24/2026-03638"]
    kinds = fr.objects[("2026-02-24", "2026-03638")]
    assert rule["source_object_id"] == by_sha[kinds["detail"][1]]
    assert rule["body_object_id"] == by_sha[kinds["xml"][1]]
    assert rule["pdf_object_id"] == by_sha[kinds["pdf"][1]]
    assert rule["content_hash"] == kinds["detail"][1]

    correction = docs["2003-08-28/03-5521"]  # XML 없이 PDF 만
    assert correction["body_object_id"] is None
    assert correction["pdf_object_id"] == by_sha[fr.objects[("2003-08-28", "03-5521")]["pdf"][1]]
    assert correction["body_status"] == "pdf_only"


def test_values_are_copied_in_the_text_form_postgres_needs(fr):
    conn = _conn_for(fr)

    load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    docs = {d["document_key"]: d for d in _rows(conn, "fr_document")}
    rule = docs["2026-02-24/2026-03638"]
    assert rule["publication_date"] == "2026-02-24" and rule["effective_on"] == "2026-04-27"  # date: ISO 문자열
    assert rule["volume"] == 91  # integer
    assert rule["subtype"] is None  # NULL
    assert json.loads(rule["agencies"])[0]["name"] == "Environmental Protection Agency"  # jsonb: JSON 문자열
    assert json.loads(rule["docket_ids"]) == ["EPA-HQ-OAR-2018-0794", "FRL-6716.4-02-OAR"]
    assert json.loads(rule["raw_metadata"])["document_number"] == "2026-03638"
    assert docs["2003-08-28/03-5521"]["effective_on"] is None

    ref = _rows(conn, "fr_cfr_reference")[0]
    assert ref["title"] == 40 and ref["part"] == "63" and ref["subpart"] is None
    assert ref["review_status"] == "검토 전"


def test_loading_the_same_release_twice_does_not_grow_any_table(fr):
    conn = _conn_for(fr)

    load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)
    first = {t: len(r) for t, r in conn.tables.items()}
    load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert {t: len(r) for t, r in conn.tables.items()} == first
    deletes = [re.match(r"delete from (\w+)", s.lower()).group(1) for s, p in conn.executed if s.lower().startswith("delete from")]
    assert set(deletes) == set(TABLES)
    assert all(p == (RELEASE_ID,) for s, p in conn.executed if s.lower().startswith("delete from"))
    first_run = deletes[: len(TABLES)]
    assert first_run.index("fr_document") == len(TABLES) - 1  # 자식 3개를 먼저, 부모는 마지막에 지운다


def test_session_drops_statement_timeout_and_fk_triggers_before_any_write(fr):
    """SUU-127 교훈: pooler 기본 2분 제한과 행마다 FK 검사를 끄고 시작한다. 고아 FK는 fr_check 가 본다."""
    conn = _conn_for(fr)

    load_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    statements = [s.lower() for s, _ in conn.executed]
    assert "set statement_timeout = 0" in statements
    assert "set session_replication_role = replica" in statements
    first_write = next(i for i, s in enumerate(statements) if s.startswith("delete from"))
    assert statements.index("set statement_timeout = 0") < first_write
    assert statements.index("set session_replication_role = replica") < first_write
