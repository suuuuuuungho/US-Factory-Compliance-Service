"""SUU-70: ecfr_node/ecfr_block을 RAG 청크(list[dict])로 나눈다.

fixture XML을 진짜 파서(ecfr_parse.parse_release)로 돌려서 만든 실제
nodes.jsonl/blocks.jsonl을 입력으로 쓴다. `40/63/subpart-G/section-63.110`는
block_no 5가 표(table)이고 나머지 12개는 본문이라서, "표는 분리, 나머지는 그대로"를
확인하기 좋은 실제 사례로 쓴다(계획 문서 원칙 [3]).
"""
import json
from datetime import date
from pathlib import Path

from ecfr_chunks import build_chunks
from ecfr_parse import PARSER_VERSION, parse_release
from ecfr_raw import save_raw

FIXTURES = Path(__file__).parent.parent / "1_ecfr" / "fixtures"
XML = (FIXTURES / "ecfr_part63_sample.xml").read_bytes()
STRUCTURE = (FIXTURES / "ecfr_structure_sample.json").read_bytes()
AS_OF = "2026-09-10"
TABLE_SECTION_KEY = "40/63/subpart-G/section-63.110"


def put_raw(root):
    for name, body, media in (
        ("title-40-structure.json", STRUCTURE, "application/json"),
        ("title-40-part-63.xml", XML, "application/xml"),
    ):
        save_raw(
            root, date.fromisoformat(AS_OF), name, body,
            source_url=f"https://example.test/{name}", final_url=f"https://example.test/{name}",
            http_status=200, media_type=media,
        )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def parsed_nodes_and_blocks(tmp_path):
    put_raw(tmp_path)
    parse_release(tmp_path, AS_OF)
    out = tmp_path / "parsed" / AS_OF / PARSER_VERSION
    return read_jsonl(out / "nodes.jsonl"), read_jsonl(out / "blocks.jsonl")


def test_creates_one_base_chunk_per_non_reserved_section_or_appendix(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)

    chunks = build_chunks(nodes, blocks)

    base_chunks = [c for c in chunks if c["parent_chunk_key"] is None]
    expected_node_keys = {
        node["node_key"] for node in nodes
        if node["node_type"] in ("section", "appendix") and not node["reserved"]
    }
    assert {c["node_key"] for c in base_chunks} == expected_node_keys
    assert len(base_chunks) == len(expected_node_keys)


def test_excludes_reserved_nodes_entirely(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    reserved_keys = {node["node_key"] for node in nodes if node["reserved"]}

    chunks = build_chunks(nodes, blocks)

    assert not any(c["node_key"] in reserved_keys for c in chunks)


def test_splits_table_blocks_into_separate_chunks_linked_to_their_parent(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    table_blocks = [b for b in blocks if b["kind"] == "table"]

    chunks = build_chunks(nodes, blocks)

    table_chunks = [c for c in chunks if c["parent_chunk_key"] is not None]
    assert len(table_chunks) == len(table_blocks)

    base_by_node = {c["node_key"]: c for c in chunks if c["parent_chunk_key"] is None}
    for table_block, chunk in zip(table_blocks, table_chunks):
        assert chunk["node_key"] == table_block["node_key"]
        assert chunk["block_nos"] == [table_block["block_no"]]
        assert chunk["parent_chunk_key"] == base_by_node[table_block["node_key"]]["chunk_key"]


def test_table_section_body_chunk_excludes_the_table_block_number(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    section_blocks = [b for b in blocks if b["node_key"] == TABLE_SECTION_KEY]
    table_block_no = next(b["block_no"] for b in section_blocks if b["kind"] == "table")
    all_block_nos = sorted(b["block_no"] for b in section_blocks)

    chunks = build_chunks(nodes, blocks)

    body_chunk = next(
        c for c in chunks
        if c["node_key"] == TABLE_SECTION_KEY and c["parent_chunk_key"] is None
    )
    assert table_block_no not in body_chunk["block_nos"]
    assert body_chunk["block_nos"] == [n for n in all_block_nos if n != table_block_no]
    assert body_chunk["chunk_key"] == f"ecfr/{TABLE_SECTION_KEY}/0"
