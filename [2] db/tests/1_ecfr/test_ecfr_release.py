"""SUU-65: 파싱된 eCFR 원본 하나를 Supabase common_* 테이블에 release로 등록한다.

실제 Supabase에는 붙지 않는다. supabase-py와 같은 모양(``client.table(name)
.insert(row).execute()``, ``.select(...).eq(...).execute()``)의 가짜 client를
주입해서 어떤 행이 만들어지는지만 확인한다.
"""
import hashlib
from datetime import date
from pathlib import Path

from ecfr_raw import save_raw
from ecfr_release import DATASET, SCOPE_KEY, register_release

AS_OF = "2026-09-10"


def put_raw(root):
    """1단계(ecfr_collect)가 남기는 모양 그대로 raw/{as_of}/manifest.json을 만든다."""
    for name, body, media in (
        ("title-40-structure.json", b'{"fake": "structure"}', "application/json"),
        ("title-40-part-63.xml", b"<PART>fake</PART>", "application/xml"),
    ):
        save_raw(
            root, date.fromisoformat(AS_OF), name, body,
            source_url=f"https://example.test/{name}", final_url=f"https://example.test/{name}",
            http_status=200, media_type=media,
        )


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows
        self._filters: dict = {}

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def select(self, _columns="*"):
        return self

    def execute(self):
        matched = [
            row for row in self._rows
            if all(row.get(key) == value for key, value in self._filters.items())
        ]
        return _Result(matched)


class FakeClient:
    """supabase-py의 client.table(name).insert(row).execute() 모양을 흉내낸다."""

    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def insert(self, row):
        self._store.setdefault(self._name, []).append(dict(row))
        return _Query([row])

    def select(self, _columns="*"):
        return _Query(self._store.get(self._name, []))


def test_registers_a_new_as_of_as_run_raw_objects_release_and_release_objects(tmp_path):
    put_raw(tmp_path)
    client = FakeClient()

    release_id = register_release(tmp_path, AS_OF, client=client)

    assert len(client.store["common_ingest_run"]) == 1
    run = client.store["common_ingest_run"][0]
    assert run["dataset"] == DATASET

    raw_objects = client.store["common_raw_object"]
    assert len(raw_objects) == 2
    assert {obj["run_id"] for obj in raw_objects} == {run["run_id"]}
    structure_sha = hashlib.sha256(b'{"fake": "structure"}').hexdigest()
    xml_sha = hashlib.sha256(b"<PART>fake</PART>").hexdigest()
    assert {obj["sha256"] for obj in raw_objects} == {structure_sha, xml_sha}

    releases = client.store["common_dataset_release"]
    assert len(releases) == 1
    release = releases[0]
    assert release["release_id"] == release_id
    assert release["dataset"] == DATASET
    assert release["scope_key"] == SCOPE_KEY
    assert release["status"] == "staging"
    assert release["run_id"] == run["run_id"]
    expected_hash = hashlib.sha256(f"{structure_sha}:{xml_sha}".encode()).hexdigest()
    assert release["manifest_hash"] == expected_hash

    release_objects = client.store["common_release_object"]
    assert len(release_objects) == 2
    assert {obj["release_id"] for obj in release_objects} == {release_id}
    assert {obj["object_id"] for obj in release_objects} == {obj["object_id"] for obj in raw_objects}
    assert {obj["role"] for obj in release_objects} == {"structure", "xml"}


def test_reuses_existing_release_id_without_creating_duplicate_rows(tmp_path):
    put_raw(tmp_path)
    client = FakeClient()

    first_id = register_release(tmp_path, AS_OF, client=client)
    second_id = register_release(tmp_path, AS_OF, client=client)

    assert second_id == first_id
    assert len(client.store["common_ingest_run"]) == 1
    assert len(client.store["common_raw_object"]) == 2
    assert len(client.store["common_dataset_release"]) == 1
    assert len(client.store["common_release_object"]) == 2
