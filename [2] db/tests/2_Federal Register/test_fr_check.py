"""SUU-209: 적재된 release 가 jsonl·quality_report.json 과 같은지 DB 에서 세어 보고 문제를 돌려준다.

실제 Postgres 없음. 가짜 conn 이 check_release 가 보내는 SQL 모양(count / left join / is null)을 알아보고
답한다. 테스트가 답을 망가뜨려 검출을 본다 (SUU-124 방식).
"""
import json
import re

from fr_check import check_release

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
TABLES = ["fr_document", "fr_identifier", "fr_cfr_reference", "fr_date_event"]
CHILDREN = ["fr_identifier", "fr_cfr_reference", "fr_date_event"]
LINES = {"fr_document": 3, "fr_identifier": 4, "fr_cfr_reference": 3, "fr_date_event": 2}


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
        assert params == (RELEASE_ID,), (sql, params)  # 항상 release_id 로 좁힌다
        self.conn.sql.append(text)
        if "left join" in text:
            child = re.search(r"from (\w+) c left join fr_document", text).group(1)
            self._answer = (self.conn.orphans.get(child, 0),)
        elif "source_object_id is null" in text:
            self._answer = (self.conn.unlinked,)
        else:
            table = re.search(r"count\(\*\) from (\w+)", text).group(1)
            self._answer = (self.conn.counts[table],)
        return self

    def fetchone(self):
        return self._answer


class FakeConn:
    """fr_load 가 끝난 뒤의 DB 상태. 테스트가 값을 바꿔 검출을 본다."""

    def __init__(self):
        self.counts = dict(LINES)
        self.orphans: dict[str, int] = {}
        self.unlinked = 0  # source_object_id 가 NULL 인 fr_document 행 수
        self.sql: list[str] = []

    def cursor(self):
        return FakeCursor(self)


def test_clean_release_is_ok_with_no_problems_and_reports_counts(fr):
    conn = FakeConn()

    result = check_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is True and result["problems"] == []
    assert result["counts"] == LINES
    assert len([s for s in conn.sql if re.fullmatch(r"select count\(\*\) from fr_\w+ where release_id = %s", s)]) == 4
    assert len([s for s in conn.sql if "left join fr_document" in s]) == 3  # 자식 3표 → fr_document


def test_row_count_mismatch_names_the_table(fr):
    conn = FakeConn()
    conn.counts["fr_identifier"] -= 1

    result = check_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    assert len(result["problems"]) == 1
    assert "fr_identifier" in result["problems"][0] and "3" in result["problems"][0] and "4" in result["problems"][0]


def test_one_orphan_fk_names_the_child_table(fr):
    conn = FakeConn()
    conn.orphans["fr_date_event"] = 1

    result = check_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    assert result["problems"] == ["orphan fr_date_event.document_key: 1"]


def test_document_without_source_object_is_a_problem(fr):
    conn = FakeConn()
    conn.unlinked = 2

    result = check_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    assert any("source_object_id" in p and "2" in p for p in result["problems"])


def test_quality_report_that_disagrees_with_db_is_a_problem(fr):
    report_path = fr.root / "parsed" / fr.as_of / "quality_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["rows"]["fr_document"] = 4  # jsonl 과 DB 는 3
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    conn = FakeConn()

    result = check_release(fr.root, fr.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    assert any("quality_report" in p and "fr_document" in p for p in result["problems"])
