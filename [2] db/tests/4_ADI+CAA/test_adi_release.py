"""SUU-224: raw/ 원본(목록 HTML 2 + 회신 PDF) 전부를 common_raw_object 에 넣고 adi release 하나로 묶는다.

fr_release(SUU-209)와 같은 틀. raw_as_of 는 parsed/{as_of}/quality_report.json 에서 읽고,
`root/**/raw/{raw_as_of}/manifest.json` 의 모든 항목이 대상이다. role: .html → list, .pdf → letter.
같은 파일이 두 목록에 실리면(같은 sha256, 다른 URL) raw_object 는 (source_url, sha256)마다 하나다.
"""
from __future__ import annotations

import uuid

from adi_release import DATASET, PARSER_VERSION, SCOPE_KEY, register_release


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, rows=None):
        self.table, self.rows, self.filters, self.in_filters = table, rows, {}, {}

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def in_(self, column, values):
        self.in_filters[column] = list(values)
        return self

    def select(self, _columns="*"):
        return self

    def execute(self):
        if self.rows is not None:
            self.table.inserts.append(self.rows)
            self.table.rows.extend(self.rows)
            return _Result(self.rows)
        return _Result([r for r in self.table.rows
                        if all(r.get(k) == v for k, v in self.filters.items())
                        and all(r.get(k) in v for k, v in self.in_filters.items())])


class _Table:
    def __init__(self):
        self.rows: list[dict] = []
        self.inserts: list[list[dict]] = []

    def select(self, _columns="*"):
        return _Query(self)

    def insert(self, rows):
        return _Query(self, [dict(r) for r in (rows if isinstance(rows, list) else [rows])])


class FakeClient:
    def __init__(self):
        self.tables: dict[str, _Table] = {}

    def table(self, name):
        return self.tables.setdefault(name, _Table())


def test_registers_run_every_raw_file_one_release_and_release_objects(adi):
    client = FakeClient()

    release_id = register_release(adi.root, adi.as_of, client=client)

    assert (DATASET, SCOPE_KEY, PARSER_VERSION) == ("adi", "adi+caa_dashboard", "1")
    runs = client.table("common_ingest_run").rows
    assert len(runs) == 1 and runs[0]["dataset"] == "adi" and runs[0]["status"] == "succeeded"
    assert runs[0]["scope"]["as_of"] == adi.as_of and runs[0]["scope"]["raw_as_of"] == "2026-09-17"

    objects = client.table("common_raw_object").rows
    assert {(o["source_url"], o["sha256"]) for o in objects} == set(adi.objects.values())
    assert len(objects) == 6  # 같은 파일(1800013.pdf == King PDF)도 URL 이 다르면 원본 2개
    assert all(o["run_id"] == runs[0]["run_id"] and o["storage_uri"] and o["byte_size"] and o["fetched_at"] for o in objects)
    by_sha = {o["sha256"]: o for o in objects}
    assert by_sha[adi.objects["M170010"][1]]["storage_uri"].startswith("adi_letters/shard_1/raw/2026-09-17/")
    assert by_sha[adi.objects["adi_list"][1]]["storage_uri"].startswith("raw/2026-09-17/")

    releases = client.table("common_dataset_release").rows
    assert len(releases) == 1 and releases[0]["release_id"] == release_id
    assert (releases[0]["dataset"], releases[0]["scope_key"], releases[0]["parser_version"]) == ("adi", "adi+caa_dashboard", "1")
    assert releases[0]["status"] == "staging" and releases[0]["source_as_of"] == adi.as_of and releases[0]["published_at"] is None
    assert releases[0]["run_id"] == runs[0]["run_id"]
    uuid.UUID(release_id)

    links = client.table("common_release_object").rows
    assert len(links) == 6 and {l["release_id"] for l in links} == {release_id}
    sha_by_id = {o["object_id"]: o["sha256"] for o in objects}
    roles = {sha_by_id[l["object_id"]]: l["role"] for l in links}
    assert roles[adi.objects["adi_list"][1]] == "list" and roles[adi.objects["dashboard_list"][1]] == "list"
    assert roles[adi.objects["M170010"][1]] == "letter" and roles[adi.objects["westvaco"][1]] == "letter"


def test_raw_and_release_objects_are_inserted_in_batches_not_one_by_one(adi):
    client = FakeClient()

    register_release(adi.root, adi.as_of, client=client)

    assert [len(batch) for batch in client.table("common_raw_object").inserts] == [6]
    assert [len(batch) for batch in client.table("common_release_object").inserts] == [6]


def test_same_manifest_hash_twice_makes_one_release(adi):
    client = FakeClient()

    first = register_release(adi.root, adi.as_of, client=client)
    second = register_release(adi.root, adi.as_of, client=client)

    assert first == second
    assert len(client.table("common_dataset_release").rows) == 1
    assert len(client.table("common_ingest_run").rows) == 1
    assert len(client.table("common_raw_object").rows) == 6
    assert len(client.table("common_release_object").rows) == 6


def test_next_release_reuses_raw_objects_already_registered(adi):
    """다음 as_of 에도 같은 PDF 를 다시 쓴다. (source_url, sha256) 가 이미 있으면 그 object_id 를 재사용한다."""
    client = FakeClient()
    known = client.table("common_raw_object")
    old_id = str(uuid.uuid4())
    known.rows.append({"object_id": old_id, "source_url": adi.objects["M170010"][0], "sha256": adi.objects["M170010"][1]})

    release_id = register_release(adi.root, adi.as_of, client=client)

    assert len(known.rows) == 6  # 5개만 새로 넣었다
    assert [len(batch) for batch in known.inserts] == [5]
    links = {l["object_id"] for l in client.table("common_release_object").rows if l["release_id"] == release_id}
    assert old_id in links and len(links) == 6


def test_same_file_in_two_manifests_is_one_raw_object_and_one_link(adi):
    """SUU-225: 같은 파일이 (같은 URL·sha256으로) manifest 두 곳에 있어도 raw_object 1개, release_object 1개."""
    from datetime import date
    from ecfr_raw import save_raw

    url, _ = adi.objects["M170010"]
    body = next((adi.root / "adi_letters" / "shard_1").glob("raw/2026-09-17/*/M170010.pdf")).read_bytes()
    save_raw(adi.root / "adi_letters", date(2026, 9, 17), "M170010.pdf", body, source_url=url, final_url=url, http_status=200, media_type="application/pdf")
    client = FakeClient()

    release_id = register_release(adi.root, adi.as_of, client=client)

    assert len(client.table("common_raw_object").rows) == 6
    links = [l for l in client.table("common_release_object").rows if l["release_id"] == release_id]
    assert len(links) == 6 and len({l["object_id"] for l in links}) == 6
