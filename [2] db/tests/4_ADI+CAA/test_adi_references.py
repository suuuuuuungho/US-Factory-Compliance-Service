"""SUU-222: 블록 글자 속 "40 CFR 63.xxxx" 인용 → adi_cfr_reference 행.

인용은 title/part/subpart/section/paragraph 로 나눈다. Part 63 section·subpart 만 eCFR 노드(nodes.jsonl)에 잇는다.
Part 60 AAAA ≠ Part 63 AAAA. 못 이은 인용은 current_node_key None + review_status=미해결.
reference_role 은 1차에서 전부 mention.
"""
from __future__ import annotations

import uuid

from adi_references import build_node_index, extract_references, parse_citations

VERSION_ID = "11111111-1111-5111-8111-111111111111"

NODES = [
    {"node_key": "40/63", "node_type": "part", "identifier": "63"},
    {"node_key": "40/63/subpart-A", "node_type": "subpart", "identifier": "A"},
    {"node_key": "40/63/subpart-A/section-63.2", "node_type": "section", "identifier": "63.2"},
    {"node_key": "40/63/subpart-A/section-63.7", "node_type": "section", "identifier": "63.7"},
    {"node_key": "40/63/subpart-AAAA", "node_type": "subpart", "identifier": "AAAA"},
    {"node_key": "40/63/subpart-EEE", "node_type": "subpart", "identifier": "EEE"},
    {"node_key": "40/63/subpart-EEE/section-63.1204", "node_type": "section", "identifier": "63.1204"},
    {"node_key": "40/63/subpart-EEE/section-63.1207", "node_type": "section", "identifier": "63.1207"},
    {"node_key": "40/63/subpart-CCCCCCC/subject-group-ECFR99bb52384c85a56/section-63.11607", "node_type": "section", "identifier": "63.11607"},
]


def _block(block_no: int, text: str) -> dict:
    return {"version_id": VERSION_ID, "block_no": block_no, "page_no": 1, "kind": "body", "text_content": text}


def test_parse_citations_splits_section_paragraph_and_subpart_forms():
    text = (
        "pursuant to 40 C.F.R. 63.1207(c)(2) and 40 CFR § 63.7(h). See 40 CFR part 63, subpart EEE "
        "and 40 CFR Part 60, Subpart AAAA. Also §63.11607(a)(1)."
    )

    cites = parse_citations(text)

    by_raw = {cite["raw_citation"]: cite for cite in cites}
    start = text.index("40 C.F.R. 63.1207")
    assert by_raw["40 C.F.R. 63.1207(c)(2)"] == {
        "raw_citation": "40 C.F.R. 63.1207(c)(2)", "title": 40, "part": "63", "subpart": None,
        "section": "63.1207", "paragraph": "(c)(2)", "start": start, "end": start + len("40 C.F.R. 63.1207(c)(2)"),
    }
    assert by_raw["40 CFR § 63.7(h)"]["section"] == "63.7"
    assert by_raw["40 CFR § 63.7(h)"]["paragraph"] == "(h)"
    start = text.index("40 CFR part 63")
    assert by_raw["40 CFR part 63, subpart EEE"] == {
        "raw_citation": "40 CFR part 63, subpart EEE", "title": 40, "part": "63", "subpart": "EEE",
        "section": None, "paragraph": None, "start": start, "end": start + len("40 CFR part 63, subpart EEE"),
    }
    assert by_raw["40 CFR Part 60, Subpart AAAA"]["part"] == "60"
    assert by_raw["40 CFR Part 60, Subpart AAAA"]["subpart"] == "AAAA"
    bare = by_raw["§63.11607(a)(1)"]
    assert (bare["title"], bare["part"], bare["section"], bare["paragraph"]) == (None, "63", "63.11607", "(a)(1)")
    assert [cite["start"] for cite in cites] == sorted(cite["start"] for cite in cites)


def test_part60_citation_is_not_linked_to_part63_node():
    index = build_node_index(NODES)
    blocks = [_block(1, "This request also cites 40 CFR Part 60, Subpart AAAA and 40 CFR 60.5175(b), not 40 CFR part 63, subpart AAAA.")]

    refs = extract_references(VERSION_ID, blocks, index)

    by_raw = {ref["raw_citation"]: ref for ref in refs}
    assert by_raw["40 CFR Part 60, Subpart AAAA"]["current_node_key"] is None
    assert by_raw["40 CFR Part 60, Subpart AAAA"]["review_status"] == "미해결"
    assert by_raw["40 CFR 60.5175(b)"]["current_node_key"] is None
    assert by_raw["40 CFR 60.5175(b)"]["review_status"] == "미해결"
    assert by_raw["40 CFR part 63, subpart AAAA"]["current_node_key"] == "40/63/subpart-AAAA"
    assert by_raw["40 CFR part 63, subpart AAAA"]["review_status"] == "검토 전"


def test_unresolved_part63_section_has_null_node_and_unresolved_status():
    index = build_node_index(NODES)
    blocks = [_block(1, "The old rule at 40 CFR 63.9999 no longer exists, but 40 CFR 63.2 does.")]

    refs = extract_references(VERSION_ID, blocks, index)

    by_raw = {ref["raw_citation"]: ref for ref in refs}
    assert by_raw["40 CFR 63.9999"]["current_node_key"] is None
    assert by_raw["40 CFR 63.9999"]["review_status"] == "미해결"
    assert by_raw["40 CFR 63.2"]["current_node_key"] == "40/63/subpart-A/section-63.2"
    assert by_raw["40 CFR 63.2"]["review_status"] == "검토 전"
    assert all(ref["historical_node_key"] is None for ref in refs)


def test_references_are_mentions_with_evidence_inside_their_block_and_stable_ids():
    index = build_node_index(NODES)
    blocks = [
        _block(1, "Q: Is the kiln subject to 40 CFR part 63, subpart EEE?"),
        _block(2, "A: Yes. See 40 C.F.R. 63.1204(c)(1) and 40 C.F.R. 63.1204(c)(1) again."),
    ]

    refs = extract_references(VERSION_ID, blocks, index)

    assert len(refs) == 3
    assert {ref["reference_role"] for ref in refs} == {"mention"}
    assert [ref["block_no"] for ref in refs] == [1, 2, 2]
    assert refs[0]["evidence_locator"] == "block:1;char:26-53"
    assert refs[1]["current_node_key"] == "40/63/subpart-EEE/section-63.1204"
    assert refs[1]["paragraph"] == "(c)(1)"
    assert len({ref["reference_id"] for ref in refs}) == 3
    assert all(uuid.UUID(ref["reference_id"]).version == 5 for ref in refs)
    assert extract_references(VERSION_ID, blocks, index) == refs
    assert all(ref["version_id"] == VERSION_ID for ref in refs)
