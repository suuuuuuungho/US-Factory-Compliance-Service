"""SUU-123: parsed/{as_of}/ jsonl 13개 + code_map을 release_id를 붙여 echo_* 표에 COPY로 넣는다.

실제 Postgres에는 붙지 않는다. psycopg 3 모양(``conn.cursor()`` → ``cur.execute(sql, params)``,
``with cur.copy(sql) as copy: copy.write_row(row)``)의 가짜 conn을 주입해 어떤 COPY가 어떤 행으로
나가는지만 본다. 열 타입(date/numeric/jsonb)은 SUU-121 표가 정하고 COPY 텍스트가 그 형식이면 된다.
"""
import json
import re

from echo_load import load_release

AS_OF = "2026-09-17"
CODE_MAP_VERSION = "2026-09-17"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"
ICIS_SHA = "a" * 64
ICIS_OBJECT_ID = "22222222-2222-2222-2222-222222222222"

# 실제 2026-09-17 산출물 첫 행들을 줄인 것. 표별 키 순서 = jsonl 키 순서.
ROWS = {
    "echo_source_row": [
        {"source_file": "ICIS-AIR_FACILITIES.csv", "source_row_no": 1, "raw_payload": {"PGM_SYS_ID": "F1"}, "row_hash": "h1", "parse_status": "ok", "error": None, "source_object_sha256": ICIS_SHA},
        {"source_file": "ICIS-AIR_FCES_PCES.csv", "source_row_no": 7, "raw_payload": {"PGM_SYS_ID": "F1", "ACTUAL_END_DATE": "13/40/2020"}, "row_hash": "h2", "parse_status": "held", "error": "ValueError: bad date", "source_object_sha256": ICIS_SHA},
    ],
    "echo_facility": [
        {"pgm_sys_id": "F1", "registry_id": "110070834547", "name": "HIGHLAND PARK MARKET", "address": "68 BRIDGE ST ", "city": "SUFFIELD", "county": "Hartford", "state": "CT", "zip": "06078", "epa_region": "01", "facility_type": None, "source_class": None, "source_class_desc": None, "operating_status": None, "operating_status_desc": None, "current_hpv": "No Violation Identified", "local_control_region_code": None, "local_control_region_name": None},
        {"pgm_sys_id": "F2", "registry_id": None, "name": "PLANT TWO", "address": None, "city": None, "county": None, "state": "NJ", "zip": None, "epa_region": "02", "facility_type": None, "source_class": None, "source_class_desc": None, "operating_status": None, "operating_status_desc": None, "current_hpv": None, "local_control_region_code": None, "local_control_region_name": None},
    ],
    "echo_facility_identifier": [
        {"program_system": "ICIS-AIR", "pgm_sys_id": "F1", "registry_id": "110070834547", "mapping_source": "ICIS-AIR_FACILITIES.csv", "review_status": "source_stated"},
    ],
    "echo_industry": [
        {"pgm_sys_id": "F1", "code_system": "NAICS", "code": "445110", "source_locator": "NAICS_CODES"},
    ],
    "echo_program": [
        {"pgm_sys_id": "F1", "program_code": "CAASIP", "description": "SIP", "status_code": "CLS", "status_desc": "Permanently Closed", "begin_date": "2017-02-22", "updated_date": None, "raw_dates": {"BEGIN_DATE": "02/22/2017", "UPDATED_DATE": ""}},
    ],
    "echo_program_subpart": [
        {"pgm_sys_id": "F1", "program_code": "CAASIP", "subpart_code": "CAANESHFF", "subpart_desc": "NESHAP Part 61 - Subpart FF", "cfr_title": 40, "cfr_part": "61", "cfr_subpart": "FF", "mapping_status": "mapped"},
    ],
    "echo_pollutant": [
        {"pgm_sys_id": "F1", "pollutant_key": "300000322", "pollutant_code": "300000322", "description": "TOTAL PARTICULATE MATTER", "srs_id": "1647643", "cas_number": None, "class_code": "MIN", "class_desc": "Minor Emissions", "source_locator": "ICIS-AIR_POLLUTANTS.csv:1", "review_status": "ok"},
    ],
    "echo_activity": [
        {"activity_kind": "inspection", "activity_id": "121929", "type_code": "INS", "type_desc": "Inspection/Evaluation", "lead_flag": "E", "monitor_code": "PCE", "monitor_desc": "PCE On-Site", "activity_date": "2004-05-04", "raw_date": "05-04-2004", "attributes": {"PROGRAM_CODES": None, "ACTIVITY_PURPOSE_DESC": "Agency Priority"}},
        {"activity_kind": "formal", "activity_id": "600031828", "type_code": "AO", "type_desc": None, "lead_flag": None, "monitor_code": None, "monitor_desc": None, "activity_date": None, "raw_date": "", "attributes": {}},
    ],
    "echo_activity_facility": [
        {"activity_kind": "inspection", "activity_id": "121929", "pgm_sys_id": "F1"},
        {"activity_kind": "formal", "activity_id": "600031828", "pgm_sys_id": "F1"},
    ],
    "echo_violation": [
        {"violation_id": "3400309508", "determination_uid": "DE000A", "policy_code": "HPV", "agency": "State", "state": "DE", "first_frv_date": None, "hpv_dayzero_date": "1997-02-28", "resolved_date": "1998-02-19", "programs": ["CAASIP"], "pollutants": ["300000243"], "raw_dates": {"HPV_DAYZERO_DATE": "02-28-1997"}, "attributes": {"AIR_LCON_CODE": None}},
    ],
    "echo_violation_facility": [
        {"violation_id": "3400309508", "pgm_sys_id": "F1"},
    ],
    "echo_penalty": [
        {"penalty_key": "formal:1", "activity_kind": "formal", "activity_id": "600031828", "amount": "1234.50", "amount_kind": "penalty", "currency": "USD", "amount_scope": "row", "raw_amount": "1234.5", "source_locator": "ICIS-AIR_FORMAL_ACTIONS.csv:1"},
    ],
    "echo_pipeline_link": [
        {"link_key": "1d7a", "pgm_sys_id": "F1", "eval_activity_id": "-9999", "violation_activity_id": "3400309508", "ea_activity_id": None, "ea_fea_activity_id": None, "flags": {"PIPELINE_FLAG": "N", "FEA_ISSUE_DATE_FLAG": None}, "synthetic_violation": True, "resolution_status": "resolved", "resolved_eval_kind": None, "resolved_eval_id": None, "resolved_violation_id": "3400309508", "resolved_ea_kind": None, "resolved_ea_id": None, "source_row_no": 1, "attributes": {"SORT_ORDER": "55478", "VIOL_END_DATE": "N/A"}},
    ],
}
CODE_MAP = [
    {"program_code": "CAAGHG", "raw_subpart_code": "CAAGHGA", "raw_description": "GHG Part 98 - Subpart A", "cfr_title": "40", "cfr_part": "98", "cfr_subpart": "A", "review_status": "ok", "dictionary_version": CODE_MAP_VERSION, "source_url": "u"},
    {"program_code": "CAAMACT", "raw_subpart_code": "CAAMACT", "raw_description": "6B MACT Part 63 - Subpart BBBBBB", "cfr_title": "40", "cfr_part": "63", "cfr_subpart": "BBBBBB", "review_status": "conflict", "dictionary_version": CODE_MAP_VERSION, "source_url": "u"},
]


