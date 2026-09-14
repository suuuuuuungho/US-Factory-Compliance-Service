"""SUU-31: eCFR 제목 API(titles.json)에서 Title 40 반영 기준일 읽기.

샘플은 2026-09-14에 받은 실제 응답이다. 네트워크는 쓰지 않는다.
"""
import copy
import json
from datetime import date
from pathlib import Path

import pytest

from ecfr_titles import parse_title_status

FIXTURE = Path(__file__).parent / "fixtures" / "ecfr_titles.json"


def load_sample() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_title_40_dates_and_flag():
    status = parse_title_status(load_sample(), title=40)

    assert status.up_to_date_as_of == date(2026, 9, 10)
    assert status.latest_amended_on == date(2026, 9, 9)
    assert status.latest_issue_date == date(2026, 9, 9)
    assert status.import_in_progress is False


def test_keeps_import_in_progress_true():
    sample = copy.deepcopy(load_sample())
    sample["meta"]["import_in_progress"] = True

    status = parse_title_status(sample, title=40)

    assert status.import_in_progress is True


def test_raises_when_title_missing():
    sample = copy.deepcopy(load_sample())
    sample["titles"] = [t for t in sample["titles"] if t["number"] != 40]

    with pytest.raises(ValueError, match="40"):
        parse_title_status(sample, title=40)
