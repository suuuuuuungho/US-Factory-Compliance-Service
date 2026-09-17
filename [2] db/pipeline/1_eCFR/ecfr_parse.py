"""Parse one stored eCFR release and write deterministic JSONL artifacts."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lxml import etree

from ecfr_blocks import flat_text, parse_blocks
from ecfr_labels import assign_label_paths
from ecfr_nodes import _STRUCTURAL_TAGS, _TYPE_NAMES, parse_nodes
from ecfr_structure import count_by_type, find_part


PARSER_VERSION = "v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_entry(manifest: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for entry in reversed(manifest):
        if entry.get("name") == name:
            return entry
    raise FileNotFoundError(f"{name} is missing from the raw manifest")


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows
    ).encode("utf-8")


def _node_text(element: etree._Element) -> str:
    parts = [element.text or ""]
    for child in element:
        if child.tag != "HEAD":
            parts.append(flat_text(child))
        parts.append(child.tail or "")
    return " ".join(" ".join(parts).split())


def parse_release(root: Path, as_of: str) -> dict[str, Any]:
    """Parse a raw Part 63 snapshot and write its rows and quality report."""

    root = Path(root)
    started_at = _now()
    manifest_path = root / "raw" / as_of / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    structure_entry = _manifest_entry(manifest, "title-40-structure.json")
    xml_entry = _manifest_entry(manifest, "title-40-part-63.xml")

    structure_bytes = (root / structure_entry["path"]).read_bytes()
    xml_bytes = (root / xml_entry["path"]).read_bytes()
    structure = json.loads(structure_bytes)
    structure_counts = count_by_type(find_part(structure, "63"))

    nodes = parse_nodes(xml_bytes)
    node_counts = dict(
        Counter(node["node_type"] for node in nodes if node["node_type"] != "part")
    )

    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True
    )
    tree_root = etree.fromstring(xml_bytes, parser)
    elements = [
        element
        for element in tree_root.iter()
        if element.tag in _STRUCTURAL_TAGS
        and element.get("TYPE", "").upper() in _TYPE_NAMES
    ]
    assert len(elements) == len(nodes)

    block_rows: list[dict[str, Any]] = []
    block_kinds: Counter[str] = Counter()
    label_statuses: Counter[str] = Counter()
    lost_text = 0
    for element, node in zip(elements, nodes):
        assert element.get("N", "") == node["identifier"]
        if node["node_type"] not in {"section", "appendix"}:
            continue

        blocks = assign_label_paths(parse_blocks(element))
        block_text = " ".join(
            " ".join(block["text_content"] for block in blocks).replace("|", " ").split()
        )
        if block_text != _node_text(element):
            lost_text += 1

        for block in blocks:
            block_rows.append({"node_key": node["node_key"], **block})
            block_kinds[block["kind"]] += 1
            label_statuses[block["label_status"]] += 1

    status = (
        "succeeded"
        if node_counts == structure_counts and lost_text == 0
        else "failed"
    )
    report: dict[str, Any] = {
        "as_of": as_of,
        "parser_version": PARSER_VERSION,
        "status": status,
        "structure_sha256": structure_entry["sha256"],
        "xml_sha256": xml_entry["sha256"],
        "structure_counts": structure_counts,
        "node_counts": node_counts,
        "lost_text": lost_text,
        "block_kinds": dict(block_kinds),
        "label_statuses": dict(label_statuses),
        "started_at": started_at,
        "finished_at": _now(),
    }

    out = root / "parsed" / as_of / PARSER_VERSION
    out.mkdir(parents=True, exist_ok=True)
    (out / "nodes.jsonl").write_bytes(_jsonl_bytes(nodes))
    (out / "blocks.jsonl").write_bytes(_jsonl_bytes(block_rows))
    (out / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    pipeline_root = Path(__file__).resolve().parents[2] / "1) eCFR"
    raw_root = pipeline_root / "raw"
    selected_as_of = (
        sys.argv[1]
        if len(sys.argv) > 1
        else max(path.name for path in raw_root.iterdir() if path.is_dir())
    )
    result = parse_release(pipeline_root, selected_as_of)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "succeeded" else 2)


__all__ = ["PARSER_VERSION", "parse_release"]
