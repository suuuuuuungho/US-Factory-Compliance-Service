"""Walk the ADI search forms and fetch the results page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Callable
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener as _build_opener


HOME_URL = "https://cfpub.epa.gov/adi/"

_TAG = re.compile(
    r'''<(form|input)\b((?:\s+[\w-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*/?>''',
    re.I,
)
_ATTR = re.compile(
    r'''([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))'''
)
_FORM_END = re.compile(r"</form\s*>", re.I)
_CRITERIA = (
    ("fuseaction", "home.dsp_review_critieria"),
    ("controlnumvalue", ""),
    ("recentupdatevalue", "ALL"),
    ("categoryvalue", None),
    ("regionvalue", "ALL"),
    ("begindate", ""),
    ("enddate", ""),
    ("letterauthortext", ""),
    ("wordsearchtext", ""),
    ("subpartvalue", "ALL"),
    ("cfrvalue", "ALL"),
)


@dataclass(frozen=True)
class _Response:
    body: bytes
    final_url: str
    http_status: int
    media_type: str
    byte_size: int


def build_opener():
    """Return an opener that retains ADI session cookies between requests."""

    return _build_opener(HTTPCookieProcessor(CookieJar()))


def _attributes(source: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for match in _ATTR.finditer(source):
        value = next(value for value in match.groups()[1:] if value is not None)
        attributes[match.group(1).lower()] = value
    return attributes


def _form(page: bytes, fuseaction: str) -> tuple[str, list[tuple[str, str]]]:
    source = page.decode("utf-8", errors="replace")

    for form_tag in _TAG.finditer(source):
        if form_tag.group(1).lower() != "form":
            continue
        form_end = _FORM_END.search(source, form_tag.end())
        if form_end is None:
            continue

        hidden: list[tuple[str, str]] = []
        for input_tag in _TAG.finditer(source, form_tag.end(), form_end.start()):
            if input_tag.group(1).lower() != "input":
                continue
            attributes = _attributes(input_tag.group(2))
            if attributes.get("type", "").lower() != "hidden":
                continue
            name = attributes.get("name")
            if name is not None:
                hidden.append((name, attributes.get("value", "")))

        if ("fuseaction", fuseaction) in hidden:
            action = _attributes(form_tag.group(2)).get("action")
            if action:
                return action, hidden

    raise ValueError(f"ADI form not found: {fuseaction}")


def _default_requester() -> Callable[..., _Response]:
    opener = build_opener()

    def request(url: str, data: list[tuple[str, str]] | None = None) -> _Response:
        encoded = urlencode(data, doseq=True).encode("utf-8") if data is not None else None
        http_request = Request(
            url,
            data=encoded,
            headers={"User-Agent": "US-Factory-Compliance-Service/1.0"},
            method="POST" if data is not None else "GET",
        )
        with opener.open(http_request, timeout=180) as response:
            body = response.read()
            return _Response(
                body=body,
                final_url=response.geturl(),
                http_status=response.status,
                media_type=response.headers.get("Content-Type", ""),
                byte_size=len(body),
            )

    return request


def fetch_results(
    category: str = "ALL", *, request: Callable[..., Any] | None = None
) -> dict[str, Any]:
    """Return the ADI result HTML and response metadata for ``category``."""

    requester = request or _default_requester()
    home = requester(HOME_URL)
    home_action, _ = _form(home.body, "home.dsp_review_critieria")
    criteria = [
        (name, category if value is None else value) for name, value in _CRITERIA
    ]
    review = requester(urljoin(HOME_URL, home_action), criteria)
    review_action, hidden = _form(review.body, "home.dsp_show_results_table")
    source_url = urljoin(HOME_URL, review_action)
    results = requester(source_url, hidden)

    return {
        "body": results.body,
        "source_url": source_url,
        "final_url": results.final_url,
        "http_status": results.http_status,
        "media_type": results.media_type,
        "byte_size": results.byte_size,
    }
