"""SUU-209: raw/ 아래 원본 전부(상세 JSON·XML·PDF)를 common_* 테이블에 release 하나로 등록한다.

실제 Supabase 없음. supabase-py 모양의 가짜 client (SUU-65·122 방식). FR은 eCFR·ECHO와 달리
원본이 문서 폴더 1,532개에 흩어져 있고, 다음 as_of 에도 같은 파일을 다시 쓴다 → 묶음 insert,
이미 있는 (source_url, sha256) 는 재사용.
"""
import hashlib

from fr_fetch import Fetched, detail_url
from fr_raw import store_raw
from fr_release import DATASET, PARSER_VERSION, SCOPE_KEY, register_release


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows, self._filters, self._in = rows, {}, {}

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def in_(self, column, values):
        self._in[column] = set(values)
        return self

    def select(self, _columns="*"):
        return self

    def execute(self):
        return _Result([
            r for r in self._rows
            if all(r.get(k) == v for k, v in self._filters.items())
            and all(r.get(k) in v for k, v in self._in.items())
        ])


class _Table:
    def __init__(self, store, calls, name):
        self._store, self._calls, self._name = store, calls, name

    def insert(self, rows):
        rows = rows if isinstance(rows, list) else [rows]
        self._calls.append((self._name, len(rows)))
        if self._name == "common_raw_object":
            existing = {(r["source_url"], r["sha256"]) for r in self._store.get(self._name, [])}
            for r in rows:
                assert (r["source_url"], r["sha256"]) not in existing, "unique (source_url, sha256) violated"
        self._store.setdefault(self._name, []).extend(dict(r) for r in rows)
        return _Query(rows)

    def select(self, _columns="*"):
        return _Query(self._store.get(self._name, []))


class FakeClient:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}
        self.inserts: list[tuple[str, int]] = []  # (table, 한 번에 넣은 행 수)

    def table(self, name):
        return _Table(self.store, self.inserts, name)


def _all_shas(fr):
    return sorted(sha for kinds in fr.objects.values() for _, sha in kinds.values())


def test_registers_run_every_raw_file_one_release_and_release_objects(fr):
    client = FakeClient()

    release_id = register_release(fr.root, fr.as_of, client=client)

    runs = client.store["common_ingest_run"]
    assert len(runs) == 1 and runs[0]["dataset"] == "fr" and runs[0]["status"] == "succeeded"

    raw_objects = client.store["common_raw_object"]
    assert len(raw_objects) == 8  # 3 detail + 2 xml + 3 pdf
    assert {o["run_id"] for o in raw_objects} == {runs[0]["run_id"]}
    assert sorted(o["sha256"] for o in raw_objects) == _all_shas(fr)
    src_url, detail_sha = fr.objects[("2026-02-24", "2026-03638")]["detail"]
    detail = next(o for o in raw_objects if o["sha256"] == detail_sha)
    assert detail["source_url"] == src_url
    assert detail["storage_uri"] == f"raw/2026/2026-02-24_2026-03638/{detail_sha}/2026-03638.json"
    assert detail["fetched_at"]

    releases = client.store["common_dataset_release"]
    assert len(releases) == 1
    release = releases[0]
    assert release["release_id"] == release_id
    assert (release["dataset"], release["scope_key"]) == (DATASET, SCOPE_KEY) == ("fr", "part63_metadata")
    assert release["status"] == "staging" and release["published_at"] is None
    assert release["source_as_of"] == fr.as_of
    assert release["parser_version"] == PARSER_VERSION
    assert release["manifest_hash"] == hashlib.sha256(":".join(_all_shas(fr)).encode()).hexdigest()

    release_objects = client.store["common_release_object"]
    assert len(release_objects) == 8
    assert {o["release_id"] for o in release_objects} == {release_id}
    by_id = {o["object_id"]: o["sha256"] for o in raw_objects}
    roles = {by_id[o["object_id"]]: o["role"] for o in release_objects}
    for kinds in fr.objects.values():
        for kind, (_, sha) in kinds.items():
            assert roles[sha] == kind  # role = detail / xml / pdf


def test_raw_and_release_objects_are_inserted_in_batches_not_one_by_one(fr):
    client = FakeClient()

    register_release(fr.root, fr.as_of, client=client)

    assert [n for t, n in client.inserts if t == "common_raw_object"] == [8]  # 1,532건 × 3 을 한 줄씩 넣지 않는다
    assert [n for t, n in client.inserts if t == "common_release_object"] == [8]


def test_same_manifest_hash_twice_makes_one_release(fr):
    client = FakeClient()

    first = register_release(fr.root, fr.as_of, client=client)
    second = register_release(fr.root, fr.as_of, client=client)

    assert second == first
    assert len(client.store["common_ingest_run"]) == 1
    assert len(client.store["common_raw_object"]) == 8
    assert len(client.store["common_dataset_release"]) == 1
    assert len(client.store["common_release_object"]) == 8


def test_next_release_reuses_raw_objects_already_registered(fr):
    """다음 수집에서 문서가 하나 늘면 새 release 지만, 이미 있는 원본 8개는 다시 넣지 않는다 (unique source_url+sha256)."""
    client = FakeClient()
    first = register_release(fr.root, fr.as_of, client=client)
    first_ids = {o["object_id"] for o in client.store["common_raw_object"]}
    # 새 문서 하나(상세만): 2026-03638 상세의 번호만 바꾼 것
    old = next((fr.root / "raw" / "2026" / "2026-02-24_2026-03638").glob("*/2026-03638.json")).read_bytes()
    new_detail = old.replace(b'"2026-03638"', b'"2026-09999"')
    url = detail_url("2026-09999", "2026-09-01")
    store_raw(fr.root, "2026-09-01", "2026-09999", Fetched(new_detail, url, url, 200, "", len(new_detail), hashlib.sha256(new_detail).hexdigest()), kind="detail")

    second = register_release(fr.root, fr.as_of, client=client)

    assert second != first
    assert len(client.store["common_dataset_release"]) == 2
    raw_objects = client.store["common_raw_object"]
    assert len(raw_objects) == 9  # 8 재사용 + 1 새로
    assert first_ids <= {o["object_id"] for o in raw_objects}
    second_objects = [o for o in client.store["common_release_object"] if o["release_id"] == second]
    assert len(second_objects) == 9  # 새 release 는 기존 8개 + 새 1개를 모두 가리킨다
    assert first_ids <= {o["object_id"] for o in second_objects}
