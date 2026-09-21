"""HTTP helpers for Federal Register raw-document collection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class FormatMismatch(ValueError):
    """A response did not have the format promised by its URL."""


@dataclass(frozen=True)
class Fetched:
    body: bytes
    source_url: str
    final_url: str
    http_status: int
    media_type: str
    byte_size: int
    sha256: str


def fetch(url: str) -> Fetched:
    """Download *url* into memory, retaining response metadata."""

    request = Request(url, method="GET")
    with urlopen(request, timeout=60) as response:
        body = response.read()
        return Fetched(
            body=body,
            source_url=url,
            final_url=response.geturl(),
            http_status=response.status,
            media_type=response.headers.get("Content-Type", ""),
            byte_size=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
        )


def detail_url(document_number: str, publication_date: str) -> str:
    query = urlencode({"publication_date": publication_date})
    return f"https://www.federalregister.gov/api/v1/documents/{document_number}.json?{query}"


def check_format(body: bytes, kind: str) -> None:
    """Reject HTML or malformed data before it can be archived as raw data."""

    start = body.lstrip().lower()
    valid = {
        "json": start.startswith((b"{", b"[")),
        "xml": start.startswith(b"<") and not start.startswith((b"<!doctype html", b"<html")),
        "pdf": start.startswith(b"%pdf-"),
    }
    if not valid.get(kind, False):
        actual = "html" if start.startswith((b"<!doctype html", b"<html")) else "unexpected format"
        raise FormatMismatch(f"{kind} expected, got {actual}")
