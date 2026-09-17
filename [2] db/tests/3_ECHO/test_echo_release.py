"""SUU-122: 파싱된 ECHO 묶음 하나(as_of)를 Supabase common_* 테이블에 release로 등록한다.

실제 Supabase에는 붙지 않는다. supabase-py 모양(``client.table(name).insert(row).execute()``,
``.select(...).eq(...).execute()``)의 가짜 client를 주입해 어떤 행이 만들어지는지만 본다 (SUU-65와 같은 방식).
"""
import hashlib
import json

from echo_release import DATASET, PARSER_VERSION, SCOPE_KEY, register_release

AS_OF = "2026-09-17"
ICIS_SHA = "a" * 64
PIPELINE_SHA = "b" * 64


def put_manifest(root):
    """SUU-98(echo_raw.store_raw)이 남기는 raw/{as_of}/manifest.json 모양 그대로 (실제 2026-09-17 값 축약)."""
    entries = []
    for name, sha, size, modified in (
        ("ICIS-AIR_downloads.zip", ICIS_SHA, 70168265, "Sun, 13 Sep 2026 02:10:24 GMT"),
        ("pipeline_caa_downloads.zip", PIPELINE_SHA, 5332282, "Sun, 13 Sep 2026 06:12:06 GMT"),
    ):
        entries.append({
            "name": name, "path": f"raw/{AS_OF}/{sha}/{name}",
            "source_url": f"https://echo.epa.gov/files/echodownloads/{name}",
            "final_url": f"https://echo.epa.gov/files/echodownloads/{name}",
            "http_status": 200, "media_type": "application/zip", "etag": f'"{sha[:7]}"',
            "last_modified": modified, "sha256": sha, "byte_size": size,
            "fetched_at": "2026-09-17T06:06:19.356430+00:00",
            "members": [{"name": "x.csv", "row_count": 1}],
        })
    path = root / "raw" / AS_OF / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(entries), encoding="utf-8")


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
        return _Result([r for r in self._rows if all(r.get(k) == v for k, v in self._filters.items())])


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def insert(self, row):
        self._store.setdefault(self._name, []).append(dict(row))
        return _Query([row])

    def select(self, _columns="*"):
        return _Query(self._store.get(self._name, []))


class FakeClient:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


def test_registers_run_two_raw_objects_one_release_and_two_release_objects(tmp_path):
    put_manifest(tmp_path)
    client = FakeClient()

    release_id = register_release(tmp_path, AS_OF, client=client)

    runs = client.store["common_ingest_run"]
    assert len(runs) == 1 and runs[0]["dataset"] == DATASET and runs[0]["status"] == "succeeded"

    raw_objects = client.store["common_raw_object"]
    assert len(raw_objects) == 2
    assert {o["run_id"] for o in raw_objects} == {runs[0]["run_id"]}
    assert {o["sha256"] for o in raw_objects} == {ICIS_SHA, PIPELINE_SHA}
    by_sha = {o["sha256"]: o for o in raw_objects}
    assert by_sha[ICIS_SHA]["storage_uri"] == f"raw/{AS_OF}/{ICIS_SHA}/ICIS-AIR_downloads.zip"
    assert by_sha[ICIS_SHA]["byte_size"] == 70168265
    assert by_sha[ICIS_SHA]["source_modified_at"] == "2026-09-13T02:10:24+00:00"  # HTTP 날짜 → ISO

    releases = client.store["common_dataset_release"]
    assert len(releases) == 1
    release = releases[0]
    assert release["release_id"] == release_id
    assert (release["dataset"], release["scope_key"]) == (DATASET, SCOPE_KEY) == ("echo", "icis_air_national+caa_pipeline")
    assert release["status"] == "staging" and release["published_at"] is None
    assert release["source_as_of"] == AS_OF
    assert release["parser_version"] == PARSER_VERSION
    assert release["manifest_hash"] == hashlib.sha256(f"{ICIS_SHA}:{PIPELINE_SHA}".encode()).hexdigest()

    release_objects = client.store["common_release_object"]
    assert len(release_objects) == 2
    assert {o["release_id"] for o in release_objects} == {release_id}
    assert {(o["role"], o["object_id"]) for o in release_objects} == {
        ("icis_air", by_sha[ICIS_SHA]["object_id"]), ("pipeline", by_sha[PIPELINE_SHA]["object_id"]),
    }


def test_reuses_existing_release_id_without_creating_duplicate_rows(tmp_path):
    put_manifest(tmp_path)
    client = FakeClient()

    first_id = register_release(tmp_path, AS_OF, client=client)
    second_id = register_release(tmp_path, AS_OF, client=client)

    assert second_id == first_id
    assert len(client.store["common_ingest_run"]) == 1
    assert len(client.store["common_raw_object"]) == 2
    assert len(client.store["common_dataset_release"]) == 1
    assert len(client.store["common_release_object"]) == 2
