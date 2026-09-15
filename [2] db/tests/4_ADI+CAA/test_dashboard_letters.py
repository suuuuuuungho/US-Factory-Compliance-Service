"""SUU-55: CAA Dashboard 한 행의 회신 원문(PDF)을 canonical_url로 받아 PDF 여부를 판별한다.

네트워크는 쓰지 않는다. request 를 가짜로 넣는다. ADI와 마찬가지로 Content-Type이 아니라
파일 시작부(매직바이트 %PDF)로 PDF 여부를 정한다.
"""
from __future__ import annotations

from dashboard_letters import fetch_letter

PDF_BODY = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n%%EOF"
NOT_PDF_BODY = b"<html><body>Not Found</body></html>"
CANONICAL_URL = "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"


class FakeResponse:
    def __init__(self, body: bytes, media_type: str = "application/pdf"):
        self.body = body
        self.final_url = CANONICAL_URL
        self.http_status = 200
        self.media_type = media_type
        self.byte_size = len(body)


def fake_request(body: bytes, media_type: str = "application/pdf"):
    calls: list[tuple[str, object]] = []

    def _request(url: str, data=None):
        calls.append((url, data))
        return FakeResponse(body, media_type)

    _request.calls = calls
    return _request


def test_flags_true_and_keeps_body_for_pdf_magic_bytes():
    request = fake_request(PDF_BODY)

    letter = fetch_letter(CANONICAL_URL, request=request)

    assert letter["is_pdf"] is True
    assert letter["body"] == PDF_BODY
    assert letter["canonical_url"] == CANONICAL_URL
    assert letter["byte_size"] == len(PDF_BODY)


def test_flags_false_when_body_is_not_pdf_even_if_content_type_says_pdf():
    request = fake_request(NOT_PDF_BODY, media_type="application/pdf")

    letter = fetch_letter(CANONICAL_URL, request=request)

    assert letter["is_pdf"] is False


def test_requests_the_canonical_url_directly():
    request = fake_request(PDF_BODY)

    fetch_letter(CANONICAL_URL, request=request)

    assert request.calls == [(CANONICAL_URL, None)]
