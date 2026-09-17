"""SUU-126: register → load → check → publish를 순서대로 배선한다.

각 단계는 SUU-122~125에서 검증했다. 여기서는 run_echo_ingest가 네 함수를 올바른 순서·인자로 부르고,
검사 실패 때 공개하지 않고 release를 failed로 남기는지만 본다 (SUU-68 방식: 함수를 키워드 인자로 주입).
"""
import re
from pathlib import Path

import pytest

from echo_ingest import CheckFailed, _latest_as_of, run_echo_ingest

ROOT = Path("/fake/root")
AS_OF = "2026-09-17"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"


class _Query:
    def __init__(self, table, data):
        self.table, self.data, self.filters = table, data, {}

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def execute(self):
        self.table.updates.append((self.data, dict(self.filters)))


class _Table:
    def __init__(self):
        self.updates = []

    def update(self, data):
        return _Query(self, data)


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return self.tables.setdefault(name, _Table())


class FakeConn:
    pass


def _fakes(calls, check_result):
    def register(root, as_of, *, client):
        calls.append(("register", root, as_of, client)); return RELEASE_ID

    def load(root, as_of, release_id, code_map_version, *, conn):
        calls.append(("load", root, as_of, release_id, code_map_version, conn)); return {"echo_facility": 1}

    def check(root, as_of, release_id, *, conn):
        calls.append(("check", root, as_of, release_id, conn)); return check_result

    def publish(release_id, *, client):
        calls.append(("publish", release_id, client))

    return dict(register_release=register, load_release=load, check_release=check, publish_release=publish)


def test_calls_register_load_check_publish_in_order_with_the_same_release_id():
    calls, client, conn = [], FakeClient(), FakeConn()

    result = run_echo_ingest(ROOT, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": True, "problems": [], "counts": {}}))

    assert result == RELEASE_ID
    assert calls == [
        ("register", ROOT, AS_OF, client),
        ("load", ROOT, AS_OF, RELEASE_ID, AS_OF, conn),  # code_map_version 기본값 = as_of
        ("check", ROOT, AS_OF, RELEASE_ID, conn),
        ("publish", RELEASE_ID, client),
    ]
    assert client.tables == {}  # 성공하면 status는 publish가 바꾼다. 여기서 따로 update 없음


def test_failed_check_skips_publish_marks_release_failed_and_raises_with_problems():
    calls, client, conn = [], FakeClient(), FakeConn()
    problems = ["echo_activity: db 3 != jsonl 4", "orphan echo_penalty.activity: 1"]

    with pytest.raises(CheckFailed, match=re.escape("echo_activity: db 3 != jsonl 4")) as info:
        run_echo_ingest(ROOT, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": False, "problems": problems, "counts": {}}))

    assert [c[0] for c in calls] == ["register", "load", "check"]  # publish 없음
    assert info.value.release_id == RELEASE_ID and info.value.problems == problems
    assert client.tables["common_dataset_release"].updates == [({"status": "failed"}, {"release_id": RELEASE_ID})]


def test_latest_as_of_picks_the_newest_parsed_folder_or_raises(tmp_path):
    parsed = tmp_path / "parsed"
    for as_of in ("2026-09-10", "2026-09-17", "2026-09-03"):
        (parsed / as_of).mkdir(parents=True)
    assert _latest_as_of(parsed) == "2026-09-17"

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match=re.escape(str(empty))):
        _latest_as_of(empty)
