"""SUU-103: ECHO 셀 값 변환 규칙 — 날짜·결측·금액·다중 코드.

값은 실제 ZIP에서 관찰한 모양이다 (2026-09-17 raw).
- 날짜: 대부분 ``06/24/2004``, VIOLATION_HISTORY 만 ``05-04-2004``
- 결측: ``""``, ``N/A`` (Pipeline VIOL_END_DATE), ``-9999`` (Pipeline EVAL_ACTIVITY_ID)
- 금액: ``0``, ``657412``, ``103449.5`` — 빈값과 0 을 구분
- 다중 코드: 공백 구분 ``3541 3545``, ``CAANSPS CAASIP``, ``7003 300000319 300000329``
"""
from datetime import date
from decimal import Decimal

import pytest

from echo_values import is_missing, parse_amount, parse_date, split_codes


def test_parse_date_accepts_both_us_formats_and_rejects_the_rest():
    assert parse_date("05-04-2004") == date(2004, 5, 4)  # MM-DD-YYYY (VIOLATION_HISTORY)
    assert parse_date("06/24/2004") == date(2004, 6, 24)  # MM/DD/YYYY (나머지 전부)
    assert parse_date(" 03/08/2007 ") == date(2007, 3, 8)  # 앞뒤 공백은 무시

    for raw in ("", "N/A", "Unresolved", "Unresolved (Addressed)", "2004-05-04", "24/06/2004", "13/45/2004", "6/4/04"):
        assert parse_date(raw) is None, raw  # 모호하거나 다른 형식은 None — 원문은 호출자가 그대로 남긴다



# SUU-270: 원본의 가짜 날짜(1900년 전, 2100년 후)는 날짜로 믿지 않는다. 원문은 호출자가 raw 칸에 남긴다

def test_parse_date_returns_none_for_fake_dates_before_1900_or_from_2100():
    for raw in ("01/01/0001", "01/01/8888", "11/02/0215", "12/31/1899", "01/01/2100", "11-12-2104"):
        assert parse_date(raw) is None, raw


def test_parse_date_keeps_boundary_and_near_future_dates():
    assert parse_date("01/01/1900") == date(1900, 1, 1)
    assert parse_date("12/31/2099") == date(2099, 12, 31)
    assert parse_date("11/07/2027") == date(2027, 11, 7)  # 계획 중인 시설일 수 있어 그대로 둔다

def test_missing_markers_and_amount_keeps_zero_apart_from_empty():
    assert is_missing("") is True
    assert is_missing("   ") is True
    assert is_missing("N/A") is True
    assert is_missing("-9999") is True
    assert is_missing("0") is False
    assert is_missing("445110") is False

    assert parse_amount("") is None
    assert parse_amount("N/A") is None
    assert parse_amount("0") == Decimal("0")
    assert parse_amount("657412") == Decimal("657412")
    assert parse_amount("103449.5") == Decimal("103449.5")
    assert isinstance(parse_amount("0"), Decimal)  # float 금지

    with pytest.raises(ValueError):
        parse_amount("abc")  # 숫자가 아니면 조용히 None 이 아니라 예외 → 호출자가 보류


def test_split_codes_splits_on_whitespace_and_empty_is_empty_list():
    assert split_codes("3541 3545") == ["3541", "3545"]
    assert split_codes("CAANSPS CAASIP CAATVP") == ["CAANSPS", "CAASIP", "CAATVP"]
    assert split_codes("7003  300000319 300000329") == ["7003", "300000319", "300000329"]  # 공백 여러 개
    assert split_codes("445110") == ["445110"]
    assert split_codes("") == []
    assert split_codes("N/A") == []
