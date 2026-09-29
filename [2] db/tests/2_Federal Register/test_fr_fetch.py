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


# ---- SUU-299: GitHub 러너에서 1,533건 중 1,149건이 HTTP 429(너무 많이 요청함)로 거절됐다

class _Response:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"{}"

    def geturl(self):
        return "https://x/a.json"


def _answers(monkeypatch, *answers):
    import fr_fetch

    calls = []

    def urlopen(request, timeout):
        calls.append(request.full_url)
        answer = answers[len(calls) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(fr_fetch, "urlopen", urlopen)
    return calls


def _too_many(url="https://x/a.json"):
    from urllib.error import HTTPError

    return HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)


def test_429_waits_and_tries_again(monkeypatch):
    from fr_fetch import fetch

    calls = _answers(monkeypatch, _too_many(), _too_many(), _Response())
    waits = []

    fetched = fetch("https://x/a.json", sleep=waits.append)

    assert fetched.body == b"{}"
    assert len(calls) == 3
    assert len(waits) == 2 and waits[0] < waits[1]  # 점점 더 오래 기다린다


def test_429_gives_up_after_a_few_tries(monkeypatch):
    from urllib.error import HTTPError

    from fr_fetch import fetch

    calls = _answers(monkeypatch, *[_too_many()] * 10)

    with pytest.raises(HTTPError) as info:
        fetch("https://x/a.json", sleep=lambda s: None)

    assert info.value.code == 429
    assert 2 <= len(calls) < 10  # 끝없이 매달리지 않는다


def test_other_http_errors_are_not_retried(monkeypatch):
    from urllib.error import HTTPError

    from fr_fetch import fetch

    calls = _answers(monkeypatch, HTTPError("https://x/a.json", 404, "Not Found", hdrs=None, fp=None), _Response())

    with pytest.raises(HTTPError):
        fetch("https://x/a.json", sleep=lambda s: None)

    assert len(calls) == 1
