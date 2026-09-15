"""Fetch the CAA Dashboard page with one GET request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DASHBOARD_URL = (
    "https://www.epa.gov/complying-air-emissions-standards-stationary-sources"
    "/epa-determinations-compliance-and"
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


def fetch_dashboard(*, request: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Return the CAA Dashboard HTML and response metadata."""

    requester = request or _default_requester()
    response = requester(DASHBOARD_URL)
    return {
        "body": response.body,
        "source_url": DASHBOARD_URL,
        "final_url": response.final_url,
        "http_status": response.http_status,
        "media_type": response.media_type,
        "byte_size": response.byte_size,
    }


__all__ = ["DASHBOARD_URL", "fetch_dashboard"]
