"""SUU-50: ADI 목록 수집 진입점 — fetch_results 로 받은 결과를 raw 폴더에 저장하고
서버 총건수·행 수·고유 Control Number 수를 대조해 run.json 을 남긴다.

네트워크는 쓰지 않는다. fetch_results 를 가짜로 주입한다. 실제 폴더에 쓰지 않는다.
pytest tmp_path 를 root 로 쓴다. HTML은 SUU-48 fixture(762건 표시, 실제 39행)를 재사용하고
문자열 치환으로 총건수 일치/불일치, 중복 Control Number 상황을 만든다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from adi_collect import collect

FIXTURE = Path(__file__).parent / "fixtures" / "adi_results_sample.html"
MISMATCH_HTML = FIXTURE.read_bytes()  # results_length=762, 실제 39행
TODAY = date(2026, 9, 15)


def _matching_html() -> bytes:
    """results_length 를 실제 행 수(39)로 맞춘 사본. succeeded 케이스용."""
    return MISMATCH_HTML.replace(b'name="results_length" value="762"', b'name="results_length" value="39"')


def _duplicate_control_number_html() -> bytes:
    """첫 데이터 행을 통째로 복제해 Control Number 중복을 만들고, results_length 도 40으로 맞춘다."""
    html = _matching_html()
    tbody_start = html.index(b"<tbody>") + len(b"<tbody>")
    first_row_end = html.index(b"</tr>", tbody_start) + len(b"</tr>")
    first_row = html[tbody_start:first_row_end]
    duplicated = html[:first_row_end] + first_row + html[first_row_end:]
    return duplicated.replace(b'name="results_length" value="39"', b'name="results_length" value="40"')


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


def read_run(root: Path, as_of: date = TODAY) -> dict:
    return json.loads((root / "raw" / as_of.isoformat() / "run.json").read_text(encoding="utf-8"))


def test_saves_html_with_manifest_entry(tmp_path):
    import hashlib

    body = _matching_html()
    collect(tmp_path, fetch_results=fake_fetch_results(body), today=TODAY)

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["sha256"] == hashlib.sha256(body).hexdigest()
    assert entry["byte_size"] == len(body)
    assert entry["source_url"].startswith("https://cfpub.epa.gov/adi/")
    saved = (tmp_path / entry["path"]).read_bytes()
    assert saved == body


def test_succeeds_when_counts_all_match(tmp_path):
    run = collect(tmp_path, fetch_results=fake_fetch_results(_matching_html()), today=TODAY)

    assert run["status"] == "succeeded"
    assert run["reason"] is None
    assert run["results_length"] == 39
    assert run["row_count"] == 39
    assert run["unique_control_numbers"] == 39
    assert run["as_of"] == "2026-09-15"
    assert read_run(tmp_path) == run


def test_holds_when_results_length_differs_from_row_count(tmp_path):
    run = collect(tmp_path, fetch_results=fake_fetch_results(MISMATCH_HTML), today=TODAY)

    assert run["status"] == "held"
    assert run["reason"] == "results_length_mismatch"
    assert run["results_length"] == 762
    assert run["row_count"] == 39
    assert read_run(tmp_path)["status"] == "held"
    # 파일은 지우지 않는다
    assert (tmp_path / "raw" / TODAY.isoformat() / "manifest.json").exists()


def test_holds_when_control_numbers_duplicate(tmp_path):
    run = collect(tmp_path, fetch_results=fake_fetch_results(_duplicate_control_number_html()), today=TODAY)

    assert run["status"] == "held"
    assert run["reason"] == "duplicate_control_number"
    assert run["results_length"] == 40
    assert run["row_count"] == 40
    assert run["unique_control_numbers"] == 39
    assert read_run(tmp_path)["status"] == "held"
    assert (tmp_path / "raw" / TODAY.isoformat() / "manifest.json").exists()
