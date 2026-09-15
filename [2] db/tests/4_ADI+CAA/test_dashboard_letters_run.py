"""SUU-56: 저장된 Dashboard run에서 canonical_url 목록을 뽑아 dashboard_letters_collect.collect()를 실행한다.

네트워크는 쓰지 않는다. dashboard_collect.collect()로 tmp_path에 실제 Dashboard run을 먼저
만들어두고, fetch_letter만 가짜로 주입한다. 실제 fixture(236행, canonical_url 235개, 고유 230개)를
그대로 쓴다.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from adi_dashboard import parse_dashboard
from dashboard_collect import collect as dashboard_collect
from dashboard_letters_run import run

FIXTURE = Path(__file__).parent / "fixtures" / "adi_dashboard_sample.html"
BODY = FIXTURE.read_bytes()
TODAY = date(2026, 9, 15)


def fake_fetch_dashboard(*args, **kwargs) -> dict:
    return {
        "body": BODY,
        "source_url": "https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and",
        "final_url": "https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and",
        "http_status": 200,
        "media_type": "text/html;charset=UTF-8",
        "byte_size": len(BODY),
    }


def fake_fetch_letter(calls: list):
    def _fetch_letter(canonical_url: str, **kwargs) -> dict:
        calls.append(canonical_url)
        body = f"%PDF-{canonical_url}".encode()
        return {
            "canonical_url": canonical_url,
            "body": body,
            "source_url": canonical_url,
            "final_url": canonical_url,
            "http_status": 200,
            "media_type": "application/pdf",
            "byte_size": len(body),
            "is_pdf": True,
        }

    return _fetch_letter


def _unique_canonical_url_count() -> int:
    rows = parse_dashboard(BODY)
    return len({row["canonical_url"] for row in rows if row["canonical_url"]})


def test_extracts_canonical_urls_from_saved_dashboard_run_and_collects_letters(tmp_path):
    dashboard_root = tmp_path / "caa_dashboard"
    letters_root = tmp_path / "dashboard_letters"
    dashboard_collect(dashboard_root, fetch_dashboard=fake_fetch_dashboard, today=TODAY)

    calls: list[str] = []
    letters_run = run(dashboard_root, letters_root, fetch_letter=fake_fetch_letter(calls), today=TODAY)

    expected = _unique_canonical_url_count()
    assert letters_run["requested"] == expected
    assert letters_run["succeeded"] == expected
    assert letters_run["failed"] == 0
    assert len(calls) == expected
    assert (letters_root / "raw" / TODAY.isoformat() / "manifest.json").exists()


def test_skips_rows_without_canonical_url_and_dedupes(tmp_path):
    dashboard_root = tmp_path / "caa_dashboard"
    letters_root = tmp_path / "dashboard_letters"
    dashboard_collect(dashboard_root, fetch_dashboard=fake_fetch_dashboard, today=TODAY)

    calls: list[str] = []
    run(dashboard_root, letters_root, fetch_letter=fake_fetch_letter(calls), today=TODAY)

    assert calls == sorted(set(calls))
    assert None not in calls


def test_raises_when_no_dashboard_run_found(tmp_path):
    dashboard_root = tmp_path / "caa_dashboard"
    letters_root = tmp_path / "dashboard_letters"

    try:
        run(dashboard_root, letters_root, fetch_letter=fake_fetch_letter([]), today=TODAY)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("FileNotFoundError expected")
