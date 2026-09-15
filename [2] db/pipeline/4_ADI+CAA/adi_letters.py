"""Fetch one ADI response document and identify PDF content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FILE_URL = (
    "https://cfpub.epa.gov/adi/index.cfm?"
    "fuseaction=home.dsp_show_file_contents&id="
)


@dataclass(frozen=True)
class _Response:
    body: bytes
    final_url: str
    http_status: int
    media_type: str
    byte_size: int


def _default_requester() -> Callable[..., _Response]:
    def request(url: str, data: list[tuple[str, str]] | None = None) -> _Response:
        encoded = urlencode(data, doseq=True).encode("utf-8") if data is not None else None
        http_request = Request(
            url,
            data=encoded,
            headers={"User-Agent": "US-Factory-Compliance-Service/1.0"},
            method="POST" if data is not None else "GET",
        )
        with urlopen(http_request, timeout=180) as response:
            body = response.read()
            return _Response(
                body=body,
                final_url=response.geturl(),
                http_status=response.status,
                media_type=response.headers.get("Content-Type", ""),
                byte_size=len(body),
            )

    return request


def fetch_letter(
    control_number: str, *, request: Callable[..., Any] | None = None
) -> dict[str, Any]:
    """Return one ADI response document and whether its bytes are a PDF."""

    requester = request or _default_requester()
    source_url = FILE_URL + control_number
    response = requester(source_url)
    return {
        "control_number": control_number,
        "body": response.body,
        "source_url": source_url,
        "final_url": response.final_url,
        "http_status": response.http_status,
        "media_type": response.media_type,
        "byte_size": response.byte_size,
        "is_pdf": response.body.lstrip()[:4] == b"%PDF",
    }


__all__ = ["FILE_URL", "fetch_letter"]
