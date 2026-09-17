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


# ---------------------------------------------------------------------------
# SUU-84: 임계값(max_chars)을 넘는 본문 청크만 label_path 경계로 쪼갠다.
# 글자 수 계산은 select_subpart_chunks(SUU-76)와 같은 "\n\n".join(text_content) 기준.
# 가짜 nodes/blocks를 직접 만들어 크기를 통제한다(fixture XML엔 큰 조문이 없다).
# ---------------------------------------------------------------------------
BIG_KEY = "40/63/subpart-Z/section-63.9999"
BIG_NODE = [{"node_key": BIG_KEY, "node_type": "section", "reserved": False}]


def _block(block_no, label_path, kind="paragraph", text=None):
    return {
        "node_key": BIG_KEY,
        "block_no": block_no,
        "kind": kind,
        "label_path": label_path,
        "text_content": text if text is not None else f"[{block_no}]" + "x" * 47,  # 50자
    }


def _body_chunks(chunks):
    return [c for c in chunks if c["node_key"] == BIG_KEY and c["parent_chunk_key"] is None]


def _chunk_len(chunk, blocks):
    text_by_no = {b["block_no"]: b["text_content"] for b in blocks}
    return len("\n\n".join(text_by_no[n] for n in chunk["block_nos"]))


def test_max_chunk_chars_constant_is_thirty_thousand():
    from ecfr_chunks import MAX_CHUNK_CHARS

    assert MAX_CHUNK_CHARS == 30_000


def test_section_over_limit_is_split_at_top_level_label_boundaries():
    blocks = [
        _block(1, []),          # 앞머리(label 없음)
        _block(2, ["a"]),
        _block(3, ["a", "1"]),
        _block(4, ["b"]),
        _block(5, ["b", "1"]),
        _block(6, ["c"]),
    ]  # 전체 6*50 + 5*2 = 310자

    chunks = build_chunks(BIG_NODE, blocks, max_chars=200)

    body = _body_chunks(chunks)
    assert [c["block_nos"] for c in body] == [[1, 2, 3], [4, 5], [6]]
    assert [c["chunk_key"] for c in body] == [
        f"ecfr/{BIG_KEY}/0", f"ecfr/{BIG_KEY}/0-1", f"ecfr/{BIG_KEY}/0-2",
    ]
    assert all(_chunk_len(c, blocks) <= 200 for c in body)
    assert all(c["parent_chunk_key"] is None for c in body)


def test_recurses_to_deeper_label_level_when_top_level_group_is_still_too_large():
    blocks = [
        _block(1, ["a"]),
        _block(2, ["a", "1"]),
        _block(3, ["a", "2"]),
        _block(4, ["b"]),
    ]

    chunks = build_chunks(BIG_NODE, blocks, max_chars=120)

    body = _body_chunks(chunks)
    # (a) 묶음 [1,2,3]=154자 > 120 → (a)(1),(a)(2)로 다시 나눔. (a) 본문(1)은 첫 조각에
    assert [c["block_nos"] for c in body] == [[1, 2], [3], [4]]
    assert all(_chunk_len(c, blocks) <= 120 for c in body)


def test_leading_unlabeled_blocks_go_to_first_piece_and_block_order_is_kept():
    blocks = [
        _block(1, []),
        _block(2, []),
        _block(3, ["a"]),
        _block(4, ["a"], kind="heading"),   # label_path는 상속(inherited)
        _block(5, ["b"]),
        _block(6, ["b"], kind="note"),
    ]

    chunks = build_chunks(BIG_NODE, blocks, max_chars=210)

    body = _body_chunks(chunks)
    assert body[0]["block_nos"][:2] == [1, 2]
    flat = [n for c in body for n in c["block_nos"]]
    assert flat == [1, 2, 3, 4, 5, 6]
    assert [c["block_nos"] for c in body] == [[1, 2, 3, 4], [5, 6]]


def test_single_block_over_limit_is_kept_whole_not_truncated():
    blocks = [_block(1, ["a"], text="y" * 300), _block(2, ["b"])]

    chunks = build_chunks(BIG_NODE, blocks, max_chars=100)

    body = _body_chunks(chunks)
    assert [c["block_nos"] for c in body] == [[1], [2]]


def test_section_within_limit_is_unchanged_single_chunk():
    blocks = [_block(1, []), _block(2, ["a"]), _block(3, ["b"])]

    chunks = build_chunks(BIG_NODE, blocks, max_chars=1_000)

    body = _body_chunks(chunks)
    assert len(body) == 1
    assert body[0]["chunk_key"] == f"ecfr/{BIG_KEY}/0"
    assert body[0]["block_nos"] == [1, 2, 3]
    assert build_chunks(BIG_NODE, blocks) == chunks  # 기본값(30,000자)도 같은 결과


def test_table_chunks_of_split_section_still_point_to_first_piece():
    blocks = [
        _block(1, ["a"]),
        _block(2, ["a"], kind="table"),
        _block(3, ["b"]),
        _block(4, ["c"]),
    ]

    chunks = build_chunks(BIG_NODE, blocks, max_chars=60)

    body = _body_chunks(chunks)
    assert [c["chunk_key"] for c in body] == [
        f"ecfr/{BIG_KEY}/0", f"ecfr/{BIG_KEY}/0-1", f"ecfr/{BIG_KEY}/0-2",
    ]
    table = [c for c in chunks if c["parent_chunk_key"] is not None]
    assert len(table) == 1
    assert table[0]["chunk_key"] == f"ecfr/{BIG_KEY}/1"
    assert table[0]["block_nos"] == [2]
    assert table[0]["parent_chunk_key"] == f"ecfr/{BIG_KEY}/0"


def test_fixture_sections_are_all_under_default_limit_so_output_is_unchanged(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)

    chunks = build_chunks(nodes, blocks)

    assert all("-" not in c["chunk_key"].rsplit("/", 1)[1] for c in chunks)
