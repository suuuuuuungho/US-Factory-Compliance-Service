"""SUU-66: parsed/{as_of}/{parser_version}/nodes.jsonl·blocks.jsonl을 ecfr_node·ecfr_block에 적재한다.

실제 Supabase에는 붙지 않는다. supabase-py와 같은 모양(``client.table(name)
.upsert(rows, on_conflict=...).execute()``, ``.select(...).eq(...).execute()``)의
가짜 client를 주입해서 어떤 행이 만들어지는지만 확인한다. nodes.jsonl/blocks.jsonl은
SUU-44의 진짜 파서(parse_release)로 fixture XML을 돌려서 만든다.
"""
import json
from datetime import date
from pathlib import Path

from ecfr_load import load_release
from ecfr_parse import PARSER_VERSION, parse_release
from ecfr_raw import save_raw

FIXTURES = Path(__file__).parent / "fixtures"
XML = (FIXTURES / "ecfr_part63_sample.xml").read_bytes()
STRUCTURE = (FIXTURES / "ecfr_structure_sample.json").read_bytes()
AS_OF = "2026-09-10"
RELEASE_ID = "11111111-1111-1111-1111-111111111111"
XML_OBJECT_ID = "22222222-2222-2222-2222-222222222222"


def put_raw(root):
    """1단계(ecfr_collect)가 남기는 모양 그대로 raw/{as_of}/manifest.json과 원본을 만든다."""
    for name, body, media in (
        ("title-40-structure.json", STRUCTURE, "application/json"),
        ("title-40-part-63.xml", XML, "application/xml"),
    ):
        save_raw(
            root, date.fromisoformat(AS_OF), name, body,
            source_url=f"https://example.test/{name}", final_url=f"https://example.test/{name}",
            http_status=200, media_type=media,
        )


def out_dir(root):
    return root / "parsed" / AS_OF / PARSER_VERSION


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


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
    """supabase-py의 .table(name).upsert(rows, on_conflict=...).execute() 모양을 흉내낸다."""

    def __init__(self):
        self.store: dict[str, list[dict]] = {}
        # SUU-77: upsert() 호출마다 몇 개의 행을 보냈는지 기록한다 (배치 크기 확인용)
        self.upsert_call_sizes: dict[str, list[int]] = {}

    def table(self, name):
        return _Table(self.store, self.upsert_call_sizes, name)


class _Table:
    def __init__(self, store, upsert_call_sizes, name):
        self._store = store
        self._upsert_call_sizes = upsert_call_sizes
        self._name = name

    def _rows(self):
        return self._store.setdefault(self._name, [])

    def insert(self, rows):
        rows_list = rows if isinstance(rows, list) else [rows]
        self._rows().extend(dict(row) for row in rows_list)
        return _Query(list(rows_list))

    def upsert(self, rows, on_conflict=None):
        columns = [c.strip() for c in (on_conflict or "").split(",") if c.strip()]
        rows_list = rows if isinstance(rows, list) else [rows]
        self._upsert_call_sizes.setdefault(self._name, []).append(len(rows_list))
        existing = self._rows()
        for row in rows_list:
            key = tuple(row.get(c) for c in columns)
            existing[:] = [r for r in existing if tuple(r.get(c) for c in columns) != key]
            existing.append(dict(row))
        return _Query(list(rows_list))

    def select(self, _columns="*"):
        return _Query(list(self._rows()))


def make_client_with_xml_object():
    client = FakeClient()
    client.store["common_release_object"] = [
        {"release_id": RELEASE_ID, "object_id": XML_OBJECT_ID, "role": "xml"},
    ]
    return client


def test_loads_every_node_row_into_ecfr_node_with_release_and_source_object_id(tmp_path):
    put_raw(tmp_path)
    parse_release(tmp_path, AS_OF)
    nodes = read_jsonl(out_dir(tmp_path) / "nodes.jsonl")
    client = make_client_with_xml_object()

    load_release(tmp_path, AS_OF, RELEASE_ID, client=client)

    loaded = client.store["ecfr_node"]
    assert len(loaded) == len(nodes)
    assert {row["node_key"] for row in loaded} == {node["node_key"] for node in nodes}
    assert all(row["release_id"] == RELEASE_ID for row in loaded)
    assert all(row["source_object_id"] == XML_OBJECT_ID for row in loaded)
    by_key = {row["node_key"]: row for row in loaded}
    for node in nodes:
        row = by_key[node["node_key"]]
        assert row["parent_key"] == node["parent_key"]
        assert row["node_type"] == node["node_type"]
        assert row["heading"] == node["heading"]
        assert row["content_hash"] == node["content_hash"]


