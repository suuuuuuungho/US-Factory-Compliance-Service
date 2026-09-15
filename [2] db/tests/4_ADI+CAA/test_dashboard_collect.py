"""SUU-51: Dashboard 진입점 — fetch_dashboard 로 받은 표를 raw 폴더에 저장하고
행 수·Part 63 언급 행 수를 run.json 에 남긴다.

네트워크는 쓰지 않는다. fetch_dashboard 를 가짜로 주입한다. 실제 폴더에 쓰지 않는다.
pytest tmp_path 를 root 로 쓴다. HTML은 SUU-47 fixture(실제 236행, Part 63 132행)를 재사용한다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from dashboard_collect import collect

FIXTURE = Path(__file__).parent / "fixtures" / "adi_dashboard_sample.html"
BODY = FIXTURE.read_bytes()
TODAY = date(2026, 9, 15)
DASHBOARD_URL = (
    "https://www.epa.gov/complying-air-emissions-standards-stationary-sources"
    "/epa-determinations-compliance-and"
)


def fake_fetch_dashboard(body: bytes = BODY):
    def _fetch_dashboard(*args, **kwargs) -> dict:
        return {
            "body": body,
            "source_url": DASHBOARD_URL,
            "final_url": DASHBOARD_URL,
            "http_status": 200,
            "media_type": "text/html;charset=UTF-8",
            "byte_size": len(body),
        }

    return _fetch_dashboard


def read_run(root: Path, as_of: date = TODAY) -> dict:
    return json.loads((root / "raw" / as_of.isoformat() / "run.json").read_text(encoding="utf-8"))


def test_saves_html_with_manifest_entry(tmp_path):
    collect(tmp_path, fetch_dashboard=fake_fetch_dashboard(), today=TODAY)

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert entry["byte_size"] == len(BODY)
    assert entry["source_url"] == DASHBOARD_URL
    saved = (tmp_path / entry["path"]).read_bytes()
    assert saved == BODY


def test_run_json_has_row_count_and_part_63_count(tmp_path):
    run = collect(tmp_path, fetch_dashboard=fake_fetch_dashboard(), today=TODAY)

    assert run["row_count"] == 236
    assert run["part_63_count"] == 132
    assert run["as_of"] == "2026-09-15"
    assert read_run(tmp_path) == run


def test_raises_and_does_not_save_when_table_missing(tmp_path):
    broken = b"<html><body><p>no table here</p></body></html>"

    with pytest.raises(ValueError):
        collect(tmp_path, fetch_dashboard=fake_fetch_dashboard(broken), today=TODAY)

    assert not (tmp_path / "raw" / TODAY.isoformat()).exists()
