"""SUU-58: 저장된 ADI run에서 Control Number 목록을 뽑아 adi_details_collect.collect()를 실행한다.

네트워크는 쓰지 않는다. adi_collect.collect()로 tmp_path에 실제 ADI run을 먼저 만들어두고,
fetch_details만 가짜로 주입한다. parse_details는 monkeypatch로 바꿔치기해서
run()의 "목록 뽑기 + collect 호출" 로직만 검증한다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from adi_collect import collect as adi_collect
from adi_details_run import run

FIXTURE = Path(__file__).parent / "fixtures" / "adi_results_sample.html"
TODAY = date(2026, 9, 15)


def _matching_html() -> bytes:
    """results_length 를 실제 행 수(39)로 맞춘 사본. adi_collect가 succeeded 로 저장한다."""
    return FIXTURE.read_bytes().replace(b'name="results_length" value="762"', b'name="results_length" value="39"')


def fake_fetch_results(body: bytes):
    def _fetch_results(*args, **kwargs) -> dict:
        return {
            "body": body,
            "source_url": "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_results_table",
            "final_url": "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_results_table",
            "http_status": 200,
            "media_type": "text/html;charset=UTF-8",
            "byte_size": len(body),
        }

    return _fetch_results


def fake_fetch_details(calls: list):
    def _fetch_details(results_html, results_source_url, control_numbers, **kwargs) -> dict:
        calls.append(list(control_numbers))
        rows = [{"control_number": cn} for cn in control_numbers]
        body = json.dumps(rows).encode("utf-8")
        return {
            "body": body,
            "source_url": results_source_url,
            "final_url": results_source_url,
            "http_status": 200,
            "media_type": "text/html",
            "byte_size": len(body),
        }

    return _fetch_details


def _patch_parse_details(monkeypatch):
    import adi_details_collect

    monkeypatch.setattr(adi_details_collect, "parse_details", lambda body: json.loads(body))


def test_extracts_control_numbers_from_saved_adi_run_and_collects_details(tmp_path, monkeypatch):
    _patch_parse_details(monkeypatch)
    adi_root = tmp_path / "adi"
    details_root = tmp_path / "adi_details"
    adi_collect(adi_root, fetch_results=fake_fetch_results(_matching_html()), today=TODAY)

    calls: list[list[str]] = []
    details_run = run(adi_root, details_root, fetch_details=fake_fetch_details(calls), today=TODAY)

    assert details_run["requested"] == 39
    assert details_run["succeeded"] == 39
    assert details_run["failed"] == 0
    assert sum(len(call) for call in calls) == 39
    assert (details_root / "raw" / TODAY.isoformat() / "details.json").exists()


def test_calls_fetch_details_with_sorted_unique_control_numbers(tmp_path, monkeypatch):
    _patch_parse_details(monkeypatch)
    adi_root = tmp_path / "adi"
    details_root = tmp_path / "adi_details"
    adi_collect(adi_root, fetch_results=fake_fetch_results(_matching_html()), today=TODAY)

    calls: list[list[str]] = []
    run(adi_root, details_root, fetch_details=fake_fetch_details(calls), today=TODAY)

    requested = [cn for call in calls for cn in call]
    assert requested == sorted(set(requested))
    assert len(requested) == len(set(requested))


def test_raises_when_no_adi_run_found(tmp_path, monkeypatch):
    _patch_parse_details(monkeypatch)
    adi_root = tmp_path / "adi"
    details_root = tmp_path / "adi_details"

    try:
        run(adi_root, details_root, fetch_details=fake_fetch_details([]), today=TODAY)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("FileNotFoundError expected")
