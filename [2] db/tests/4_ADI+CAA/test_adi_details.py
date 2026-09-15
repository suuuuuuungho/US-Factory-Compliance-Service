"""SUU-57: 저장된 ADI 결과 HTML의 hidden 필드를 재사용해 여러 Control Number를
체크박스로 다시 제출하고("View Details" 버튼과 같은 동작), 상세 응답 HTML을 받는다.

네트워크는 쓰지 않는다. request 를 가짜로 넣는다. 실제 사이트에서 확인한 사실:
- "View Details"는 별도 페이지가 아니라 결과 목록 폼(this_form, fuseaction=home.dsp_show_results)을
  체크된 control_number 값들과 함께 그대로 재제출하는 것이다.
- 결과 목록 HTML 자체가 이미 그 폼(hidden 필드 전부)을 담고 있다 — adi_results_sample.html 재사용.
- 잘못된 필드(determination/downloadList)만 채우면 서버가 "zero determinations"를 돌려준다.
  실제 체크박스 필드인 control_number(반복 가능)를 채워야 한다.
"""
from __future__ import annotations

from pathlib import Path

from adi_details import fetch_details

FIXTURE = Path(__file__).parent / "fixtures" / "adi_results_sample.html"
RESULTS_HTML = FIXTURE.read_bytes()
RESULTS_SOURCE_URL = (
    "https://cfpub.epa.gov/adi/index.cfm?CFID=1&CFTOKEN=1&requesttimeout=180"
)


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body
        self.final_url = RESULTS_SOURCE_URL
        self.http_status = 200
        self.media_type = "text/html"
        self.byte_size = len(body)


def fake_request(body: bytes = b"<html></html>"):
    calls: list[tuple[str, object]] = []

    def _request(url: str, data=None):
        calls.append((url, data))
        return FakeResponse(body)

    _request.calls = calls
    return _request


def test_resubmits_results_form_with_checked_control_numbers():
    request = fake_request()

    fetch_details(RESULTS_HTML, RESULTS_SOURCE_URL, ["M200005", "1800013"], request=request)

    assert len(request.calls) == 1
    url, fields = request.calls[0]
    assert url.startswith(RESULTS_SOURCE_URL.split("?")[0])

    field_names = [name for name, _ in fields]
    assert ("fuseaction", "home.dsp_show_results") in fields
    assert field_names.count("control_number") == 2
    assert ("control_number", "M200005") in fields
    assert ("control_number", "1800013") in fields


def test_returns_response_envelope_with_body_and_metadata():
    request = fake_request(b"<html>detail body</html>")

    result = fetch_details(RESULTS_HTML, RESULTS_SOURCE_URL, ["M200005"], request=request)

    assert result["body"] == b"<html>detail body</html>"
    assert result["http_status"] == 200
    assert result["media_type"] == "text/html"
    assert result["byte_size"] == len(b"<html>detail body</html>")


def test_no_network_request_for_empty_control_number_list():
    request = fake_request()

    fetch_details(RESULTS_HTML, RESULTS_SOURCE_URL, [], request=request)

    assert request.calls == []
