"""Parse CAA Dashboard response rows from page HTML."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from lxml import etree
from lxml import html as lxml_html


_HEADERS = (
    "Facility Name",
    "Title",
    "Affected Subpart",
    "Link to Responses",
)
_SUBPART_PATTERN = re.compile(r"Part\s*(\d+)\s*,\s*([A-Za-z]{1,7})\s*:")


def _text(element: etree._Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _urls(cell: etree._Element) -> tuple[str | None, str | None]:
    links = cell.xpath(".//a[@href]")
    if not links:
        return None, None

    href = links[0].get("href")
    if not href:
        return None, None

    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    wrapped_urls = query.get("url")
    if wrapped_urls:
        candidate = wrapped_urls[0]
        source_url = parsed._replace(
            query=urlencode({"url": candidate}), fragment=""
        ).geturl()
    else:
        candidate = href
        source_url = href

    canonical = urlparse(candidate)
    canonical_url = (
        candidate
        if canonical.scheme == "https" and canonical.netloc == "www.epa.gov"
        else None
    )
    return source_url, canonical_url


def parse_dashboard(html: bytes) -> list[dict[str, Any]]:
    """Return the response rows from the first matching CAA Dashboard table."""

    try:
        document = lxml_html.fromstring(html)
    except (etree.ParserError, ValueError) as error:
        raise ValueError("CAA Dashboard table not found") from error

    table = None
    indexes: dict[str, int] = {}
    for candidate in document.xpath("//table"):
        headers = [_text(header) for header in candidate.xpath(".//thead//th")]
        if all(header in headers for header in _HEADERS):
            table = candidate
            indexes = {header: headers.index(header) for header in _HEADERS}
            break

    if table is None:
        raise ValueError("CAA Dashboard table is missing required columns")

    rows: list[dict[str, Any]] = []
    for table_row in table.xpath(".//tbody/tr"):
        cells = table_row.xpath("./td")
        if not cells:
            continue

        facility_cell = cells[indexes["Facility Name"]]
        title_cell = cells[indexes["Title"]]
        subpart_cell = cells[indexes["Affected Subpart"]]
        link_cell = cells[indexes["Link to Responses"]]
        affected_subpart_raw = _text(subpart_cell)
        source_url, canonical_url = _urls(link_cell)

        rows.append(
            {
                "source_system": "caa_dashboard",
                "facility_name": _text(facility_cell),
                "title": _text(title_cell),
                "affected_subpart_raw": affected_subpart_raw,
                "link_text": _text(link_cell),
                "source_url": source_url,
                "canonical_url": canonical_url,
                "affected_subparts": [
                    {"part": part, "subpart": subpart}
                    for part, subpart in _SUBPART_PATTERN.findall(
                        affected_subpart_raw
                    )
                ],
            }
        )

    return rows
