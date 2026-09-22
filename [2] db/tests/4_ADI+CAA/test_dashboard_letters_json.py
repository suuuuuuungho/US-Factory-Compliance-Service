"""SUU-252: CAA Dashboard Part 63 후보 행을 프론트가 읽을 decision-letters.json 으로 만든다.

네트워크·DB 없음. adi_source_entry.jsonl 을 작은 fixture 로 흉내 낸다.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_letters_json import build, part63_subparts

ROOT = Path(__file__).resolve().parents[3]
REAL_ENTRIES = ROOT / "[2] db" / "4) ADI+CAA" / "parsed" / "2026-09-22" / "adi_source_entry.jsonl"


def _entry(**overrides) -> dict:
    base = {
        "source_system": "caa_dashboard",
        "source_key": "ce814c7924dce44b",
        "scope_status": "part63_candidate",
        "text_status": "ok",
        "facility_name": "Domtar AW LLC-Ashdown AR",
        "title": "Applicability Determination for Kraft Pulp Mills",
        "affected_subpart_raw": "Part 60, BB: Kraft Pulp Mills ; Part 63, S: Pulp and Paper Production",
        "link_text": "2025-03-10",
        "canonical_url": "https://www.epa.gov/system/files/documents/2025-06/domtar-response_3-10-25.pdf",
        "control_number": None,
        "categories": [],
    }
    base.update(overrides)
    return base


FIXTURE_ROWS = [
    _entry(),
    _entry(
        source_key="62fa404d15244d54",
        facility_name="Battery Builders Inc",
        title="Performance Test Waiver for Lead Acid Battery Manufacturing Area Sources",
        affected_subpart_raw="Part 63, PPPPPP: Pollutants for Lead Acid Battery Manufacturing Area Sources",
        link_text="2021-11-29",
        canonical_url="https://www.epa.gov/system/files/documents/2022-08/Battery%20Builders%20LLC%20Response_11-29-21.pdf",
    ),
    _entry(  # 원문 없음(404)
        source_key="d06f168138377095",
        facility_name="Missing PDF Co",
        text_status="text_missing",
        canonical_url="https://www.epa.gov/system/files/documents/gone.pdf",
    ),
    _entry(  # ADI 행은 뺀다
        source_system="adi",
        source_key="M200005",
        control_number="M200005",
        facility_name=None,
        affected_subpart_raw=None,
        link_text=None,
        canonical_url="https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M200005",
    ),
    _entry(  # Part 63 아닌 Dashboard 행은 뺀다
        source_key="0000000000000001",
        scope_status="out_of_scope",
        affected_subpart_raw="Part 60, Db: Indust.-Comm.-Inst. Steam Gen. Units",
    ),
]


@pytest.fixture
def entries_path(tmp_path: Path) -> Path:
    path = tmp_path / "adi_source_entry.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in FIXTURE_ROWS), encoding="utf-8")
    return path


def test_build_keeps_only_dashboard_part63_rows(entries_path: Path):
    payload = build(entries_path)

    letters = payload["letters"]
    assert [l["source_key"] for l in letters] == [
        "ce814c7924dce44b",
        "62fa404d15244d54",
        "d06f168138377095",
    ]
    first = letters[0]
    assert first == {
        "source_key": "ce814c7924dce44b",
        "facility_name": "Domtar AW LLC-Ashdown AR",
        "title": "Applicability Determination for Kraft Pulp Mills",
        "subparts": ["S"],
        "date": "2025-03-10",
        "pdf_url": "https://www.epa.gov/system/files/documents/2025-06/domtar-response_3-10-25.pdf",
    }


def test_part63_subparts_drops_other_parts_and_keeps_order():
    assert part63_subparts("Part 60, BB: Kraft Pulp Mills ; Part 63, S: Pulp and Paper Production") == ["S"]
    assert part63_subparts("Part 63, PPPPPP: Pollutants for Lead Acid Battery") == ["PPPPPP"]
    assert part63_subparts("Part 63, ZZZZ: Engines ; Part 63, DDDDD: Boilers") == ["ZZZZ", "DDDDD"]
    assert part63_subparts("Part 60, Db: Steam Gen. Units") == []
    assert part63_subparts(None) == []


def test_pdf_url_is_null_when_text_status_is_not_ok(entries_path: Path):
    letters = {l["source_key"]: l for l in build(entries_path)["letters"]}

    assert letters["d06f168138377095"]["pdf_url"] is None
    assert letters["62fa404d15244d54"]["pdf_url"] is not None


@pytest.mark.skipif(not REAL_ENTRIES.exists(), reason="2026-09-22 parsed 자료는 레포에 없다(로컬 전용)")
def test_real_2026_09_22_data_yields_132_letters():
    letters = build(REAL_ENTRIES)["letters"]

    assert len(letters) == 132
    assert sum(1 for l in letters if l["pdf_url"]) == 128
