"""Stream ECHO CSV members from ZIP archives as numbered dictionaries."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterator
import zipfile


def iter_rows(zip_path: Path, member: str) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield each CSV data row as a one-based number and header-keyed dict."""

    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as raw, io.TextIOWrapper(
        raw, encoding="utf-8-sig", newline=""
    ) as text:
        reader = csv.reader(text)
        header = next(reader)
        for number, row in enumerate(reader, start=1):
            yield number, dict(zip(header, row))
