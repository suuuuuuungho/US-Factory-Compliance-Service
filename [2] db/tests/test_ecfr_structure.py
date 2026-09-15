"""SUU-35: eCFR 목차(structure JSON)에서 Part 63 가지와 종류별 항목 수 읽기.

샘플은 2026-09-10 기준 Title 40 목차에서 Part 62·63·64만 남기고 줄인 것이다.
Part 63은 Subpart A·G·J·K·XX와 Part 바로 아래 항목만 남겼다. 네트워크는 쓰지 않는다.
"""
import json
from pathlib import Path

import pytest

from ecfr_structure import count_by_type, find_part

FIXTURE = Path(__file__).parent / "fixtures" / "ecfr_structure_sample.json"


def load_sample() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_finds_part_63_node():
    part = find_part(load_sample(), "63")

    assert part["type"] == "part"
    assert part["identifier"] == "63"
    assert part["label"].startswith("Part 63")


def test_missing_part_raises():
    with pytest.raises(ValueError):
        find_part(load_sample(), "999")


def test_counts_descendants_by_type_including_reserved():
    part = find_part(load_sample(), "63")

    # 샘플에 든 것: Subpart K(예약), §§ 63.569-63.599(예약), Tables 14-14b(예약)도 모두 센다
    assert count_by_type(part) == {
        "subpart": 5,
        "subject_group": 3,
        "section": 9,
        "appendix": 4,
    }