def test_loads_every_block_row_into_ecfr_block_with_release_id(tmp_path):
    put_raw(tmp_path)
    parse_release(tmp_path, AS_OF)
    blocks = read_jsonl(out_dir(tmp_path) / "blocks.jsonl")
    client = make_client_with_xml_object()

    load_release(tmp_path, AS_OF, RELEASE_ID, client=client)

    loaded = client.store["ecfr_block"]
    assert len(loaded) == len(blocks)
    assert all(row["release_id"] == RELEASE_ID for row in loaded)
    by_key = {(row["node_key"], row["block_no"]): row for row in loaded}
    for block in blocks:
        row = by_key[(block["node_key"], block["block_no"])]
        assert row["kind"] == block["kind"]
        assert row["text_content"] == block["text_content"]
        assert row["parse_status"] == block["parse_status"]


def test_loading_the_same_release_twice_does_not_duplicate_rows(tmp_path):
    put_raw(tmp_path)
    parse_release(tmp_path, AS_OF)
    nodes = read_jsonl(out_dir(tmp_path) / "nodes.jsonl")
    blocks = read_jsonl(out_dir(tmp_path) / "blocks.jsonl")
    client = make_client_with_xml_object()

    load_release(tmp_path, AS_OF, RELEASE_ID, client=client)
    load_release(tmp_path, AS_OF, RELEASE_ID, client=client)

    assert len(client.store["ecfr_node"]) == len(nodes)
    assert len(client.store["ecfr_block"]) == len(blocks)


def make_synthetic_node(i):
    return {
        "node_key": f"40/63/subpart-A/section-63.{i}",
        "parent_key": "40/63/subpart-A",
        "node_type": "section",
        "identifier": f"63.{i}",
        "heading": f"Section {i}",
        "reserved": False,
        "sort_order": i,
        "source_locator": f"//section[{i}]",
        "xml_fragment": f"<section>{i}</section>",
        "content_hash": f"hash-{i}",
    }


def make_synthetic_block(i):
    return {
        "node_key": f"40/63/subpart-A/section-63.{i}",
        "block_no": 1,
        "kind": "paragraph",
        "label_path": ["(a)"],
        "text_content": f"Block text {i}",
        "markup": f"<p>{i}</p>",
        "source_locator": f"//section[{i}]/p",
        "parse_status": "ok",
    }


def write_synthetic_parsed_files(root, count):
    parsed_dir = out_dir(root)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    nodes = [make_synthetic_node(i) for i in range(count)]
    blocks = [make_synthetic_block(i) for i in range(count)]
    (parsed_dir / "nodes.jsonl").write_text(
        "\n".join(json.dumps(n) for n in nodes), encoding="utf-8"
    )
    (parsed_dir / "blocks.jsonl").write_text(
        "\n".join(json.dumps(b) for b in blocks), encoding="utf-8"
    )
    return nodes, blocks


def test_batches_large_upserts_to_avoid_statement_timeout(tmp_path):
    """SUU-77: 실제 Part 63 데이터는 block이 71,700개라 한 번에 upsert하면
    Postgres statement timeout이 난다(실측). 여러 번 나눠 보내야 한다."""
    count = 1200
    nodes, blocks = write_synthetic_parsed_files(tmp_path, count)
    client = make_client_with_xml_object()

    load_release(tmp_path, AS_OF, RELEASE_ID, client=client)

    node_calls = client.upsert_call_sizes["ecfr_node"]
    block_calls = client.upsert_call_sizes["ecfr_block"]

    assert len(node_calls) > 1, "node upsert가 한 번에 다 보내지고 있다"
    assert len(block_calls) > 1, "block upsert가 한 번에 다 보내지고 있다"
    assert max(node_calls) <= 1000
    assert max(block_calls) <= 1000
    assert sum(node_calls) == count
    assert sum(block_calls) == count
    assert len(client.store["ecfr_node"]) == count
    assert len(client.store["ecfr_block"]) == count
