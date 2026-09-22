"""SUU-224: 적재된 release 가 jsonl 과 같은지 DB 에서 세어 보고 문제를 돌려준다.

실제 Postgres 없음. 가짜 conn 이 check_release 가 보내는 SQL 모양(count / left join)을 알아보고 답한다.
테스트가 답을 망가뜨려 검출을 본다 (fr_check 테스트 방식).
검사 3가지: 표 9개 행 수 = jsonl 줄 수, 고아 FK 0 (entry_document→version, page→version, cfr_reference→ecfr_node).
재실행 중복 0 은 같은 기준(행 수 = 줄 수)으로 잡힌다.
"""
from __future__ import annotations

import re

from adi_check import check_release

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
RELEASE_TABLES = ("adi_source_entry", "adi_entry_document")
LINES = {"adi_source_entry": 275, "adi_document": 2, "adi_document_version": 2, "adi_entry_document": 3, "adi_page": 7,
         "adi_block": 6, "adi_cfr_reference": 4, "adi_document_relation": 1, "adi_facility_candidate": 1}
ORPHAN_CHILDREN = ("adi_entry_document", "adi_page", "adi_cfr_reference")


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
        self.conn.sql.append(text)
        if "left join" in text:
            child = re.search(r"from (\w+) c left join (\w+)", text).group(1)
            self._answer = (self.conn.orphans.get(child, 0),)
        else:
            table = re.search(r"count\(\*\) from (\w+)", text).group(1)
            self._answer = (self.conn.counts[table],)
        # release 표는 release_id 로, 나머지는 jsonl 키 목록으로 좁힌다
        if "release_id = %s" in text:
            assert params == (RELEASE_ID,), (sql, params)
        else:
            assert "= any(%s)" in text and isinstance(params[0], list) and params[0], (sql, params)
        return self

    def fetchone(self):
        return self._answer


class FakeConn:
    """adi_load 가 끝난 뒤의 DB 상태. 테스트가 값을 바꿔 검출을 본다."""

    def __init__(self):
        self.counts = dict(LINES)
        self.orphans: dict[str, int] = {}
        self.sql: list[str] = []

    def cursor(self):
        return FakeCursor(self)


def test_clean_release_is_ok_with_no_problems_and_reports_counts(adi):
    conn = FakeConn()

    result = check_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is True and result["problems"] == []
    assert result["counts"] == LINES == {t: len(adi.rows(t)) for t in adi.tables}
    assert len([s for s in conn.sql if re.match(r"select count\(\*\) from adi_\w+ where", s)]) == 9
    joins = [re.search(r"from (\w+) c left join (\w+)", s).groups() for s in conn.sql if "left join" in s]
    assert sorted(joins) == [("adi_cfr_reference", "ecfr_node"), ("adi_entry_document", "adi_document_version"), ("adi_page", "adi_document_version")]
    ecfr_join = next(s for s in conn.sql if "left join ecfr_node" in s)
    assert "current_ecfr_release_id" in ecfr_join and "current_node_key is not null" in ecfr_join  # 못 이은 인용(NULL)은 고아가 아니다


def test_row_count_mismatch_names_the_table(adi):
    conn = FakeConn()
    conn.counts["adi_page"] += 1  # 재실행 중복 같은 상황

    result = check_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

    assert result["ok"] is False
    assert result["problems"] == ["adi_page: db 8 != jsonl 7"]


def test_one_orphan_fk_names_the_child_table(adi):
    for child, column in (("adi_entry_document", "version_id"), ("adi_page", "version_id"), ("adi_cfr_reference", "current_node_key")):
        conn = FakeConn()
        conn.orphans[child] = 1

        result = check_release(adi.root, adi.as_of, RELEASE_ID, conn=conn)

        assert result["ok"] is False
        assert result["problems"] == [f"orphan {child}.{column}: 1"], child
