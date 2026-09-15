"""Fetch ADI detail metadata by resubmitting a saved results form."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urljoin

from adi_fetch import _default_requester, _form


def fetch_details(
    results_html: bytes,
    results_source_url: str,
    control_numbers: list[str],
    *,
    request: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Return details for selected ADI control numbers."""

    if not control_numbers:
        return {
            "body": b"",
            "source_url": results_source_url,
            "final_url": results_source_url,
            "http_status": None,
            "media_type": "",
            "byte_size": 0,
        }

    requester = request or _default_requester()
    action, hidden = _form(results_html, "home.dsp_show_results")
    fields = list(hidden) + [
        ("control_number", control_number)
        for control_number in control_numbers
    ]
    source_url = urljoin(results_source_url, action)
    response = requester(source_url, fields)

    return {
        "body": response.body,
        "source_url": source_url,
        "final_url": response.final_url,
        "http_status": response.http_status,
        "media_type": response.media_type,
        "byte_size": response.byte_size,
    }


__all__ = ["fetch_details"]
