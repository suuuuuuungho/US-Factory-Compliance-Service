"""SUU-94: ECHO ZIP을 디스크로 흘려 받으며 해시 계산.

네트워크는 쓰지 않는다. ``echo_fetch.urlopen``을 가짜로 바꾼다.
"""
import hashlib
import os
from email.message import Message

import pytest

import echo_fetch
from echo_fetch import fetch_to_file

ZIP = b"PK\x03\x04" + bytes(range(256)) * 40  # 10KB 남짓한 가짜 ZIP 바이트
HTML = b"<!DOCTYPE html><html><body>Access Denied</body></html>"


class FakeResponse:
    """urlopen()이 돌려주는 응답 흉내. read(n) / headers / geturl / status 만 있다."""

    def __init__(self, body, *, url, status=200, content_type="application/zip", etag=None, last_modified=None):
        self._body = body
        self._pos = 0
        self._url = url
        self.status = status
        self.read_sizes = []
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if etag:
            self.headers["ETag"] = etag
        if last_modified:
            self.headers["Last-Modified"] = last_modified

    def read(self, n=-1):
        self.read_sizes.append(n)
        if n is None or n < 0:
            chunk = self._body[self._pos:]
        else:
            chunk = self._body[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def install_fake(monkeypatch, response):
    def _urlopen(request, timeout=None):
        return response

    monkeypatch.setattr(echo_fetch, "urlopen", _urlopen)


def test_streams_chunks_to_part_file_then_renames(monkeypatch, tmp_path):
    response = FakeResponse(ZIP, url="https://x/a.zip")
    install_fake(monkeypatch, response)
    dest = tmp_path / "a.zip"

    replaced = []
    real_replace = os.replace

    def _replace(src, dst):
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _replace)

    got = fetch_to_file("https://x/a.zip", dest, chunk_size=4096)

    # 통째로 read() 하지 않고 조각 단위로 읽는다
    assert len(response.read_sizes) > 1
    assert all(n == 4096 for n in response.read_sizes)
    # .part 에 먼저 쓰고 이름을 바꾼다. 끝나면 .part 가 없다
    assert (str(dest) + ".part", str(dest)) in replaced
    assert not (tmp_path / "a.zip.part").exists()
    assert dest.read_bytes() == ZIP
    assert got.path == dest
    assert got.sha256 == hashlib.sha256(ZIP).hexdigest()


def test_returns_response_metadata(monkeypatch, tmp_path):
    install_fake(
        monkeypatch,
        FakeResponse(
            ZIP,
            url="https://echo.epa.gov/files/final.zip",
            etag='"abc123"',
            last_modified="Mon, 15 Sep 2026 03:12:00 GMT",
        ),
    )

    got = fetch_to_file("https://echo.epa.gov/files/start.zip", tmp_path / "a.zip")

    assert got.source_url == "https://echo.epa.gov/files/start.zip"
    assert got.final_url == "https://echo.epa.gov/files/final.zip"
    assert got.http_status == 200
    assert got.media_type == "application/zip"
    assert got.etag == '"abc123"'
    assert got.last_modified == "Mon, 15 Sep 2026 03:12:00 GMT"
    assert got.byte_size == len(ZIP)


def test_missing_etag_and_last_modified_are_none(monkeypatch, tmp_path):
    install_fake(monkeypatch, FakeResponse(ZIP, url="https://x/a.zip"))

    got = fetch_to_file("https://x/a.zip", tmp_path / "a.zip")

    assert got.etag is None
    assert got.last_modified is None


def test_rejects_html_and_leaves_no_part_file(monkeypatch, tmp_path):
    install_fake(monkeypatch, FakeResponse(HTML, url="https://x/a.zip", content_type="text/html"))
    dest = tmp_path / "a.zip"

    with pytest.raises(ValueError):
        fetch_to_file("https://x/a.zip", dest)

    assert not dest.exists()
    assert not (tmp_path / "a.zip.part").exists()
