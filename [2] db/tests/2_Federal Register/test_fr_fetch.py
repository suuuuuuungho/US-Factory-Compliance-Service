"""SUU-206: 상세 JSON·XML·PDF 주소를 만들고, 받은 바이트의 실제 형식이 기대와 맞는지 검사한다.

네트워크 없음. fetch() 자체는 urlopen 을 쓰므로 여기서는 URL 조립과 형식 검사만 본다.
"""
import hashlib

import pytest

from fr_fetch import Fetched, FormatMismatch, check_format, detail_url


def test_detail_url_pins_publication_date():
    # 번호만 넣으면 서버가 아무 발행본이나 주므로 (03-5521 → 2003-08-28) 발행일을 꼭 붙인다
    url = detail_url("03-5521", "2003-05-27")
    assert url == "https://www.federalregister.gov/api/v1/documents/03-5521.json?publication_date=2003-05-27"


def test_fetched_carries_sha256_of_body():
    body = b'{"document_number": "2026-03638"}'
    fetched = Fetched(
        body=body, source_url="https://x/a.json", final_url="https://x/a.json",
        http_status=200, media_type="application/json", byte_size=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
    )
    assert fetched.sha256 == hashlib.sha256(body).hexdigest()
    assert fetched.byte_size == len(body)


@pytest.mark.parametrize(
    "kind, body",
    [
        ("json", b'  {"document_number": "2026-03638"}'),
        ("xml", b"<RULE>\n<PREAMB/></RULE>"),
        ("xml", b'<?xml version="1.0"?><RULE/>'),
        ("pdf", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3"),
    ],
)
def test_check_format_accepts_real_shapes(kind, body):
    assert check_format(body, kind) is None


@pytest.mark.parametrize(
    "kind, body",
    [
        ("xml", b"<!DOCTYPE html><html><body>Sign in</body></html>"),
        ("xml", b"<html><head></head></html>"),
        ("pdf", b"<!DOCTYPE html><html>Not Found</html>"),
        ("json", b"<html>rate limited</html>"),
        ("pdf", b"%PDF"[:2]),
    ],
)
def test_check_format_rejects_html_in_place_of_xml_pdf_json(kind, body):
    with pytest.raises(FormatMismatch) as info:
        check_format(body, kind)
    assert kind in str(info.value)
