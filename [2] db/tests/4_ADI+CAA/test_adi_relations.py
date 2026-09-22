"""SUU-222: 본문에 적힌 다른 Control Number → adi_document_relation 행.

문서 안에서 알고 있는 Control Number(자기 것 제외)를 찾고, 바로 앞 문구로 관계 종류를 정한다:
"also filed as / also appears in" → same_file, "rescind / supersede / replace" → supersedes, "withdraw" → withdraws.
근거 위치(evidence_locator)는 필수. 문구가 없거나(단순 "See also") 상대 문서가 없으면 관계를 만들지 않는다.
"""
from __future__ import annotations

from adi_relations import extract_relations

VERSION_ID = "11111111-1111-5111-8111-111111111111"
DOC_SELF = "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"
DOC_OTHER = "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"
DOC_THIRD = "cccccccc-cccc-5ccc-8ccc-cccccccccccc"
CONTROL_TO_DOCUMENT = {"M090020": DOC_SELF, "M080027": DOC_OTHER, "M050031": DOC_THIRD}


def _block(block_no: int, text: str) -> dict:
    return {"version_id": VERSION_ID, "block_no": block_no, "page_no": 1, "kind": "header", "text_content": text}


def test_supersedes_phrase_gives_one_relation_with_evidence():
    first = "Control Number: M090020\nComments: Partially rescinds the determination issued as ADI Control Number M080027."
    blocks = [
        _block(1, first),
        _block(2, "Letter:\nThe waiver is rescinded. (See ADI Control Number M080027). EPA reserves the right to rescind this determination."),
    ]

    relations = extract_relations(VERSION_ID, DOC_SELF, blocks, CONTROL_TO_DOCUMENT)

    start = first.index("M080027")
    assert relations == [{
        "from_document_id": DOC_SELF,
        "to_document_id": DOC_OTHER,
        "relation_type": "supersedes",
        "evidence_version_id": VERSION_ID,
        "evidence_locator": f"block:1;char:{start}-{start + 7}",
        "review_status": "검토 전",
    }]


def test_also_filed_as_gives_same_file_and_plain_mentions_or_unknown_targets_give_nothing():
    blocks = [
        _block(1, "Control Number: M090020\nComments: This determination also filed as a MACT determination, ADI Control No. M050031."),
        _block(2, "See also ADI Control Number M080027 for a related determination. Request withdrawn per M999999."),
    ]

    relations = extract_relations(VERSION_ID, DOC_SELF, blocks, CONTROL_TO_DOCUMENT)

    assert [(rel["to_document_id"], rel["relation_type"]) for rel in relations] == [(DOC_THIRD, "same_file")]


def test_withdrawn_phrase_gives_withdraws_and_self_mention_is_ignored():
    blocks = [_block(1, "Control Number: M090020\nThe request in M080027 has been withdrawn by the company. This is M090020.")]

    relations = extract_relations(VERSION_ID, DOC_SELF, blocks, CONTROL_TO_DOCUMENT)

    assert [(rel["from_document_id"], rel["to_document_id"], rel["relation_type"]) for rel in relations] == [(DOC_SELF, DOC_OTHER, "withdraws")]
