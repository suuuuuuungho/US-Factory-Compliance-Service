"""SUU-209: register → load → check → publish 를 순서대로 배선한다.

각 단계는 test_fr_release/load/check 에서 검증한다. 여기서는 run_fr_ingest 가 네 함수를 올바른 순서·인자로
부르고, 검사 실패 때 공개하지 않고 release 를 failed 로 남기는지, 성공 때 공개(ecfr_publish.publish_release)가
common_dataset_current(fr) 를 갱신하는지 본다 (SUU-126 방식: 함수를 키워드 인자로 주입).
"""
import re
from pathlib import Path

import pytest

from fr_ingest import CheckFailed, _latest_as_of, run_fr_ingest

ROOT = Path("/fake/root")
AS_OF = "2026-09-21"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, data=None):
        self.table, self.data, self.filters = table, data, {}

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def select(self, _columns="*"):
        return self

    def execute(self):
        if self.data is not None:
            self.table.updates.append((self.data, dict(self.filters)))
            for row in self.table.rows:
                if all(row.get(k) == v for k, v in self.filters.items()):
                    row.update(self.data)
        return _Result([r for r in self.table.rows if all(r.get(k) == v for k, v in self.filters.items())])


class _Table:
    def __init__(self):
        self.rows: list[dict] = []
        self.updates: list = []
        self.upserts: list = []

    def select(self, _columns="*"):
        return _Query(self)

    def update(self, data):
        return _Query(self, data)

    def upsert(self, row, on_conflict=None):
        self.upserts.append((dict(row), on_conflict))
        self.rows = [r for r in self.rows if (r["dataset"], r["scope_key"]) != (row["dataset"], row["scope_key"])] + [dict(row)]
        return _Query(self)


class FakeClient:
    def __init__(self):
        self.tables: dict[str, _Table] = {}

    def table(self, name):
        return self.tables.setdefault(name, _Table())


class FakeConn:
    pass


def _fakes(calls, check_result):
    def register(root, as_of, *, client):
        calls.append(("register", root, as_of, client)); return RELEASE_ID

    def load(root, as_of, release_id, *, conn):
        calls.append(("load", root, as_of, release_id, conn)); return {"fr_document": 3}

    def check(root, as_of, release_id, *, conn):
        calls.append(("check", root, as_of, release_id, conn)); return check_result

    def publish(release_id, *, client):
        calls.append(("publish", release_id, client))

    return dict(register_release=register, load_release=load, check_release=check, publish_release=publish)


def test_calls_register_load_check_publish_once_each_in_order():
    calls, client, conn = [], FakeClient(), FakeConn()

    result = run_fr_ingest(ROOT, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": True, "problems": [], "counts": {}}))

    assert result == RELEASE_ID
    assert calls == [
        ("register", ROOT, AS_OF, client),
        ("load", ROOT, AS_OF, RELEASE_ID, conn),
        ("check", ROOT, AS_OF, RELEASE_ID, conn),
        ("publish", RELEASE_ID, client),
    ]
    assert client.tables == {}  # 성공하면 status 는 publish 가 바꾼다. 여기서 따로 update 없음


def test_failed_check_skips_publish_marks_release_failed_and_raises_with_problems():
    calls, client, conn = [], FakeClient(), FakeConn()
    problems = ["fr_identifier: db 3 != jsonl 4", "orphan fr_date_event.document_key: 1"]

    with pytest.raises(CheckFailed, match=re.escape("fr_identifier: db 3 != jsonl 4")) as info:
        run_fr_ingest(ROOT, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": False, "problems": problems, "counts": {}}))

    assert [c[0] for c in calls] == ["register", "load", "check"]  # publish 0번
    assert info.value.release_id == RELEASE_ID and info.value.problems == problems
    assert client.tables["common_dataset_release"].updates == [({"status": "failed"}, {"release_id": RELEASE_ID})]


def test_real_publish_updates_current_pointer_for_fr():
    """publish 는 ecfr_publish.publish_release 를 그대로 쓴다 — release 행의 dataset/scope_key 를 읽어 current 를 갱신한다."""
    calls, client, conn = [], FakeClient(), FakeConn()
    client.table("common_dataset_release").rows.append({
        "release_id": RELEASE_ID, "dataset": "fr", "scope_key": "part63_metadata",
        "source_as_of": AS_OF, "status": "staging", "published_at": None,
    })
    fakes = _fakes(calls, {"ok": True, "problems": [], "counts": {}})
    del fakes["publish_release"]  # 기본값 = ecfr_publish.publish_release

    run_fr_ingest(ROOT, AS_OF, client=client, conn=conn, **fakes)

    release = client.table("common_dataset_release").rows[0]
    assert release["status"] == "published" and release["published_at"]
    current = client.table("common_dataset_current").rows
    assert len(current) == 1
    assert (current[0]["dataset"], current[0]["scope_key"], current[0]["release_id"]) == ("fr", "part63_metadata", RELEASE_ID)
    assert current[0]["latest_source_as_of"] == AS_OF


def test_latest_as_of_picks_the_newest_parsed_folder_or_raises(tmp_path):
    parsed = tmp_path / "parsed"
    for as_of in ("2026-09-10", "2026-09-21", "2026-09-03"):
        (parsed / as_of).mkdir(parents=True)
    assert _latest_as_of(parsed) == "2026-09-21"

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match=re.escape(str(empty))):
        _latest_as_of(empty)
