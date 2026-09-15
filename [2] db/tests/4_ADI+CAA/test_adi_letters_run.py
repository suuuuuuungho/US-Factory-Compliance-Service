"""SUU-54: 저장된 ADI run에서 Control Number 목록을 뽑아 adi_letters_collect.collect()를 실행한다.

네트워크는 쓰지 않는다. adi_collect.collect()로 tmp_path에 실제 ADI run을 먼저 만들어두고,
fetch_letter만 가짜로 주입한다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from adi_collect import collect as adi_collect
from adi_letters_run import run

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


def fake_fetch_letter(calls: list):
    def _fetch_letter(control_number: str, **kwargs) -> dict:
        calls.append(control_number)
        body = f"%PDF-{control_number}".encode()
        return {
            "control_number": control_number,
            "body": body,
            "source_url": f"https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id={control_number}",
            "final_url": f"https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id={control_number}",
            "http_status": 200,
            "media_type": "application/pdf",
            "byte_size": len(body),
            "is_pdf": True,
        }

    return _fetch_letter


def test_extracts_control_numbers_from_saved_adi_run_and_collects_letters(tmp_path):
    adi_root = tmp_path / "adi"
    letters_root = tmp_path / "adi_letters"
    adi_collect(adi_root, fetch_results=fake_fetch_results(_matching_html()), today=TODAY)

    calls: list[str] = []
    letters_run = run(adi_root, letters_root, fetch_letter=fake_fetch_letter(calls), today=TODAY)

    assert letters_run["requested"] == 39
    assert letters_run["succeeded"] == 39
    assert letters_run["failed"] == 0
    assert len(calls) == 39
    assert (letters_root / "raw" / TODAY.isoformat() / "manifest.json").exists()


def test_calls_fetch_letter_once_per_unique_control_number_in_sorted_order(tmp_path):
    adi_root = tmp_path / "adi"
    letters_root = tmp_path / "adi_letters"
    adi_collect(adi_root, fetch_results=fake_fetch_results(_matching_html()), today=TODAY)

    calls: list[str] = []
    run(adi_root, letters_root, fetch_letter=fake_fetch_letter(calls), today=TODAY)

    assert calls == sorted(set(calls))
    assert len(calls) == len(set(calls))


def test_raises_when_no_adi_run_found(tmp_path):
    adi_root = tmp_path / "adi"
    letters_root = tmp_path / "adi_letters"

    try:
        run(adi_root, letters_root, fetch_letter=fake_fetch_letter([]), today=TODAY)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("FileNotFoundError expected")
