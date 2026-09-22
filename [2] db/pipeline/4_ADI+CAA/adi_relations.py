"""Extract explicit document-to-document relationships from ADI text."""

from __future__ import annotations

import re


_CONTROL = re.compile(r"\b[A-Z]?\d{6,8}\b")


def _sentences(text: str):
    start = 0
    for match in re.finditer(r"\n+|(?<!\bNo)(?<!\bNos)[.;!?](?=\s|$)", text, re.I):
        yield start, match.end(), text[start:match.end()]
        start = match.end()
    if start < len(text):
        yield start, len(text), text[start:]


def extract_relations(version_id: str, document_id: str, blocks: list[dict], control_to_document: dict) -> list[dict]:
    rows, seen = [], set()
    for block in blocks:
        for sentence_start, _, sentence in _sentences(block["text_content"]):
            lower = sentence.lower()
            relation_type = ("withdraws" if "withdraw" in lower else "supersedes" if any(word in lower for word in ("rescind", "supersed", "replace")) else "same_file" if any(word in lower for word in ("also filed", "also appears in", "also filed under")) else None)
            if not relation_type:
                continue
            for match in _CONTROL.finditer(sentence):
                target = control_to_document.get(match.group(0))
                if not target or target == document_id:
                    continue
                key = (document_id, target, relation_type)
                if key in seen:
                    continue
                seen.add(key)
                start = sentence_start + match.start()
                rows.append({"from_document_id": document_id, "to_document_id": target, "relation_type": relation_type,
                             "evidence_version_id": version_id, "evidence_locator": f"block:{block['block_no']};char:{start}-{start + len(match.group(0))}", "review_status": "검토 전"})
    return rows
