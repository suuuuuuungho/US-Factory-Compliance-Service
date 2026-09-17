"""SUU-125: 검증된 ECHO release를 공개 포인터(common_dataset_current)로 전환한다.

SUU-67의 ``ecfr_publish.publish_release``는 dataset/scope_key를 release 행에서 읽으므로 ECHO에도 그대로
쓴다 — 새 모듈을 만들지 않는다. 이 테스트는 그 함수가 echo release(dataset "echo", scope
"icis_air_national+caa_pipeline")에서도 맞게 동작하는지만 본다. 가짜 client는 SUU-67 테스트와 같은 모양.
"""
from ecfr_publish import publish_release
from echo_release import DATASET, SCOPE_KEY

RELEASE_1 = "11111111-1111-1111-1111-111111111111"
RELEASE_2 = "22222222-2222-2222-2222-222222222222"


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, data=None):
        self._rows, self._data, self._filters = rows, data, {}

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def select(self, _columns="*"):
        return self

    def execute(self):
        matched = [r for r in self._rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._data is not None:
            for row in matched:
                row.update(self._data)
        return _Result(matched)


class _Table:
    def __init__(self, store, name):
        self._rows = store.setdefault(name, [])

    def select(self, _columns="*"):
        return _Query(self._rows)

    def update(self, data):
        return _Query(self._rows, data)

    def upsert(self, row, on_conflict=None):
        key_cols = [c.strip() for c in on_conflict.split(",")]
        key = tuple(row[c] for c in key_cols)
        self._rows[:] = [r for r in self._rows if tuple(r[c] for c in key_cols) != key]
        self._rows.append(dict(row))
        return _Query([row])


class FakeClient:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


def staging(client, release_id, as_of):
    client.store.setdefault("common_dataset_release", []).append({
        "release_id": release_id, "dataset": DATASET, "scope_key": SCOPE_KEY,
        "source_as_of": as_of, "status": "staging", "published_at": None,
    })


def test_publishing_sets_status_published_and_published_at():
    client = FakeClient()
    staging(client, RELEASE_1, "2026-09-17")

    publish_release(RELEASE_1, client=client)

    release = client.store["common_dataset_release"][0]
    assert release["status"] == "published" and release["published_at"] is not None


def test_pointer_targets_the_echo_release_and_old_release_row_survives_republish():
    client = FakeClient()
    staging(client, RELEASE_1, "2026-09-17")
    publish_release(RELEASE_1, client=client)
    staging(client, RELEASE_2, "2026-09-24")

    publish_release(RELEASE_2, client=client)

    pointers = client.store["common_dataset_current"]
    assert pointers == [{
        "dataset": "echo", "scope_key": "icis_air_national+caa_pipeline", "release_id": RELEASE_2,
        "last_checked_at": pointers[0]["last_checked_at"], "latest_source_as_of": "2026-09-24",
    }]
    releases = {r["release_id"]: r["status"] for r in client.store["common_dataset_release"]}
    assert releases == {RELEASE_1: "published", RELEASE_2: "published"}  # 이전 release 행은 남는다
