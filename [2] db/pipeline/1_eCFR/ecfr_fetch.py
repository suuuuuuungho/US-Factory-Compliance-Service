"""Download eCFR structure and Part XML responses.

This module handles only HTTP response decoding and URL construction.  Saving,
comparison, and refresh orchestration belong to later pipeline tickets.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Fetched:
    """The response body and the metadata needed to record its provenance."""

    body: bytes
    source_url: str
    final_url: str
    http_status: int
    media_type: str
    byte_size: int


def ensure_xml(body: bytes) -> bytes:
    """Reject common HTML access/check pages while preserving XML bytes."""

    prefix = body.lstrip().lower()
    if prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
        raise ValueError("eCFR response is HTML, not XML")
    return body


def fetch(url: str) -> Fetched:
    """Fetch ``url``, decompress gzip responses, and return response metadata."""

    request = Request(
        url,
        headers={
            "Accept": "application/xml, application/json",
            "Accept-Encoding": "gzip",
        },
        method="GET",
    )
    with urlopen(request) as response:
        body = response.read()
        content_encoding = response.headers.get("Content-Encoding", "")
        final_url = response.geturl()
        http_status = response.status
        media_type = response.headers.get("Content-Type", "")

    if "gzip" in content_encoding.lower():
        body = gzip.decompress(body)

    return Fetched(
        body=body,
        source_url=url,
        final_url=final_url,
        http_status=http_status,
        media_type=media_type,
        byte_size=len(body),
    )


def structure_url(as_of: date, title: int = 40) -> str:
    """Build the eCFR title structure endpoint URL."""

    return f"https://www.ecfr.gov/api/versioner/v1/structure/{as_of.isoformat()}/title-{title}.json"


def part_xml_url(as_of: date, title: int = 40, part: int = 63) -> str:
    """Build the eCFR full-title XML endpoint URL for one Part."""

    return f"https://www.ecfr.gov/api/versioner/v1/full/{as_of.isoformat()}/title-{title}.xml?part={part}"


__all__ = ["Fetched", "ensure_xml", "fetch", "part_xml_url", "structure_url"]
