from __future__ import annotations

import io
from typing import Any, Callable

from pypdf import PdfReader


def _default_reader(pdf_bytes: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf_bytes))


def extract_pages(
    pdf_bytes: bytes,
    *,
    reader_factory: Callable[[bytes], Any] = _default_reader,
) -> list[dict[str, Any]]:
    reader = reader_factory(pdf_bytes)
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages):
        page_no = index + 1
        try:
            text = page.extract_text() or ""
        except Exception as error:
            pages.append(
                {
                    "page_no": page_no,
                    "text": "",
                    "status": "failed",
                    "reason": str(error),
                }
            )
            continue
        status = "ok" if text.strip() else "empty"
        pages.append({"page_no": page_no, "text": text, "status": status})
    return pages


__all__ = ["extract_pages"]
