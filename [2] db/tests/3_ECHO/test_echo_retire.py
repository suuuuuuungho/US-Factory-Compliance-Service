"""SUU-294: 새 ECHO release 를 공개한 직후 옛 release 의 echo_* 행을 지워 DB 가 매주 커지지 않게 한다.

실제 Postgres·Supabase 없음. 가짜 conn 은 받은 SQL 을 기록하고, 가짜 client 는 common_dataset_release 행을 들고 있다.
지우는 것: echo_* 13개 표의 "현재 release 가 아닌" 행 (자식 표부터). 남기는 것: common_dataset_release 행(status → archived),
common_raw_object, common_release_object, echo_code_map (release_id 가 없는 사전).
"""
from echo_parse import TABLES

RELEASE_ID = "11111111-1111-1111-1111-111111111111"
OLD_PUBLISHED = "22222222-2222-2222-2222-222222222222"
OLD_FAILED = "33333333-3333-3333-3333-333333333333"


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.sql.append((" ".join(sql.split()).lower(), params, self.conn.autocommit))


class FakeConn:
    def __init__(self):
        self.sql: list[tuple[str, tuple | None, bool]] = []
        self.autocommit = False
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, data=None):
        self.table, self.data, self.filters, self.excluded = table, data, {}, {}

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def neq(self, column, value):
        self.excluded[column] = value
        return self

    def select(self, _columns="*"):
        return self

    def _matches(self, row):
        return all(row.get(k) == v for k, v in self.filters.items()) and all(row.get(k) != v for k, v in self.excluded.items())

    def execute(self):
        matched = [r for r in self.table.rows if self._matches(r)]
        if self.data is not None:
            for row in matched:
                row.update(self.data)
        return _Result(matched)


class _Table:
    def __init__(self):
        self.rows: list[dict] = []

    def select(self, _columns="*"):
        return _Query(self)

    def update(self, data):
        return _Query(self, data)


class FakeClient:
    def __init__(self):
        self.tables: dict[str, _Table] = {}

    def table(self, name):
        return self.tables.setdefault(name, _Table())


def _client_with_releases():
    client = FakeClient()
    client.table("common_dataset_release").rows.extend([
        {"release_id": RELEASE_ID, "dataset": "echo", "status": "published"},
        {"release_id": OLD_PUBLISHED, "dataset": "echo", "status": "published"},
        {"release_id": OLD_FAILED, "dataset": "echo", "status": "failed"},
        {"release_id": "ecfr-1", "dataset": "ecfr", "status": "published"},  # 다른 데이터셋은 건드리지 않는다
    ])
    return client


def test_deletes_other_release_rows_from_every_echo_table_children_first():
    from echo_retire import retire_other_releases

    conn = FakeConn()

    retire_other_releases(RELEASE_ID, client=_client_with_releases(), conn=conn)

    deletes = [(sql, params) for sql, params, _ in conn.sql if sql.startswith("delete")]
    assert [sql.split(" from ")[1].split(" ")[0] for sql, _ in deletes] == list(reversed(TABLES))  # 자식 표부터, 13개 전부
    for sql, params in deletes:
        assert "release_id <> %s" in sql and params == (RELEASE_ID,), sql  # 현재 release 만 남긴다
    assert "echo_code_map" not in " ".join(sql for sql, _ in deletes)  # 사전은 release 별이 아니다
    assert conn.commits == 1


def test_marks_old_published_echo_releases_archived_only():
    from echo_retire import retire_other_releases

    client = _client_with_releases()

    archived = retire_other_releases(RELEASE_ID, client=client, conn=FakeConn())

    assert archived == [OLD_PUBLISHED]
    status = {r["release_id"]: r["status"] for r in client.table("common_dataset_release").rows}
    assert status == {RELEASE_ID: "published", OLD_PUBLISHED: "archived", OLD_FAILED: "failed", "ecfr-1": "published"}


def test_vacuums_every_echo_table_after_deleting_with_autocommit_and_restores_it():
    from echo_retire import retire_other_releases

    conn = FakeConn()

    retire_other_releases(RELEASE_ID, client=_client_with_releases(), conn=conn)

    vacuums = [(sql, autocommit) for sql, _, autocommit in conn.sql if sql.startswith("vacuum")]
    assert sorted(sql.split()[-1] for sql, _ in vacuums) == sorted(TABLES)  # VACUUM 은 트랜잭션 밖에서만 돈다
    assert all(autocommit for _, autocommit in vacuums)
    assert conn.autocommit is False  # 끝나면 원래대로
    first_vacuum = next(i for i, (sql, _, _) in enumerate(conn.sql) if sql.startswith("vacuum"))
    last_delete = max(i for i, (sql, _, _) in enumerate(conn.sql) if sql.startswith("delete"))
    assert last_delete < first_vacuum  # 지운 다음에 청소