def put_parsed(root):
    out = root / "parsed" / AS_OF
    out.mkdir(parents=True)
    for table, rows in ROWS.items():
        (out / f"{table}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (out / "report.json").write_text("{}", encoding="utf-8")
    code_map = root / "code_map" / CODE_MAP_VERSION / "echo_code_map.jsonl"
    code_map.parent.mkdir(parents=True)
    code_map.write_text("".join(json.dumps(r) + "\n" for r in CODE_MAP), encoding="utf-8")


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
    """psycopg 3의 cursor 모양. execute한 SQL과 COPY로 들어온 행을 표별로 쌓는다."""

    def __init__(self, conn):
        self.conn = conn
        self._pending = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append((" ".join(sql.split()), params))
        text = " ".join(sql.split()).lower()
        if text.startswith("delete from"):
            table = re.match(r"delete from (\w+)", text).group(1)
            if table in self.conn.tables:
                self.conn.tables[table] = [r for r in self.conn.tables[table] if r[0] != params[0]]
        if "common_raw_object" in text:
            self._pending = [(ICIS_OBJECT_ID, ICIS_SHA)]
        if text.startswith("insert into echo_code_map"):
            rows = self.conn.tables.setdefault("echo_code_map", [])
            if tuple(params[:4]) not in {r[:4] for r in rows}:  # PK (version, program, subpart, description) — on conflict do nothing
                rows.append(tuple(params))
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
    def __init__(self):
        self.tables: dict[str, list[tuple]] = {}
        self.columns: dict[str, tuple[str, ...]] = {}
        self.executed: list = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def _row(conn, table, i=0):
    return dict(zip(conn.columns[table], conn.tables[table][i]))


def test_copies_every_jsonl_row_with_release_id_and_only_held_source_rows(tmp_path):
    put_parsed(tmp_path)
    conn = FakeConn()

    counts = load_release(tmp_path, AS_OF, RELEASE_ID, CODE_MAP_VERSION, conn=conn)

    expected = {table: len(rows) for table, rows in ROWS.items()}
    expected["echo_source_row"] = 1  # held 행만
    assert counts == {**expected, "echo_code_map": 2}
    assert {t: len(r) for t, r in conn.tables.items()} == {**expected, "echo_code_map": 2}
    for table in ROWS:
        assert conn.columns[table][0] == "release_id" and all(r[0] == RELEASE_ID for r in conn.tables[table]), table

    held = _row(conn, "echo_source_row")
    assert held["parse_status"] == "held" and held["source_row_no"] == 7
    assert held["source_object_id"] == ICIS_OBJECT_ID  # sha256 → common_raw_object.object_id
    assert "source_object_sha256" not in conn.columns["echo_source_row"]
    assert conn.commits >= 1

    # 부모 표가 자식보다 먼저 COPY 된다 (FK)
    order = list(conn.tables)  # COPY 순서
    assert order.index("echo_facility") < order.index("echo_industry")
    assert order.index("echo_program") < order.index("echo_program_subpart")
    assert order.index("echo_activity") < order.index("echo_activity_facility") and order.index("echo_activity") < order.index("echo_penalty")
    assert order.index("echo_violation") < order.index("echo_violation_facility") and order.index("echo_violation") < order.index("echo_pipeline_link")


def test_loading_the_same_release_twice_does_not_grow_any_table(tmp_path):
    put_parsed(tmp_path)
    conn = FakeConn()

    load_release(tmp_path, AS_OF, RELEASE_ID, CODE_MAP_VERSION, conn=conn)
    first = {t: len(r) for t, r in conn.tables.items()}
    load_release(tmp_path, AS_OF, RELEASE_ID, CODE_MAP_VERSION, conn=conn)

    assert {t: len(r) for t, r in conn.tables.items()} == first
    deletes = [(s, p) for s, p in conn.executed if s.lower().startswith("delete from")]
    assert {p[0] for _, p in deletes} == {RELEASE_ID}
    assert {re.match(r"delete from (\w+)", s.lower()).group(1) for s, _ in deletes} == set(ROWS)  # 13개 표 전부
    # 자식 표를 부모보다 먼저 지운다 (FK)
    first_run = [re.match(r"delete from (\w+)", s.lower()).group(1) for s, _ in deletes][: len(ROWS)]
    assert first_run.index("echo_activity_facility") < first_run.index("echo_activity")
    assert first_run.index("echo_pipeline_link") < first_run.index("echo_violation")
    assert first_run.index("echo_industry") < first_run.index("echo_facility")
    # code_map은 지우지 않고 upsert (다른 release도 같은 사전을 쓴다)
    assert all("echo_code_map" not in s.lower() for s, _ in deletes)
    assert any("on conflict" in s.lower() for s, _ in conn.executed if "echo_code_map" in s.lower())


def test_values_are_copied_in_the_text_form_postgres_needs_for_each_column_type(tmp_path):
    put_parsed(tmp_path)
    conn = FakeConn()

    load_release(tmp_path, AS_OF, RELEASE_ID, CODE_MAP_VERSION, conn=conn)

    activity = _row(conn, "echo_activity")
    assert activity["activity_date"] == "2004-05-04"  # date 열: ISO 문자열
    assert json.loads(activity["attributes"]) == {"PROGRAM_CODES": None, "ACTIVITY_PURPOSE_DESC": "Agency Priority"}  # jsonb: JSON 문자열
    assert _row(conn, "echo_activity", 1)["activity_date"] is None  # NULL

    penalty = _row(conn, "echo_penalty")
    assert penalty["amount"] == "1234.50"  # numeric: 문자열 그대로 (float 변환 금지)

    link = _row(conn, "echo_pipeline_link")
    assert link["synthetic_violation"] is True and link["source_row_no"] == 1
    assert json.loads(link["flags"]) == {"PIPELINE_FLAG": "N", "FEA_ISSUE_DATE_FLAG": None}
    assert json.loads(link["attributes"])["VIOL_END_DATE"] == "N/A"

    violation = _row(conn, "echo_violation")
    assert json.loads(violation["programs"]) == ["CAASIP"] and json.loads(violation["raw_dates"]) == {"HPV_DAYZERO_DATE": "02-28-1997"}

    subpart = _row(conn, "echo_program_subpart")
    assert subpart["cfr_title"] == 40  # integer

    held = _row(conn, "echo_source_row")
    assert json.loads(held["raw_payload"]) == {"PGM_SYS_ID": "F1", "ACTUAL_END_DATE": "13/40/2020"}

    code_map = dict(zip(("dictionary_version", "program_code", "raw_subpart_code", "raw_description", "cfr_title", "cfr_part", "cfr_subpart", "source_url", "review_status"), conn.tables["echo_code_map"][0]))
    assert (code_map["dictionary_version"], code_map["cfr_title"], code_map["review_status"]) == (CODE_MAP_VERSION, 40, "ok")
