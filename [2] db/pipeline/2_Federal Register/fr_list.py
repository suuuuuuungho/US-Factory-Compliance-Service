"""List Part 63 Federal Register documents."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlencode

from fr_fetch import Fetched, fetch as http_fetch


def list_url(end_date: date) -> str:
    query = urlencode({
        "per_page": 1000, "conditions[cfr][title]": 40,
        "conditions[cfr][part]": 63, "conditions[publication_date][gte]": "1994-01-01",
        "conditions[publication_date][lte]": end_date.isoformat(), "order": "oldest",
    })
    return f"https://www.federalregister.gov/api/v1/documents.json?{query}"


def _body(value: bytes | Fetched) -> bytes:
    return value.body if isinstance(value, Fetched) else value


def collect_list(root: Path, end_date: date, *, fetch=http_fetch) -> dict:
    """Follow API-provided next-page URLs and save their rows as JSONL."""

    url: str | None = list_url(end_date)
    rows: list[dict] = []
    pages = 0
    count: int | None = None
    while url:
        page = json.loads(_body(fetch(url)))
        pages += 1
        if count is None:
            count = page["count"]
        rows.extend(page["results"])
        url = page.get("next_page_url")
    if count != len(rows):
        raise ValueError(f"API count {count} does not match {len(rows)} rows")
    path = Path(root) / "raw" / "lists" / end_date.isoformat() / "documents.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return {"count": count, "pages": pages, "rows": rows}
