"""SUU-44: raw 원본 → parsed/{기준일}/{parser_version}/ 에 nodes.jsonl·blocks.jsonl·quality_report.json.

네트워크와 26MB 원본은 쓰지 않는다. fixture XML·목차 샘플을 1단계와 같은 함수(save_raw)로
tmp_path/raw 에 넣고 돌린다. 기대 숫자는 fixture 를 기존 파서(SUU-41~43)로 돌린 값이다.
"""
import hashlib
import json
from datetime import date
from pathlib import Path

from lxml import etree

from ecfr_blocks import parse_blocks
from ecfr_labels import assign_label_paths
from ecfr_parse import PARSER_VERSION, parse_release
from ecfr_raw import save_raw
from ecfr_structure import find_part

FIXTURES = Path(__file__).parent / "fixtures"
XML = (FIXTURES / "ecfr_part63_sample.xml").read_bytes()
STRUCTURE = (FIXTURES / "ecfr_structure_sample.json").read_bytes()
AS_OF = "2026-09-10"
COUNTS = {"subpart": 5, "subject_group": 3, "section": 9, "appendix": 4}

NODE_FIELDS = {
    "node_key", "parent_key", "node_type", "identifier", "heading", "reserved", "sort_order",
    "hierarchy_path", "citation", "source_locator", "xml_fragment", "content_hash",
}
BLOCK_FIELDS = {
    "node_key", "block_no", "kind", "text_content", "markup", "source_locator", "parse_status",
    "label_path", "label_status",
}


def put_raw(root, structure=STRUCTURE):
    """1단계(ecfr_collect)가 남기는 모양 그대로 raw/{as_of}/manifest.json 과 원본 두 개를 만든다."""
    for name, body, media in (
        ("title-40-structure.json", structure, "application/json"),
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


def read_report(root):
    return json.loads((out_dir(root) / "quality_report.json").read_text(encoding="utf-8"))


def expected_blocks(tag, n):
    """기존 파서가 조문 하나에 주는 블록 (node_key 만 빼고 blocks.jsonl 과 같아야 한다)."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)
    element = etree.fromstring(XML, parser).find(f".//{tag}[@N='{n}']")
    return assign_label_paths(parse_blocks(element))


def without_key(blocks):
    return [{k: v for k, v in b.items() if k != "node_key"} for b in blocks]


def test_writes_three_files_and_report_passes(tmp_path):
    put_raw(tmp_path)

    report = parse_release(tmp_path, AS_OF)

    out = out_dir(tmp_path)
    assert sorted(p.name for p in out.iterdir()) == ["blocks.jsonl", "nodes.jsonl", "quality_report.json"]
    assert read_report(tmp_path) == report

    assert report["status"] == "succeeded"
    assert report["as_of"] == AS_OF
    assert report["parser_version"] == PARSER_VERSION
    assert report["xml_sha256"] == hashlib.sha256(XML).hexdigest()
    assert report["structure_sha256"] == hashlib.sha256(STRUCTURE).hexdigest()
    assert report["structure_counts"] == COUNTS
    assert report["node_counts"] == COUNTS  # part 자신은 세지 않는다 (목차도 안 센다)
    assert report["lost_text"] == 0
    assert report["block_kinds"] == {
        "paragraph": 33, "heading": 13, "citation": 6, "extract": 4, "table": 3, "image": 1,
        "formula": 1, "note": 1, "footnote": 1, "editorial_note": 1, "other": 1,
    }
    assert report["label_statuses"] == {"ok": 30, "inherited": 35}
    assert isinstance(report["started_at"], str) and isinstance(report["finished_at"], str)

    # nodes.jsonl = parse_nodes 결과 한 줄씩, 문서 순서
    nodes = read_jsonl(out / "nodes.jsonl")
    assert len(nodes) == 22
    assert nodes[0]["node_key"] == "40/63" and nodes[0]["node_type"] == "part"
    assert [n["sort_order"] for n in nodes] == list(range(22))
    assert all(set(n) == NODE_FIELDS for n in nodes)

    # blocks.jsonl = 조문·부록마다 parse_blocks → assign_label_paths 결과 + node_key. 노드 순서 → block_no 순서
    blocks = read_jsonl(out / "blocks.jsonl")
    assert len(blocks) == 65
    assert all(set(b) == BLOCK_FIELDS for b in blocks)
    order = {n["node_key"]: n["sort_order"] for n in nodes}
    assert [(order[b["node_key"]], b["block_no"]) for b in blocks] == sorted(
        (order[b["node_key"]], b["block_no"]) for b in blocks
    )
    leaves = {n["node_key"] for n in nodes if n["node_type"] in {"section", "appendix"} and not n["reserved"]}
    assert {b["node_key"] for b in blocks} == leaves  # 예약 조문·부록은 블록 0개, 상위 노드는 블록 없음

    by_node = {}
    for b in blocks:
        by_node.setdefault(b["node_key"], []).append(b)
    assert without_key(by_node["40/63/subpart-G/section-63.110"]) == expected_blocks("DIV8", "63.110")
    assert without_key(by_node["40/63/subpart-A/section-63.1"]) == expected_blocks("DIV8", "63.1")
    assert [b["block_no"] for b in by_node["40/63/subpart-G/section-63.110"]] == list(range(1, 14))


def test_second_run_writes_identical_bytes(tmp_path):
    put_raw(tmp_path)
    out = out_dir(tmp_path)

    first = parse_release(tmp_path, AS_OF)
    nodes_1 = (out / "nodes.jsonl").read_bytes()
    blocks_1 = (out / "blocks.jsonl").read_bytes()
    second = parse_release(tmp_path, AS_OF)

    assert (out / "nodes.jsonl").read_bytes() == nodes_1
    assert (out / "blocks.jsonl").read_bytes() == blocks_1
    # 줄 끝은 항상 LF. Windows 에서 만들어도 Linux(CI)와 바이트가 같다
    assert nodes_1.endswith(b"\n") and b"\r\n" not in nodes_1
    assert blocks_1.endswith(b"\n") and b"\r\n" not in blocks_1

    # 시각은 report 에만 있다
    def timeless(report):
        return {k: v for k, v in report.items() if k not in {"started_at", "finished_at"}}

    assert timeless(first) == timeless(second)


def test_fails_when_counts_differ_from_structure(tmp_path):
    # 목차에만 있는 유령 조문 하나 → 목차 section 10개, 원문 9개
    structure = json.loads(STRUCTURE)
    find_part(structure, "63")["children"].append(
        {"type": "section", "identifier": "63.999", "label": "§ 63.999 Ghost.", "children": []}
    )
    put_raw(tmp_path, json.dumps(structure).encode("utf-8"))

    report = parse_release(tmp_path, AS_OF)  # 예외 없이 끝난다

    assert report["status"] == "failed"
    assert report["structure_counts"]["section"] == 10
    assert report["node_counts"]["section"] == 9
    assert report["lost_text"] == 0
    assert read_report(tmp_path)["status"] == "failed"
    # 결과 파일은 그대로 남긴다 (왜 떨어졌는지 볼 수 있게)
    assert (out_dir(tmp_path) / "nodes.jsonl").exists()
    assert (out_dir(tmp_path) / "blocks.jsonl").exists()
