"""Find CFR citations in ADI blocks and link current Part 63 nodes."""

from __future__ import annotations

import re
import uuid


_SECTION = re.compile(r"(?:(?P<title>\d{1,2})\s*C\.?\s*F\.?\s*R\.?\s*(?:§\s*)?|§\s*)?(?P<section>(?P<part>6[0-3])\.\d+)(?P<paragraph>(?:\([A-Za-z0-9]{1,4}\))*)", re.I)
_SUBPART = re.compile(r"(?:(?P<title>\d{1,2})\s*C\.?\s*F\.?\s*R\.?\s*)?[Pp]art\s+(?P<part>\d{1,3})\s*,?\s*[Ss]ubpart\s+(?P<subpart>[A-Z]{1,7})\b")


def parse_citations(text: str) -> list[dict]:
    found: list[dict] = []
    for pattern, is_section in ((_SECTION, True), (_SUBPART, False)):
        for match in pattern.finditer(text):
            # A plain numeric section is only meaningful for Parts 60 through 63.
            raw = match.group(0)
            if is_section and not ("C" in raw.upper() or "§" in raw or match.group("part") in {"60", "61", "62", "63"}):
                continue
            found.append({
                "raw_citation": raw, "title": int(match.group("title")) if match.group("title") else None,
                "part": match.group("part"), "subpart": None if is_section else match.group("subpart"),
                "section": match.group("section") if is_section else None,
                "paragraph": (match.group("paragraph") or None) if is_section else None,
                "start": match.start(), "end": match.end(),
            })
    return sorted(found, key=lambda row: row["start"])


def build_node_index(nodes: list[dict]) -> dict:
    index = {}
    for node in nodes:
        key = node.get("node_key", "")
        if not key.startswith("40/63/"):
            continue
        if node.get("node_type") == "section":
            index[("section", node.get("identifier"))] = key
        elif node.get("node_type") == "subpart":
            index[("subpart", "63", node.get("identifier"))] = key
    return index


def extract_references(version_id: str, blocks: list[dict], node_index: dict) -> list[dict]:
    rows = []
    for block in blocks:
        for citation in parse_citations(block["text_content"]):
            node_key = None
            if citation["part"] == "63" and citation["title"] in (None, 40):
                lookup = (("section", citation["section"]) if citation["section"] else ("subpart", "63", citation["subpart"]))
                node_key = node_index.get(lookup)
            start, end = citation["start"], citation["end"]
            rows.append({
                "reference_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"adi-reference:{version_id}:{block['block_no']}:{start}")),
                "version_id": version_id, "block_no": block["block_no"],
                **{key: citation[key] for key in ("raw_citation", "title", "part", "subpart", "section", "paragraph")},
                "reference_role": "mention", "evidence_locator": f"block:{block['block_no']};char:{start}-{end}",
                "review_status": "검토 전" if node_key else "미해결",
                "historical_ecfr_release_id": None, "historical_node_key": None,
                "current_ecfr_release_id": None, "current_node_key": node_key,
            })
    return rows
