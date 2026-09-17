"""Parse the EPA ECHO program-code dictionary into versioned JSONL rows."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if len(self._row) == 3:
                self.rows.append(self._row)
            self._row = None


def parse_code_table(html: str, *, version: str, source_url: str) -> list[dict]:
    """Return ECHO code-map rows from every three-column HTML table row."""

    parser = _TableParser()
    parser.feed(html)
    rows = []
    for program_code, subpart_code, description in parser.rows:
        match = re.search(r"Part (\d+) - Subpart ([A-Za-z0-9]+)", description)
        part, subpart = match.groups() if match else (None, None)
        rows.append({
            "program_code": program_code,
            "raw_subpart_code": subpart_code,
            "raw_description": description,
            "cfr_title": "40" if match else None,
            "cfr_part": part,
            "cfr_subpart": subpart,
            "review_status": "ok" if match else "unresolved",
            "dictionary_version": version,
            "source_url": source_url,
        })
    descriptions: dict[str, set[str]] = {}
    for row in rows:
        descriptions.setdefault(row["raw_subpart_code"], set()).add(row["raw_description"])
    for row in rows:
        if len(descriptions[row["raw_subpart_code"]]) > 1:
            row["review_status"] = "conflict"
    return rows


def write_code_map(root: Path, version: str, rows: list[dict]) -> Path:
    """Write code-map rows to the versioned JSONL artifact path."""

    path = root / "code_map" / version / "echo_code_map.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path
