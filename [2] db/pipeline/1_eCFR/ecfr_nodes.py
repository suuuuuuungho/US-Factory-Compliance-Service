"""Convert the structural DIV nodes in an eCFR Part XML document to rows."""

from __future__ import annotations

import hashlib
import html
import json
from copy import deepcopy
from typing import Any

from lxml import etree


_TYPE_NAMES = {
    "PART": "part",
    "SUBPART": "subpart",
    "SUBJGRP": "subject_group",
    "SECTION": "section",
    "APPENDIX": "appendix",
}
_SEGMENT_NAMES = {
    "part": "part",
    "subpart": "subpart",
    "subject_group": "subject-group",
    "section": "section",
    "appendix": "appendix",
}
_STRUCTURAL_TAGS = {f"DIV{i}" for i in range(5, 10)}


def _heading(element: etree._Element) -> str:
    head = element.find("HEAD")
    if head is None:
        return ""
    return " ".join("".join(head.itertext()).split())


def _metadata(element: etree._Element) -> dict[str, Any]:
    raw = element.get("hierarchy_metadata", "")
    # XML decoding turns the outer &amp;quot; form into &quot; once; accepting
    # repeated entities also handles responses that contain another wrapper.
    for _ in range(3):
        decoded = html.unescape(raw)
        if decoded == raw:
            break
        raw = decoded
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _key_segment(node_type: str, identifier: str) -> str:
    value = "-".join(identifier.split())
    return f"{_SEGMENT_NAMES[node_type]}-{value}"


def _fragment(element: etree._Element, node_type: str) -> str:
    clone = deepcopy(element)
    if node_type in {"part", "subpart", "subject_group"}:
        for child in reversed(list(clone.iterdescendants())):
            if child.tag in _STRUCTURAL_TAGS:
                parent = child.getparent()
                if parent is not None:
                    parent.remove(child)
    return etree.tostring(clone, encoding="unicode", with_tail=False)


def parse_nodes(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse Part XML into document-ordered structural node dictionaries."""

    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True
    )
    root = etree.fromstring(xml_bytes, parser)
    nodes: list[dict[str, Any]] = []
    element_rows: dict[str, dict[str, Any]] = {}

    for element in root.iter():
        if element.tag not in _STRUCTURAL_TAGS:
            continue
        raw_type = element.get("TYPE", "").upper()
        node_type = _TYPE_NAMES.get(raw_type)
        if node_type is None:
            continue
        identifier = element.get("N", "")
        if node_type == "part":
            node_key = f"40/{identifier}"
        else:
            ancestor = element.getparent()
            parent_row = None
            while ancestor is not None:
                parent_row = element_rows.get(root.getroottree().getpath(ancestor))
                if parent_row is not None:
                    break
                ancestor = ancestor.getparent()
            node_key = f"{parent_row['node_key']}/{_key_segment(node_type, identifier)}" if parent_row else _key_segment(node_type, identifier)

        parent_key = None
        parent_path: list[str] = []
        ancestor = element.getparent()
        while ancestor is not None:
            row = element_rows.get(root.getroottree().getpath(ancestor))
            if row is not None:
                if parent_key is None:
                    parent_key = row["node_key"]
                parent_path = row["hierarchy_path"]
                break
            ancestor = ancestor.getparent()

        heading = _heading(element)
        fragment = _fragment(element, node_type)
        metadata = _metadata(element)
        row: dict[str, Any] = {
            "node_key": node_key,
            "parent_key": parent_key,
            "node_type": node_type,
            "identifier": identifier,
            "heading": heading,
            "reserved": "[reserved]" in heading.lower(),
            "sort_order": len(nodes),
            "hierarchy_path": [*parent_path, heading],
            "citation": metadata.get("citation"),
            "source_locator": f"line:{element.sourceline}",
            "xml_fragment": fragment,
            "content_hash": hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
        }
        nodes.append(row)
        element_rows[root.getroottree().getpath(element)] = row

    return nodes


__all__ = ["parse_nodes"]
