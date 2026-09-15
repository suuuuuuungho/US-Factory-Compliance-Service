"""SUU-60: 저장된 Dashboard 회신 PDF 하나를 받아 페이지별 텍스트를 뽑는다.

SUU-59(ADI 쪽)와 대칭. PDF 형식은 같으므로 같은 방식으로 검증한다.
"""
from __future__ import annotations

import io

from dashboard_letters_text import extract_pages


def _make_pdf(page_texts: list[str | None]) -> bytes:
    """page_texts 의 각 항목으로 PDF 페이지를 만든다. None이면 글자 없는 빈 페이지."""
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


def test_extracts_text_per_page_from_a_digital_pdf():
    pdf_bytes = _make_pdf(["Hello Dashboard", None])

    pages = extract_pages(pdf_bytes)

    assert len(pages) == 2
    assert pages[0] == {"page_no": 1, "text": "Hello Dashboard", "status": "ok"}
    assert pages[1] == {"page_no": 2, "text": "", "status": "empty"}


def test_failing_page_is_marked_failed_and_does_not_stop_the_rest():
    class FakePage:
        def __init__(self, text: str, should_fail: bool):
            self._text = text
            self._should_fail = should_fail

        def extract_text(self) -> str:
            if self._should_fail:
                raise ValueError("corrupted content stream")
            return self._text

    class FakeReader:
        def __init__(self, pdf_bytes: bytes):
            self.pages = [
                FakePage("first page text", should_fail=False),
                FakePage("", should_fail=True),
                FakePage("third page text", should_fail=False),
            ]

    pages = extract_pages(b"not a real pdf", reader_factory=FakeReader)

    assert [p["status"] for p in pages] == ["ok", "failed", "ok"]
    assert pages[1]["text"] == ""
    assert pages[1]["reason"] == "corrupted content stream"
    assert pages[2]["text"] == "third page text"
