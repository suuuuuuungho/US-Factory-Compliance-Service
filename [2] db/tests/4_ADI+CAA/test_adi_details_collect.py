"""SUU-57: 여러 Control Number의 상세 메타데이터를 청크로 나눠 가져오고,
성공/실패를 run.json에, 파싱된 행을 details.json에 남긴다.

네트워크는 쓰지 않는다. fetch_details 를 가짜로 주입한다. pytest tmp_path 를 root 로 쓴다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from adi_details_collect import collect

TODAY = date(2026, 9, 15)
RESULTS_HTML = b"<html>fake results form</html>"
RESULTS_SOURCE_URL = "https://cfpub.epa.gov/adi/index.cfm?CFID=1&CFTOKEN=1&requesttimeout=180"


def _row(control_number: str) -> dict:
    return {
        "control_number": control_number,
        "title": f"Title for {control_number}",
        "letter_date_raw": "01/01/2020",
        "author": "Someone",
        "categories": ["MACT"],
        "office": "Region 5",
        "abstract": "Q: ...\nA: ...",
    }


def fake_fetch_details(rows_by_control: dict[str, dict], fail_for: set[str] | None = None):
    fail_for = fail_for or set()
    calls: list[list[str]] = []

    def _fetch_details(results_html, results_source_url, control_numbers, **kwargs):
        calls.append(list(control_numbers))
        if fail_for & set(control_numbers):
            raise TimeoutError("server too slow")
        body = json.dumps([rows_by_control[cn] for cn in control_numbers]).encode("utf-8")
        return {"body": body, "source_url": results_source_url, "final_url": results_source_url,
                "http_status": 200, "media_type": "text/html", "byte_size": len(body)}

    _fetch_details.calls = calls
    return _fetch_details


def fake_parse_details(monkeypatch):
    # adi_details_collect 는 fetch_details 가 돌려준 body(JSON)를 parse_details 로 파싱한다.
    # 여기서는 fetch_details 가 이미 dict 형태의 행을 JSON으로 직렬화해 두었으므로
    # parse_details 를 json.loads 로 바꿔치기해서 collect() 의 청크/집계 로직만 검증한다.
    import adi_details_collect

    monkeypatch.setattr(adi_details_collect, "parse_details", lambda body: json.loads(body))


def test_collects_all_rows_in_one_chunk_when_under_chunk_size(tmp_path, monkeypatch):
    fake_parse_details(monkeypatch)
    control_numbers = ["M200005", "1800013", "1800038"]
    rows_by_control = {cn: _row(cn) for cn in control_numbers}
    fetch_details = fake_fetch_details(rows_by_control)

    run = collect(
        tmp_path, RESULTS_HTML, RESULTS_SOURCE_URL, control_numbers,
        fetch_details=fetch_details, today=TODAY, chunk_size=100,
    )

    assert run["requested"] == 3
    assert run["succeeded"] == 3
    assert run["failed"] == 0
    assert len(fetch_details.calls) == 1
    assert fetch_details.calls[0] == control_numbers

    details = json.loads((tmp_path / "raw" / TODAY.isoformat() / "details.json").read_text(encoding="utf-8"))
    assert [row["control_number"] for row in details] == control_numbers


def test_splits_into_chunks_of_chunk_size(tmp_path, monkeypatch):
    fake_parse_details(monkeypatch)
    control_numbers = ["A1", "A2", "A3", "A4", "A5"]
    rows_by_control = {cn: _row(cn) for cn in control_numbers}
    fetch_details = fake_fetch_details(rows_by_control)

    run = collect(
        tmp_path, RESULTS_HTML, RESULTS_SOURCE_URL, control_numbers,
        fetch_details=fetch_details, today=TODAY, chunk_size=2,
    )

    assert run["requested"] == 5
    assert run["succeeded"] == 5
    assert run["failed"] == 0
    assert [len(call) for call in fetch_details.calls] == [2, 2, 1]


def test_one_failing_chunk_does_not_abort_the_rest(tmp_path, monkeypatch):
    fake_parse_details(monkeypatch)
    control_numbers = ["A1", "A2", "A3", "A4"]
    rows_by_control = {cn: _row(cn) for cn in control_numbers}
    fetch_details = fake_fetch_details(rows_by_control, fail_for={"A3", "A4"})

    run = collect(
        tmp_path, RESULTS_HTML, RESULTS_SOURCE_URL, control_numbers,
        fetch_details=fetch_details, today=TODAY, chunk_size=2,
    )

    assert run["requested"] == 4
    assert run["succeeded"] == 2
    assert run["failed"] == 2
    assert run["failures"] == [
        {"control_numbers": ["A3", "A4"], "reason": "fetch_error", "detail": "server too slow"}
    ]
    assert len(fetch_details.calls) == 2

    details = json.loads((tmp_path / "raw" / TODAY.isoformat() / "details.json").read_text(encoding="utf-8"))
    assert [row["control_number"] for row in details] == ["A1", "A2"]


def test_run_json_is_written_and_matches_returned_dict(tmp_path, monkeypatch):
    fake_parse_details(monkeypatch)
    control_numbers = ["M200005"]
    fetch_details = fake_fetch_details({"M200005": _row("M200005")})

    run = collect(
        tmp_path, RESULTS_HTML, RESULTS_SOURCE_URL, control_numbers,
        fetch_details=fetch_details, today=TODAY,
    )

    on_disk = json.loads((tmp_path / "raw" / TODAY.isoformat() / "run.json").read_text(encoding="utf-8"))
    assert on_disk == run
    assert on_disk["dataset"] == "adi_details"
    assert on_disk["as_of"] == "2026-09-15"
