"""SUU-52: Control Number 하나의 ADI 회신 원문을 받아 PDF 여부를 판별한다.

네트워크는 쓰지 않는다. request 를 가짜로 넣는다. `.cfm` 주소가 실제로는 PDF/HTML 어느 쪽도
줄 수 있으므로, Content-Type이 아니라 파일 시작부(매직바이트 `%PDF`)로 PDF 여부를 정한다.
"""
from __future__ import annotations

from adi_letters import FILE_URL, fetch_letter

PDF_BODY = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n%%EOF"
NOT_PDF_BODY = b"<html><body>Not Found</body></html>"


class FakeResponse:
    def __init__(self, body: bytes, media_type: str = "application/pdf"):
        self.body = body
        self.final_url = "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M200005"
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

    letter = fetch_letter("M200005", request=request)

    assert letter["is_pdf"] is True
    assert letter["body"] == PDF_BODY
    assert letter["control_number"] == "M200005"
    assert letter["byte_size"] == len(PDF_BODY)


def test_flags_false_when_body_is_not_pdf_even_if_content_type_says_pdf():
    # .cfm 주소가 Content-Type은 pdf라 해놓고 실제로는 HTML을 줄 수 있다 — 매직바이트가 최종 판단
    request = fake_request(NOT_PDF_BODY, media_type="application/pdf")

    letter = fetch_letter("Z900001", request=request)

    assert letter["is_pdf"] is False


def test_requests_the_file_contents_endpoint_for_the_control_number():
    request = fake_request(PDF_BODY)

    fetch_letter("1800013", request=request)

    assert request.calls == [(FILE_URL + "1800013", None)]
