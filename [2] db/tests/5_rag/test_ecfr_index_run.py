"""SUU-76: Subpart 하나를 실제로 색인해 검색해보는 실행 스크립트의 재료가 되는
두 순수 함수를 확인한다.

이 티켓의 진짜 완료 기준(실제 API로 색인, 컨텍스트 육안 확인, 벡터 검색 결과,
Artifact)은 사람이 실제로 실행해서 확인한다 — 여기서는 그 실행 스크립트가 쓰는
"Subpart 청크 뽑기"·"유사도로 정렬하기" 로직만 가짜 데이터 없이도(순수 함수라서)
검증한다.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from ecfr_chunks import build_chunks
from ecfr_index_run import (
    rank_chunks_by_similarity,
    select_subpart_chunks,
    subpart_heading_for,
)
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


def test_select_subpart_chunks_only_includes_that_subparts_chunks(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-G")

    assert chunks
    assert all(c["node_key"].startswith("40/63/subpart-G/") for c in chunks)
    all_chunks = build_chunks(nodes, blocks)
    expected = [c for c in all_chunks if c["node_key"].startswith("40/63/subpart-G/")]
    assert len(chunks) == len(expected)


def test_select_subpart_chunks_includes_nested_subject_group_sections(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-J")

    node_keys = {c["node_key"] for c in chunks}
    assert "40/63/subpart-J/subject-group-ECFRad8028a5975965e/section-63.210" in node_keys


def test_select_subpart_chunks_fills_chunk_text_from_block_text_content(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    blocks_by_key = {}
    for block in blocks:
        blocks_by_key.setdefault(block["node_key"], {})[block["block_no"]] = block["text_content"]

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-G")

    body_chunk = next(
        c for c in chunks
        if c["node_key"] == TABLE_SECTION_KEY and c["parent_chunk_key"] is None
    )
    body_text = "\n\n".join(
        blocks_by_key[TABLE_SECTION_KEY][no] for no in body_chunk["block_nos"]
    )
    heading = next(n["heading"] for n in nodes if n["node_key"] == TABLE_SECTION_KEY)
    assert body_chunk["chunk_text"] == f"{heading}\n\n{body_text}"


def test_select_subpart_chunks_prefixes_body_chunk_with_node_heading(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    heading_by_key = {n["node_key"]: n["heading"] for n in nodes}

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-G")

    body_chunks = [c for c in chunks if c["parent_chunk_key"] is None]
    assert body_chunks
    for chunk in body_chunks:
        heading = heading_by_key[chunk["node_key"]]
        assert heading
        assert chunk["chunk_text"].startswith(f"{heading}\n\n")


def test_select_subpart_chunks_prefixes_table_chunk_with_node_heading(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)
    table_only_node = (
        "40/63/subpart-XX/subject-group-ECFR3a9b3e27cd7a862"
        "/appendix-Table-1-to-Subpart-XX-of-Part-63"
    )
    heading = next(n["heading"] for n in nodes if n["node_key"] == table_only_node)
    assert heading

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-XX")

    table_chunks = [
        c for c in chunks
        if c["node_key"] == table_only_node and c["parent_chunk_key"] is not None
    ]
    assert table_chunks
    for chunk in table_chunks:
        assert chunk["chunk_text"].startswith(f"{heading}\n\n")
        assert chunk["chunk_text"][len(heading) + 2:].strip()


def test_select_subpart_chunks_drops_chunks_with_empty_chunk_text(tmp_path):
    nodes, blocks = parsed_nodes_and_blocks(tmp_path)

    chunks = select_subpart_chunks(nodes, blocks, "40/63/subpart-XX")

    assert all(c["chunk_text"].strip() for c in chunks)
    table_only_node = (
        "40/63/subpart-XX/subject-group-ECFR3a9b3e27cd7a862"
        "/appendix-Table-1-to-Subpart-XX-of-Part-63"
    )
    base_chunk_key = f"ecfr/{table_only_node}/0"
    assert base_chunk_key not in {c["chunk_key"] for c in chunks}


def test_subpart_heading_for_returns_subpart_node_heading_not_section_heading(tmp_path):
    nodes, _ = parsed_nodes_and_blocks(tmp_path)
    heading_by_key = {n["node_key"]: n["heading"] for n in nodes}
    section_g = "40/63/subpart-G/section-63.110"
    section_xx = "40/63/subpart-XX/subject-group-ECFR3a9b3e27cd7a862/section-63.1097"

    assert subpart_heading_for(nodes, section_g) == heading_by_key["40/63/subpart-G"]
    assert subpart_heading_for(nodes, section_xx) == heading_by_key["40/63/subpart-XX"]
    assert subpart_heading_for(nodes, section_g) != heading_by_key[section_g]
    assert subpart_heading_for(nodes, section_g) != subpart_heading_for(nodes, section_xx)
    assert subpart_heading_for(nodes, section_g).startswith("Subpart G")
    assert subpart_heading_for(nodes, section_xx).startswith("Subpart XX")


def test_ranks_chunks_by_cosine_similarity_descending():
    query = [1.0, 0.0]
    chunks = [
        {"chunk_key": "b", "embedding": [0.0, 1.0]},
        {"chunk_key": "a", "embedding": [1.0, 0.0]},
        {"chunk_key": "c", "embedding": [0.7071, 0.7071]},
    ]

    ranked = rank_chunks_by_similarity(query, chunks)

    assert [c["chunk_key"] for c in ranked] == ["a", "c", "b"]
    assert ranked[0]["score"] == pytest.approx(1.0)
    assert ranked[2]["score"] == pytest.approx(0.0, abs=1e-9)


def test_rank_chunks_top_k_limits_result_count():
    query = [1.0, 0.0]
    chunks = [{"chunk_key": str(i), "embedding": [1.0 / (i + 1), 0.0]} for i in range(5)]

    ranked = rank_chunks_by_similarity(query, chunks, top_k=2)

    assert len(ranked) == 2
    assert ranked[0]["chunk_key"] == "0"
