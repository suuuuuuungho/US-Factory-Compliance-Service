"""SUU-230: fr-diff.json 을 fr_diff 표에 COPY 로 넣는다. 실제 Postgres 없음, psycopg 3 모양의 가짜 conn."""
import json
import re

from fr_diff_load import COLUMNS, load_diff

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
ROW = {"kind": "changed", "before": "old", "after": "new", "is_context": False}
CTX = {"kind": "equal", "before": "same", "after": "same", "is_context": True}
DATA = {
    "generated_at": "2026-09-22T00:00:00+00:00", "since": "2024-01-01",
    "documents": [
        {"document_key": "2026-07-06/2026-13550", "reason": None, "sections": [
            {"section": "63.2233", "node_key": "40/63/subpart-DDDD/section-63.2233",
             "before_date": "2026-07-05", "after_date": "2026-07-06", "rows": [CTX, ROW, ROW]},
            {"section": "63.2240", "node_key": None,
             "before_date": "2026-07-05", "after_date": "2026-07-06", "rows": [ROW]},
        ]},
        {"document_key": "2025-08-15/2025-15614", "reason": "no_effective_date", "sections": []},
    ],
}


class _Copy:
    def __init__(self, sink): self.sink = sink
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def write_row(self, row): self.sink.append(tuple(row))


class FakeConn:
    def __init__(self):
        self.rows, self.executed, self.committed = [], [], False
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def execute(self, sql, params=None): self.executed.append((" ".join(sql.split()), params))
    def copy(self, sql):
        m = re.match(r"\s*copy\s+fr_diff\s*\(([^)]*)\)\s+from\s+stdin", sql, re.I)
        assert m and tuple(c.strip() for c in m.group(1).split(",")) == COLUMNS, sql
        return _Copy(self.rows)
    def commit(self): self.committed = True


def test_load_diff_copies_every_row_and_skips_documents_without_sections(tmp_path):
    path = tmp_path / "fr-diff.json"
    path.write_text(json.dumps(DATA), encoding="utf-8")
    conn = FakeConn()

    count = load_diff(path, RELEASE_ID, conn=conn)

    expected = sum(len(s["rows"]) for d in DATA["documents"] for s in d["sections"])
    assert count == expected == 4 == len(conn.rows)
    assert conn.executed[0] == ("delete from fr_diff where release_id = %s", (RELEASE_ID,))
    assert conn.committed
    assert {r[1] for r in conn.rows} == {"2026-07-06/2026-13550"}      # 시행일 없는 문서는 행 0개
    first = dict(zip(COLUMNS, conn.rows[0]))
    assert first == {
        "release_id": RELEASE_ID, "document_key": "2026-07-06/2026-13550", "section": "63.2233",
        "node_key": "40/63/subpart-DDDD/section-63.2233", "seq": 1, "change_kind": "equal",
        "before_text": "same", "after_text": "same", "is_context": True,
        "before_date": "2026-07-05", "after_date": "2026-07-06",
    }
    assert [r[4] for r in conn.rows] == [1, 2, 3, 1]                     # seq 는 섹션마다 1부터
