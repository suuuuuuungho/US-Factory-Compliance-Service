"""Read the eCFR title-level freshness metadata.

The eCFR versioner API publishes the dates for each title in ``titles`` and
the import status for the response as a whole in ``meta``.  This module keeps
that small bit of API handling separate from the later structure/XML ingest
steps so callers can decide whether it is safe to continue a refresh.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_TITLES_URL = "https://www.ecfr.gov/api/versioner/v1/titles.json"


@dataclass(frozen=True)
class TitleStatus:
    """Freshness metadata for one eCFR title."""

    up_to_date_as_of: date
    latest_amended_on: date
    latest_issue_date: date
    import_in_progress: bool


def _parse_date(value: Any, field_name: str) -> date:
    """Parse an API ISO date and give callers a useful error for bad input."""

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO date: {value!r}") from exc


def parse_title_status(titles_json: dict[str, Any], title: int = 40) -> TitleStatus:
    """Return freshness metadata for ``title`` from a titles API response.

    ``import_in_progress`` is deliberately read from the top-level ``meta``
    object: it describes the API import, not an individual title.  A missing
    title is an input error because using another title's date would make the
    subsequent XML snapshot ambiguous.
    """

    if not isinstance(titles_json, dict):
        raise ValueError("titles response must be a JSON object")

    titles = titles_json.get("titles")
    if not isinstance(titles, list):
        raise ValueError("titles response is missing a titles list")

    title_entry = next(
        (
            entry
            for entry in titles
            if isinstance(entry, dict) and entry.get("number") == title
        ),
        None,
    )
    if title_entry is None:
        raise ValueError(f"Title {title} is missing from the eCFR response")

    meta = titles_json.get("meta")
    if not isinstance(meta, dict):
        meta = {}

    return TitleStatus(
        up_to_date_as_of=_parse_date(
            title_entry.get("up_to_date_as_of"), "up_to_date_as_of"
        ),
        latest_amended_on=_parse_date(
            title_entry.get("latest_amended_on"), "latest_amended_on"
        ),
        latest_issue_date=_parse_date(
            title_entry.get("latest_issue_date"), "latest_issue_date"
        ),
        import_in_progress=bool(meta.get("import_in_progress", False)),
    )


def fetch_titles(url: str = DEFAULT_TITLES_URL) -> dict[str, Any]:
    """Fetch and decode the eCFR titles response.

    The API has returned HTTP 406 when clients did not advertise compression,
    so gzip is explicitly accepted and decoded according to the response
    header.  HTTP and JSON errors intentionally propagate to the refresh
    runner, where they can be recorded and retried.
    """

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
        method="GET",
    )
    with urlopen(request) as response:
        payload = response.read()
        content_encoding = response.headers.get("Content-Encoding", "")

    if "gzip" in content_encoding.lower():
        payload = gzip.decompress(payload)

    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("eCFR titles response must be a JSON object")
    return decoded


__all__ = ["DEFAULT_TITLES_URL", "TitleStatus", "fetch_titles", "parse_title_status"]
