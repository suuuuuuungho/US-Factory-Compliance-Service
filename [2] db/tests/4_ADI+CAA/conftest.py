"""4_ADI+CAA 테스트 공용 fixture.

make_pdf: 페이지별 글자를 넣은 진짜 PDF 바이트를 즉석에서 만든다(디스크 fixture 없이).
None 인 페이지는 글자 없는 빈 페이지가 된다.
"""
from __future__ import annotations

import io

import pytest


def _make_pdf(page_texts: list[str | None]) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=200, height=200)
        if text is None:
            continue

        font = DictionaryObject()
        font[NameObject("/Type")] = NameObject("/Font")
        font[NameObject("/Subtype")] = NameObject("/Type1")
        font[NameObject("/BaseFont")] = NameObject("/Helvetica")
        font_ref = writer._add_object(font)

        resources = DictionaryObject()
        fontdict = DictionaryObject()
        fontdict[NameObject("/F1")] = font_ref
        resources[NameObject("/Font")] = fontdict
        page[NameObject("/Resources")] = resources

        content = DecodedStreamObject()
        content.set_data(f"BT /F1 24 Tf 10 100 Td ({text}) Tj ET".encode("latin-1"))
        content_ref = writer._add_object(content)
        page[NameObject("/Contents")] = content_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def make_pdf():
    return _make_pdf
