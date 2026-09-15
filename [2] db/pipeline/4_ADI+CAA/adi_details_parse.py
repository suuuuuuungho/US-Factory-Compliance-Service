"""Parse metadata rows from an ADI detail response."""

from __future__ import annotations

import re
from typing import Any

from lxml import etree
from lxml import html as lxml_html


_DATE_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{4})\s*$")


def _text(element: etree._Element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def _label_values(element: etree._Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for label_element in element.xpath("./strong"):
        label = _text(label_element).rstrip(":")
        value = " ".join((label_element.tail or "").split())
        values[label] = value.removeprefix(":").strip()
    return values


def parse_details(html: bytes) -> list[dict[str, Any]]:
    """Return structured metadata from each ADI detail result row."""

    try:
        document = lxml_html.fromstring(html)
    except (etree.ParserError, ValueError) as error:
        raise ValueError("ADI details table not found") from error

    rows: list[dict[str, Any]] = []
    for table_row in document.xpath(
        "//tr[contains(concat(' ', normalize-space(@class), ' '), ' no-sort ')]"
    ):
        control_values = table_row.xpath(
            ".//input[@name='control_number']/@value"
        )
        if not control_values:
            continue

        summary_divs = table_row.xpath(
            ".//div[.//input[@name='control_number']]"
        )
        links = summary_divs[0].xpath(".//a") if summary_divs else []
        if not summary_divs or not links:
            continue

        summary_text = _text(summary_divs[0])
        date_match = _DATE_PATTERN.search(summary_text)
        letter_date_raw = date_match.group(1) if date_match else ""

        metadata_divs = table_row.xpath(
            ".//div[strong[normalize-space(.)='Author']]"
        )
        metadata = _label_values(metadata_divs[0]) if metadata_divs else {}
        categories_raw = metadata.get("Categories", "")

        abstract_labels = table_row.xpath(
            ".//div[strong[normalize-space(.)='Abstract']]"
        )
        abstract_element = abstract_labels[0].getnext() if abstract_labels else None
        abstract = _text(abstract_element) if abstract_element is not None else ""

        rows.append(
            {
                "control_number": control_values[0],
                "title": _text(links[0]),
                "letter_date_raw": letter_date_raw,
                "author": metadata.get("Author", ""),
                "categories": [
                    category.strip()
                    for category in categories_raw.split(",")
                    if category.strip()
                ],
                "office": metadata.get("Office", ""),
                "abstract": abstract,
            }
        )

    return rows


__all__ = ["parse_details"]
