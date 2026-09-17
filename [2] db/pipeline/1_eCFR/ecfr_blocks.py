"""Convert the content children of an eCFR structural node into blocks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from lxml import etree


_PARAGRAPH_TAGS = {
    "P", "FP", "FP-1", "FP-2", "FP1-2", "FP2-2", "FP-DASH", "TCAP",
}
_KIND_BY_TAG = {
    **{tag: "paragraph" for tag in _PARAGRAPH_TAGS},
    "HD1": "heading",
    "HD2": "heading",
    "HD3": "heading",
    "img": "image",
    "MATH": "formula",
    "EXTRACT": "extract",
    "NOTE": "note",
    "CITA": "citation",
    "FTNT": "footnote",
    "EDNOTE": "editorial_note",
}


def _text_content(element: etree._Element) -> str:
    if _is_table(element):
        lines: list[str] = []
        caption = element.find(".//CAPTION")
        if caption is not None:
            lines.append(_text_content(caption))
        for row in element.findall(".//TR"):
            cells = [cell for cell in row if cell.tag in ("TD", "TH")]
            lines.append(" | ".join(_text_content(cell) for cell in cells))
        return "\n".join(lines)
    return " ".join(" ".join(element.itertext()).split())


def _is_table(element: etree._Element) -> bool:
    return element.tag == "DIV" and element.find(".//TABLE") is not None


def _kind(element: etree._Element) -> str:
    if _is_table(element):
        return "table"
    return _KIND_BY_TAG.get(element.tag, "other")


def _markup(element: etree._Element) -> str:
    clone = deepcopy(element)
    for image in clone.iter("img"):
        src = image.get("src", "")
        if src.startswith("/graphics/"):
            image.set("src", f"https://www.ecfr.gov{src}")
    return etree.tostring(clone, encoding="unicode", with_tail=False)


def parse_blocks(element: etree._Element) -> list[dict[str, Any]]:
    """Return direct content children of a DIV8/DIV9 as ordered block rows."""

    head = element.find("HEAD")
    if head is not None and "[reserved]" in _text_content(head).lower():
        return []

    blocks: list[dict[str, Any]] = []
    for child in element:
        if child.tag == "HEAD":
            continue

        kind = _kind(child)
        text_content = _text_content(child)
        markup = _markup(child)
        has_image = child.find(".//img") is not None or child.tag == "img"
        if kind == "other":
            parse_status = "unknown_tag"
        elif not text_content and not has_image:
            parse_status = "empty"
        else:
            parse_status = "ok"
        blocks.append(
            {
                "block_no": len(blocks) + 1,
                "kind": kind,
                "text_content": text_content,
                "markup": markup,
                "source_locator": f"line:{child.sourceline}",
                "parse_status": parse_status,
            }
        )
    return blocks


__all__ = ["parse_blocks"]
