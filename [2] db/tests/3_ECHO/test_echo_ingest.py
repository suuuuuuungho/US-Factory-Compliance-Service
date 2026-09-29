"""SUU-126: register → load → check → publish를 순서대로 배선한다.

각 단계는 SUU-122~125에서 검증했다. 여기서는 run_echo_ingest가 네 함수를 올바른 순서·인자로 부르고,
검사 실패 때 공개하지 않고 release를 failed로 남기는지만 본다 (SUU-68 방식: 함수를 키워드 인자로 주입).

SUU-294: 같은 ZIP 이 이미 공개돼 있으면(published_release_id) 아무것도 하지 않고 ``status=no_change``.
새로 공개했으면 그 직후 ``retire_other_releases`` 로 옛 release 행을 지우고 ``status=new``. 검사 실패면 retire 도 없다.
"""
import re
from pathlib import Path

import pytest

from echo_ingest import CheckFailed, _latest_as_of, format_result, run_echo_ingest

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

    def retire(release_id, *, client, conn):
        calls.append(("retire", release_id, client, conn)); return ["old-release"]

    return dict(published_release_id=lambda root, as_of, *, client: None, register_release=register,
                load_release=load, check_release=check, publish_release=publish, retire_other_releases=retire)


def test_calls_register_load_check_publish_retire_in_order_with_the_same_release_id(tmp_path):
    (tmp_path / "code_map" / "2026-09-17").mkdir(parents=True)
    calls, client, conn = [], FakeClient(), FakeConn()

    result = run_echo_ingest(tmp_path, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": True, "problems": [], "counts": {}}))

    assert result == {"release_id": RELEASE_ID, "status": "new"}
    assert calls == [
        ("register", tmp_path, AS_OF, client),
        ("load", tmp_path, AS_OF, RELEASE_ID, "2026-09-17", conn),  # SUU-299: code_map_version 기본값 = 가장 최근 code_map 폴더
        ("check", tmp_path, AS_OF, RELEASE_ID, conn),
        ("publish", RELEASE_ID, client),
        ("retire", RELEASE_ID, client, conn),  # SUU-294: 공개 성공 뒤에만 옛 release 를 지운다
    ]
    assert client.tables == {}  # 성공하면 status는 publish가 바꾼다. 여기서 따로 update 없음


# ---- SUU-294

def test_already_published_zip_skips_everything_and_reports_no_change():
    calls, client, conn = [], FakeClient(), FakeConn()
    fakes = _fakes(calls, {"ok": True, "problems": [], "counts": {}})
    fakes["published_release_id"] = lambda root, as_of, *, client: RELEASE_ID

    result = run_echo_ingest(ROOT, AS_OF, client=client, conn=conn, **fakes)

    assert result == {"release_id": RELEASE_ID, "status": "no_change"}
    assert calls == []  # register·load·check·publish·retire 모두 0번
    assert client.tables == {}


def test_uses_the_real_functions_by_default():
    import echo_ingest

    defaults = echo_ingest.run_echo_ingest.__kwdefaults__
    assert defaults["published_release_id"].__module__ == "echo_release"
    assert defaults["retire_other_releases"].__module__ == "echo_retire"


def test_format_result_is_one_line_the_workflow_can_grep():
    assert format_result({"release_id": RELEASE_ID, "status": "new"}) == f"status=new release_id={RELEASE_ID}"


def test_failed_check_skips_publish_marks_release_failed_and_raises_with_problems(tmp_path):
    (tmp_path / "code_map" / "2026-09-17").mkdir(parents=True)
    calls, client, conn = [], FakeClient(), FakeConn()
    problems = ["echo_activity: db 3 != jsonl 4", "orphan echo_penalty.activity: 1"]

    with pytest.raises(CheckFailed, match=re.escape("echo_activity: db 3 != jsonl 4")) as info:
        run_echo_ingest(tmp_path, AS_OF, client=client, conn=conn, **_fakes(calls, {"ok": False, "problems": problems, "counts": {}}))

    assert [c[0] for c in calls] == ["register", "load", "check"]  # publish 없음, retire 도 없음 (옛 행은 그대로)
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


# ---- SUU-299: 9/29 러너에서 code_map/<오늘> 을 찾다가 FileNotFoundError. 코드표는 가끔만 새로 만든다

def test_code_map_defaults_to_the_newest_code_map_folder_not_as_of(tmp_path):
    for version in ("2026-08-01", "2026-09-17"):
        (tmp_path / "code_map" / version).mkdir(parents=True)
    calls, client, conn = [], FakeClient(), FakeConn()

    run_echo_ingest(tmp_path, "2026-09-29", client=client, conn=conn, **_fakes(calls, {"ok": True, "problems": [], "counts": {}}))

    load = next(c for c in calls if c[0] == "load")
    assert load[4] == "2026-09-17"
