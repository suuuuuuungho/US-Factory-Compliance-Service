"""SUU-41: Part 63 XML을 목차와 같은 노드 표로 변환.

샘플 XML은 2026-09-11 기준 Part 63 원문에서 조각을 잘라 조립한 것이다.
ecfr_structure_sample.json(Subpart A·G·J·K·XX + Part 바로 아래 항목)과 같은 모양이다.
네트워크와 26MB 원본은 쓰지 않는다.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from ecfr_nodes import parse_nodes
from ecfr_structure import count_by_type, find_part

FIXTURES = Path(__file__).parent / "fixtures"
XML = FIXTURES / "ecfr_part63_sample.xml"
STRUCTURE = FIXTURES / "ecfr_structure_sample.json"


def load_nodes() -> list[dict]:
    return parse_nodes(XML.read_bytes())


def by_key(nodes: list[dict]) -> dict[str, dict]:
    return {n["node_key"]: n for n in nodes}


def test_node_counts_match_structure_sample():
    nodes = load_nodes()
    structure = json.loads(STRUCTURE.read_text(encoding="utf-8"))

    types = Counter(n["node_type"] for n in nodes)
    assert types.pop("part") == 1
    assert dict(types) == count_by_type(find_part(structure, "63"))
    assert dict(types) == {"subpart": 5, "subject_group": 3, "section": 9, "appendix": 4}

    # 문서 순서 그대로, Part가 0번
    assert [n["sort_order"] for n in nodes] == list(range(len(nodes)))
    assert nodes[0]["node_type"] == "part"
    assert nodes[0]["node_key"] == "40/63"


def test_reserved_flag_and_part_level_parent():
    nodes = by_key(load_nodes())

    reserved = {k for k, n in nodes.items() if n["reserved"]}
    assert reserved == {
        "40/63/subpart-K",
        "40/63/section-63.569-63.599",
        "40/63/subpart-G/appendix-Tables-14-14b-to-Subpart-G-of-Part-63",
    }
    assert nodes["40/63/subpart-A/section-63.1"]["reserved"] is False

    # Part 바로 아래 조문·부록은 부모가 Part
    assert nodes["40/63/section-63.569-63.599"]["parent_key"] == "40/63"
    assert nodes["40/63/appendix-Appendix-A-to-Part-63"]["parent_key"] == "40/63"
    assert nodes["40/63"]["parent_key"] is None
    # 중간 제목 아래 조문은 부모가 중간 제목
    section = nodes["40/63/subpart-J/subject-group-ECFRad8028a5975965e/section-63.210"]
    assert section["parent_key"] == "40/63/subpart-J/subject-group-ECFRad8028a5975965e"
    assert nodes[section["parent_key"]]["parent_key"] == "40/63/subpart-J"


def test_node_keys_unique_and_hierarchy_path():
    nodes = load_nodes()
    keys = [n["node_key"] for n in nodes]
    assert len(keys) == len(set(keys))
    assert all(n["parent_key"] in keys for n in nodes if n["parent_key"] is not None)

    node = by_key(nodes)["40/63/subpart-A/section-63.1"]
    assert node["node_type"] == "section"
    assert node["identifier"] == "63.1"
    assert node["heading"] == "§ 63.1 Applicability."
    assert node["hierarchy_path"] == [
        "PART 63—NATIONAL EMISSION STANDARDS FOR HAZARDOUS AIR POLLUTANTS FOR SOURCE CATEGORIES",
        "Subpart A—General Provisions",
        "§ 63.1 Applicability.",
    ]
    assert node["citation"] == "40 CFR 63.1"
    assert node["source_locator"] == "line:16"
    assert node["xml_fragment"].startswith("<DIV8 ")
    assert "§ 63.1 Applicability." in node["xml_fragment"]
    assert node["content_hash"] == hashlib.sha256(node["xml_fragment"].encode("utf-8")).hexdigest()

    # 두 번 escape 된 hierarchy_metadata도 읽힌다. 상위 노드는 자식 DIV를 품지 않는다
    subpart = by_key(nodes)["40/63/subpart-A"]
    assert subpart["citation"] == "40 CFR Part 63 Subpart A"
    assert subpart["hierarchy_path"][-1] == "Subpart A—General Provisions"
    assert "<DIV8" not in subpart["xml_fragment"]
    assert "Subpart A—General Provisions" in subpart["xml_fragment"]

    # 제목 끝 줄바꿈은 정리한다
    appendix = by_key(nodes)["40/63/subpart-A/appendix-Table-1-to-Subpart-A-of-Part-63"]
    assert appendix["heading"] == "Table 1 to Subpart A of Part 63—Detection Sensitivity Levels (grams per hour)"
    assert appendix["identifier"] == "Table 1 to Subpart A of Part 63"
