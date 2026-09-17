"""Download ECHO ZIP files to disk while calculating their SHA-256 digest."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Fetched:
    """The local file and HTTP metadata returned by an ECHO download."""

    path: Path
    sha256: str
    source_url: str
    final_url: str
    http_status: int
    media_type: str
    etag: str | None
    last_modified: str | None
    byte_size: int


def fetch_to_file(url: str, dest: Path, *, chunk_size: int = 1 << 20) -> Fetched:
    """Stream *url* to *dest*, returning its digest and response metadata."""

    part = Path(str(dest) + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"Accept": "application/zip"}, method="GET")
    digest = hashlib.sha256()
    byte_size = 0

    try:
        with urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            http_status = response.status
            media_type = response.headers.get("Content-Type", "")
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")

            with part.open("wb") as output:
                first_chunk = True
                while chunk := response.read(chunk_size):
                    if first_chunk and chunk.lstrip().lower().startswith(
                        (b"<!doctype html", b"<html")
                    ):
                        raise ValueError("ECHO response is HTML, not ZIP")
                    first_chunk = False
                    output.write(chunk)
                    digest.update(chunk)
                    byte_size += len(chunk)

        os.replace(str(part), str(dest))
    except Exception:
        part.unlink(missing_ok=True)
        raise

    return Fetched(
        path=dest,
        sha256=digest.hexdigest(),
        source_url=url,
        final_url=final_url,
        http_status=http_status,
        media_type=media_type,
        etag=etag,
        last_modified=last_modified,
        byte_size=byte_size,
    )
