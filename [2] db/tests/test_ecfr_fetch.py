"""SUU-36: Part 63 원문 XML 받기 — gzip 풀기, HTML 응답 거르기, 응답 정보 돌려주기.

네트워크는 쓰지 않는다. ``ecfr_fetch.urlopen``을 가짜로 바꾼다.
"""
import gzip
from datetime import date
from email.message import Message

import pytest

import ecfr_fetch
from ecfr_fetch import ensure_xml, fetch, part_xml_url, structure_url

XML = b'<?xml version="1.0"?><DIV5 N="63" TYPE="PART"><HEAD>PART 63</HEAD></DIV5>'
HTML = b"<!DOCTYPE html><html><body>Checking your browser before accessing</body></html>"


class FakeResponse:
    """urlopen()이 돌려주는 응답 흉내. read / headers / geturl / status 만 있다."""

    def __init__(self, body, *, url, status=200, content_type="application/xml", encoding=None):
        self._body = body
        self._url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if encoding:
            self.headers["Content-Encoding"] = encoding

    def read(self):
        return self._body

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_fake(monkeypatch, response, seen):
    def _urlopen(request, timeout=None):
        seen.append(request)
        return response

    monkeypatch.setattr(ecfr_fetch, "urlopen", _urlopen)


def test_decompresses_gzip_body(monkeypatch):
    seen = []
    install_fake(monkeypatch, FakeResponse(gzip.compress(XML), url="https://x/a.xml", encoding="gzip"), seen)

    got = fetch("https://x/a.xml")

    assert got.body == XML
    assert seen[0].get_header("Accept-encoding") == "gzip"


def test_rejects_html_body_even_with_200(monkeypatch):
    install_fake(monkeypatch, FakeResponse(HTML, url="https://x/a.xml", status=200, content_type="text/html"), [])

    got = fetch("https://x/a.xml")
    assert got.http_status == 200  # 받기 자체는 성공

    with pytest.raises(ValueError):
        ensure_xml(got.body)  # 하지만 XML로 인정하지 않는다
    with pytest.raises(ValueError):
        ensure_xml(b"\n  <HTML><body/></HTML>")  # 앞 공백·대문자도 같다
    assert ensure_xml(XML) == XML


def test_returns_final_url_status_type_and_size(monkeypatch):
    install_fake(
        monkeypatch,
        FakeResponse(XML, url="https://www.ecfr.gov/final.xml", content_type="application/xml; charset=utf-8"),
        [],
    )

    got = fetch("https://www.ecfr.gov/start.xml")

    assert got.source_url == "https://www.ecfr.gov/start.xml"
    assert got.final_url == "https://www.ecfr.gov/final.xml"
    assert got.http_status == 200
    assert got.media_type == "application/xml; charset=utf-8"
    assert got.byte_size == len(XML)


def test_builds_structure_and_part_xml_urls():
    as_of = date(2026, 9, 10)

    assert structure_url(as_of) == "https://www.ecfr.gov/api/versioner/v1/structure/2026-09-10/title-40.json"
    assert part_xml_url(as_of) == "https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63"
