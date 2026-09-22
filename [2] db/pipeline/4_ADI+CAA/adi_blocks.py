"""Split extracted ADI letter text into reviewable blocks."""

from __future__ import annotations

import re


_MARKERS = re.compile(
    r"(?mi)^\s*(?:(?P<question>Q\d*\s*:)|(?P<answer>A\d*\s*:)|(?P<body>Letter\s*:)|(?P<condition>Conditions?(?: of Approval)?\s*:?\s*$)|(?P<signature>(?:Sincerely|Very truly yours|Respectfully)\b))"
)


def split_blocks(version_id: str, pages: list[dict]) -> list[dict]:
    """Return lossless blocks for the successful pages of one version."""
    usable = sorted((page for page in pages if page.get("status") == "ok"), key=lambda page: page["page_no"])
    if not usable:
        return []
    starts: list[tuple[int, int]] = []
    parts: list[str] = []
    offset = 0
    for number, page in enumerate(usable):
        if number:
            parts.append("\n\n")
            offset += 2
        starts.append((offset, page["page_no"]))
        text = page.get("text_content") or ""
        parts.append(text)
        offset += len(text)
    text = "".join(parts)
    if not text:
        return []
    matches = list(_MARKERS.finditer(text))
    if not matches:
        matches = []
    boundaries = [match.start() for match in matches]
    if not boundaries or boundaries[0] != 0:
        boundaries.insert(0, 0)
    boundaries.append(len(text))
    rows = []
    for block_no, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        match = next((item for item in matches if item.start() == start), None)
        if match:
            kind = next(name for name, value in match.groupdict().items() if value is not None)
        elif start == 0 and re.search(r"(?mi)^\s*Control Number\s*:", text):
            kind = "header"
        else:
            kind = "body"
        page_no = next(page for page_start, page in reversed(starts) if page_start <= start)
        rows.append({
            "version_id": version_id, "block_no": block_no, "page_no": page_no, "kind": kind,
            "text_content": text[start:end], "source_locator": f"page:{page_no};char:{start}-{end}",
            "review_status": "검토 전",
        })
    return rows
