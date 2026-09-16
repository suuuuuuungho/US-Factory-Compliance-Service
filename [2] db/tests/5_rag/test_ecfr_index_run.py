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
from ecfr_index_run import rank_chunks_by_similarity, select_subpart_chunks
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
    expected_text = "\n\n".join(
        blocks_by_key[TABLE_SECTION_KEY][no] for no in body_chunk["block_nos"]
    )
    assert body_chunk["chunk_text"] == expected_text


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
