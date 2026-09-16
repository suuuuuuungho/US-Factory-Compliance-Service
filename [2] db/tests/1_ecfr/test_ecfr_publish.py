"""SUU-67: 다 적재된 release를 공개 포인터(common_dataset_current)로 전환한다.

실제 Supabase에는 붙지 않는다. supabase-py와 같은 모양(``.update(data).eq(...).execute()``,
``.upsert(rows, on_conflict=...).execute()``, ``.select(...).eq(...).execute()``)의
가짜 client를 주입해서 어떤 행이 바뀌는지만 확인한다.
"""
from ecfr_publish import publish_release

RELEASE_1 = "11111111-1111-1111-1111-111111111111"
RELEASE_2 = "22222222-2222-2222-2222-222222222222"
DATASET = "ecfr"
SCOPE_KEY = "40/63"


class _Result:
    def __init__(self, data):
        self.data = data


class _SelectQuery:
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


class _UpdateQuery:
    def __init__(self, rows, data):
        self._rows = rows
        self._data = data
        self._filters: dict = {}

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def execute(self):
        matched = [
            row for row in self._rows
            if all(row.get(key) == value for key, value in self._filters.items())
        ]
        for row in matched:
            row.update(self._data)
        return _Result(matched)


class FakeClient:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def _rows(self):
        return self._store.setdefault(self._name, [])

    def select(self, _columns="*"):
        return _SelectQuery(list(self._rows()))

    def update(self, data):
        return _UpdateQuery(self._rows(), data)

    def upsert(self, rows, on_conflict=None):
        columns = [c.strip() for c in (on_conflict or "").split(",") if c.strip()]
        rows_list = rows if isinstance(rows, list) else [rows]
        existing = self._rows()
        for row in rows_list:
            key = tuple(row.get(c) for c in columns)
            existing[:] = [r for r in existing if tuple(r.get(c) for c in columns) != key]
            existing.append(dict(row))
        return _SelectQuery(list(rows_list))


def make_client_with_staging_release(release_id, source_as_of="2026-09-10"):
    client = FakeClient()
    client.store["common_dataset_release"] = [
        {
            "release_id": release_id,
            "dataset": DATASET,
            "scope_key": SCOPE_KEY,
            "source_as_of": source_as_of,
            "status": "staging",
            "published_at": None,
        }
    ]
    return client


def test_publishing_sets_release_status_and_published_at():
    client = make_client_with_staging_release(RELEASE_1)

    publish_release(RELEASE_1, client=client)

    release = client.store["common_dataset_release"][0]
    assert release["status"] == "published"
    assert release["published_at"] is not None


def test_publishing_points_common_dataset_current_to_the_release():
    client = make_client_with_staging_release(RELEASE_1)

    publish_release(RELEASE_1, client=client)

    pointers = client.store["common_dataset_current"]
    assert len(pointers) == 1
    assert pointers[0]["dataset"] == DATASET
    assert pointers[0]["scope_key"] == SCOPE_KEY
    assert pointers[0]["release_id"] == RELEASE_1
    assert pointers[0]["latest_source_as_of"] == "2026-09-10"


def test_publishing_a_new_release_replaces_the_pointer_but_keeps_old_release_row():
    client = make_client_with_staging_release(RELEASE_1)
    publish_release(RELEASE_1, client=client)
    client.store["common_dataset_release"].append(
        {
            "release_id": RELEASE_2,
            "dataset": DATASET,
            "scope_key": SCOPE_KEY,
            "source_as_of": "2026-10-01",
            "status": "staging",
            "published_at": None,
        }
    )

    publish_release(RELEASE_2, client=client)

    pointers = client.store["common_dataset_current"]
    assert len(pointers) == 1
    assert pointers[0]["release_id"] == RELEASE_2

    releases_by_id = {row["release_id"]: row for row in client.store["common_dataset_release"]}
    assert releases_by_id[RELEASE_1]["status"] == "published"
    assert releases_by_id[RELEASE_2]["status"] == "published"
