"""Parse ADI search result rows from page HTML."""

from __future__ import annotations

from typing import Any

from lxml import etree
from lxml import html as lxml_html


_HEADERS = (
    "Checkbox for Determination Details",
    "Control Number",
    "Title",
    "Letter Date",
    "Categories",
    "Office",
    "Letter Author",
)
_FILE_URL = (
    "https://cfpub.epa.gov/adi/index.cfm?"
    "fuseaction=home.dsp_show_file_contents&id="
)


def _text(element: etree._Element) -> str:
    return " ".join("".join(element.itertext()).split())


def parse_results(html: bytes) -> dict[str, Any]:
    """Return the ADI server result count and rows from a search page."""

    try:
        document = lxml_html.fromstring(html)
    except (etree.ParserError, ValueError) as error:
        raise ValueError("ADI results table not found") from error

    length_inputs = document.xpath(
        "//input[@type='hidden' and @name='results_length']/@value"
    )
    if not length_inputs:
        raise ValueError("ADI results length not found")
    try:
        results_length = int(length_inputs[0])
    except (TypeError, ValueError) as error:
        raise ValueError("ADI results length is invalid") from error

    table = None
    indexes: dict[str, int] = {}
    for candidate in document.xpath("//table"):
        for header_row in candidate.xpath(".//thead/tr"):
            headers = [_text(cell) for cell in header_row.xpath("./td")]
            if all(header in headers for header in _HEADERS):
                table = candidate
                indexes = {header: headers.index(header) for header in _HEADERS}
                break
        if table is not None:
            break

    if table is None:
        raise ValueError("ADI results table is missing required columns")

    rows: list[dict[str, Any]] = []
    for table_row in table.xpath(".//tbody/tr"):
        cells = table_row.xpath("./td")
        if not cells:
            continue
        if len(cells) <= max(indexes.values()):
            raise ValueError("ADI results row is missing required columns")

        control_number = _text(cells[indexes["Control Number"]])
        categories_raw = _text(cells[indexes["Categories"]])
        author = _text(cells[indexes["Letter Author"]])
        rows.append(
            {
                "source_system": "adi",
                "control_number": control_number,
                "title": _text(cells[indexes["Title"]]),
                "letter_date_raw": _text(cells[indexes["Letter Date"]]),
                "categories": [
                    category.strip()
                    for category in categories_raw.split(",")
                    if category.strip()
                ],
                "office": _text(cells[indexes["Office"]]),
                "author": author or None,
                "source_url": _FILE_URL + control_number,
            }
        )

    return {"results_length": results_length, "rows": rows}
