"""SUU-49: ADI 검색 폼 3단계(홈 GET → 조건확인 POST → 결과 POST)를 지나 결과 HTML을 받는다.

네트워크는 쓰지 않는다. 요청 함수를 가짜로 주입해 저장된 홈·확인·결과 페이지를 돌려주고,
보낸 요청의 주소·방식·본문을 검사한다. 결과 페이지는 SUU-48 fixture를 재사용한다.
"""
import re
from pathlib import Path

import pytest

from adi_fetch import fetch_results, HOME_URL

FIXTURES = Path(__file__).parent / "fixtures"
HOME = (FIXTURES / "adi_home_form.html").read_bytes()
REVIEW = (FIXTURES / "adi_review_form.html").read_bytes()
RESULTS = (FIXTURES / "adi_results_sample.html").read_bytes()

HOME_ACTION = "https://cfpub.epa.gov/adi/index.cfm?CFID=34967852&CFTOKEN=1871e1bbf8a9d592-68C8D577-020D-4F45-D77A7810BA97B295"
REVIEW_ACTION = "https://cfpub.epa.gov/adi/index.cfm?CFID=33954140&CFTOKEN=3401b853ef12a7b1-6619394B-0E98-8E9A-69789F8FC837D7C1&requesttimeout=180"


class FakeResponse:
    def __init__(self, body, url):
        self.body = body
        self.final_url = url
        self.http_status = 200
        self.media_type = "text/html;charset=UTF-8"
        self.byte_size = len(body)


class Recorder:
    """세 요청을 순서대로 home→review→results 로 돌려주고, 부른 (url, data) 를 남긴다."""

    def __init__(self, pages=(HOME, REVIEW, RESULTS)):
        self.pages = list(pages)
        self.calls = []

    def __call__(self, url, data=None):
        self.calls.append((url, data))
        body = self.pages[len(self.calls) - 1]
        return FakeResponse(body, url)


def test_walks_three_requests_in_order():
    request = Recorder()
    fetch_results(category="MACT", request=request)

    assert len(request.calls) == 3

    # 1. 홈 GET (본문 없음)
    url0, data0 = request.calls[0]
    assert url0 == HOME_URL == "https://cfpub.epa.gov/adi/"
    assert data0 is None

    # 2. 홈 폼 action 으로 POST. 세션 값이 붙은, 페이지에서 읽은 주소다
    url1, data1 = request.calls[1]
    assert url1 == HOME_ACTION
    fields1 = dict(data1)
    assert fields1["fuseaction"] == "home.dsp_review_critieria"
    assert fields1["categoryvalue"] == "MACT"      # 인자가 그대로 실린다

    # 3. 확인 폼 action 으로 POST
    url2, _ = request.calls[2]
    assert url2 == REVIEW_ACTION


def test_forwards_all_review_hidden_fields():
    request = Recorder()
    fetch_results(request=request)

    _, data2 = request.calls[2]
    pairs = list(data2)

    # 확인 페이지 <FORM>~</FORM> 의 hidden 43개를 이름·값 그대로 전부
    expected = re.findall(
        r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"[^>]*>',
        REVIEW.decode("utf-8"),
        re.I,
    )
    expected = [(n, v) for n, v in expected]  # hidden 만 담긴 fixture라 전부 hidden
    assert len(expected) == 43
    assert pairs == expected

    fields = dict(pairs)
    assert fields["fuseaction"] == "home.dsp_show_results_table"
    # 값 속 '>' 가 있어도 깨지지 않는다
    assert fields["category"] == "instr(category,'MACT') > 0"


def test_returns_results_body_and_metadata():
    request = Recorder()
    got = fetch_results(request=request)

    assert got["body"] == RESULTS
    assert got["source_url"] == REVIEW_ACTION
    assert got["final_url"] == REVIEW_ACTION
    assert got["http_status"] == 200
    assert got["media_type"] == "text/html;charset=UTF-8"
    assert got["byte_size"] == len(RESULTS)


def test_default_requester_keeps_cookies():
    # 기본 요청기는 CookieJar 를 가진 opener 라 세 요청에 세션 쿠키가 이어진다
    from http.cookiejar import CookieJar
    from urllib.request import HTTPCookieProcessor

    import adi_fetch

    opener = adi_fetch.build_opener()
    cookie_handlers = [h for h in opener.handlers if isinstance(h, HTTPCookieProcessor)]
    assert cookie_handlers
    assert isinstance(cookie_handlers[0].cookiejar, CookieJar)


def test_raises_when_form_missing():
    no_review_form = b"<html><body><p>maintenance</p></body></html>"
    with pytest.raises(ValueError):
        fetch_results(request=Recorder(pages=(no_review_form, REVIEW, RESULTS)))

    with pytest.raises(ValueError):
        fetch_results(request=Recorder(pages=(HOME, no_review_form, RESULTS)))
