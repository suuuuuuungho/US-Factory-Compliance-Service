"""SUU-51: CAA Dashboard 페이지를 GET 한 번으로 받는다. ADI 3단계 폼과 다르다.

네트워크는 쓰지 않는다. request 를 가짜로 넣어 부른 주소·방식과 돌려주는 dict 를 검사한다.
"""
from __future__ import annotations

from pathlib import Path

from dashboard_fetch import DASHBOARD_URL, fetch_dashboard

FIXTURE = Path(__file__).parent / "fixtures" / "adi_dashboard_sample.html"
BODY = FIXTURE.read_bytes()


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body
        self.final_url = DASHBOARD_URL
        self.http_status = 200
        self.media_type = "text/html;charset=UTF-8"
        self.byte_size = len(body)


class Recorder:
    """호출된 (url, data) 를 남기고 항상 같은 body 를 돌려준다."""

    def __init__(self, body: bytes = BODY):
        self.body = body
        self.calls: list[tuple[str, object]] = []

    def __call__(self, url: str, data=None):
        self.calls.append((url, data))
        return FakeResponse(self.body)


def test_makes_single_get_request_to_dashboard_url():
    recorder = Recorder()

    fetch_dashboard(request=recorder)

    assert recorder.calls == [(DASHBOARD_URL, None)]


def test_returns_body_and_metadata():
    recorder = Recorder()

    result = fetch_dashboard(request=recorder)

    assert result == {
        "body": BODY,
        "source_url": DASHBOARD_URL,
        "final_url": DASHBOARD_URL,
        "http_status": 200,
        "media_type": "text/html;charset=UTF-8",
        "byte_size": len(BODY),
    }
