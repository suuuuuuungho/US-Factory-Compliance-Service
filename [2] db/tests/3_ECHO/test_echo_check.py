"""SUU-124: 적재된 release가 jsonl·report.json·manifest와 같은지 DB에서 세어 보고 문제를 돌려준다.

실제 Postgres 없음. 가짜 conn이 표별 행 리스트를 갖고 있고, check_release가 보내는 SQL 모양
(count / left join / sum(amount) / 짝 검사)을 알아보고 답한다. 테스트가 그 리스트를 망가뜨려 검출을 본다.
"""
import json
import re
from decimal import Decimal

from echo_check import check_release
from echo_parse import ORPHANS, TABLES

AS_OF = "2026-09-17"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"
MEMBERS = {  # 파일별 원본 행 수 (manifest row_count = report files.read)
    "ICIS-AIR_FACILITIES.csv": 2, "ICIS-AIR_PROGRAMS.csv": 1, "ICIS-AIR_PROGRAM_SUBPARTS.csv": 1, "ICIS-AIR_POLLUTANTS.csv": 1,
    "ICIS-AIR_FCES_PCES.csv": 2, "ICIS-AIR_STACK_TESTS.csv": 0, "ICIS-AIR_TITLEV_CERTS.csv": 0, "ICIS-AIR_FORMAL_ACTIONS.csv": 2,
    "ICIS-AIR_INFORMAL_ACTIONS.csv": 0, "ICIS-AIR_VIOLATION_HISTORY.csv": 1, "PIPELINE_CAA_00_COMPLETE.csv": 1,
}
LINES = {  # 표별 jsonl 줄 수. source_row는 ok 1 + held 1
    "echo_source_row": 2, "echo_facility": 2, "echo_facility_identifier": 1, "echo_industry": 1, "echo_program": 1,
    "echo_program_subpart": 1, "echo_pollutant": 1, "echo_activity": 4, "echo_activity_facility": 4, "echo_violation": 1,
    "echo_violation_facility": 1, "echo_penalty": 2, "echo_pipeline_link": 1,
}
AMOUNTS = ("1234.50", "0")


def put_release(root):
    raw = root / "raw" / AS_OF
    raw.mkdir(parents=True)
    icis = [{"name": m, "row_count": n} for m, n in MEMBERS.items() if m.startswith("ICIS")]
    pipe = [{"name": m, "row_count": n} for m, n in MEMBERS.items() if not m.startswith("ICIS")]
    (raw / "manifest.json").write_text(json.dumps([
        {"name": "ICIS-AIR_downloads.zip", "path": "x", "sha256": "a" * 64, "members": icis},
        {"name": "pipeline_caa_downloads.zip", "path": "y", "sha256": "b" * 64, "members": pipe},
    ]), encoding="utf-8")
    parsed = root / "parsed" / AS_OF
    parsed.mkdir(parents=True)
    for table, n in LINES.items():
        rows = [{"i": i} for i in range(n)]
        if table == "echo_source_row":
            rows = [{"parse_status": "ok"}, {"parse_status": "held"}]
        if table == "echo_penalty":
            rows = [{"penalty_key": f"formal:{i}", "amount": a} for i, a in enumerate(AMOUNTS)]
        (parsed / f"{table}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (parsed / "report.json").write_text(json.dumps({
        "files": {m: {"read": n, "ok": n, "held": 0} for m, n in MEMBERS.items()},
    }), encoding="utf-8")


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._answer = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        text = " ".join(sql.split()).lower()
        assert params == (RELEASE_ID,) or (params and RELEASE_ID in params), (sql, params)  # 항상 release_id로 좁힌다
        self.conn.sql.append(text)
        if "left join" in text:
            child = re.search(r"from (\w+) c left join", text).group(1)
            self._answer = (self.conn.orphans.get(child, 0),)
        elif "sum(amount)" in text:
            self._answer = (sum(Decimal(a) for a in self.conn.amounts),)
        elif "is null" in text and "echo_pipeline_link" in text:
            self._answer = (self.conn.broken_pairs,)
        else:
            table = re.search(r"count\(\*\) from (\w+)", text).group(1)
            self._answer = (self.conn.counts[table],)
        return self

    def fetchone(self):
        return self._answer


class FakeConn:
    """SUU-123 적재가 끝난 뒤의 DB 상태를 흉내낸다. 테스트가 값을 바꿔 검출을 본다."""

    def __init__(self):
        self.counts = dict(LINES, echo_source_row=1)  # held만 들어간다
        self.amounts = list(AMOUNTS)
        self.orphans: dict[str, int] = {}
        self.broken_pairs = 0
        self.sql: list[str] = []

    def cursor(self):
        return FakeCursor(self)


def test_clean_release_is_ok_with_no_problems_and_reports_counts(tmp_path):
    put_release(tmp_path)
    conn = FakeConn()

    result = check_release(tmp_path, AS_OF, RELEASE_ID, conn=conn)

    assert result["ok"] is True and result["problems"] == []
    assert result["counts"] == {**LINES, "echo_source_row": 1, "penalty_sum": "1234.50"}
    assert len([s for s in conn.sql if re.fullmatch(r"select count\(\*\) from echo_\w+ where release_id = %s", s)]) == len(TABLES)
    assert len([s for s in conn.sql if "left join" in s]) == len(ORPHANS)  # 관계 10개를 DB에서 다시 센다


def test_missing_row_extra_penalty_orphan_and_report_mismatch_are_reported(tmp_path):
    put_release(tmp_path)
    conn = FakeConn()
    conn.counts["echo_activity"] -= 1  # 행 하나 사라짐
    conn.counts["echo_penalty"] += 1
    conn.amounts.append("500")  # 벌금 하나 더 들어감
    conn.orphans["echo_penalty"] = 1  # 관계가 하나뿐인 자식 표
    conn.broken_pairs = 2
    report = json.loads((tmp_path / "parsed" / AS_OF / "report.json").read_text(encoding="utf-8"))
    report["files"]["ICIS-AIR_FCES_PCES.csv"]["read"] = 3  # manifest는 2
    (tmp_path / "parsed" / AS_OF / "report.json").write_text(json.dumps(report), encoding="utf-8")

    result = check_release(tmp_path, AS_OF, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    problems = "\n".join(result["problems"])
    assert "echo_activity" in problems and "3" in problems and "4" in problems  # db 3 != jsonl 4
    assert "echo_penalty" in problems and "1734.50" in problems and "1234.50" in problems  # sum
    assert "orphan echo_penalty.activity: 1" in problems
    assert "echo_pipeline_link" in problems and "2" in problems
    assert "ICIS-AIR_FCES_PCES.csv" in problems
    assert len(result["problems"]) == 6  # activity count, penalty count, penalty sum, orphan, pairs, report/manifest
