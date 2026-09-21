"""SUU-207: 상세 JSON 한 건 → fr_cfr_reference 행들 + fr_date_event 행들.

1차는 API 값만 쓴다. CFR 참조는 Part 수준(subpart·section NULL), 날짜 사건은 effective_on 하나.
"""
import json
from pathlib import Path

from fr_references import cfr_reference_rows, date_event_rows

FIXTURES = Path(__file__).parent / "fixtures"


def load(pub, num) -> dict:
    return json.loads((FIXTURES / f"detail_{pub}_{num}.json").read_text(encoding="utf-8"))


def test_cfr_reference_is_part_level_with_subpart_section_null():
    rows = cfr_reference_rows("2026-02-24/2026-03638", load("2026-02-24", "2026-03638"))

    assert len(rows) == 1
    row = rows[0]
    assert row["document_key"] == "2026-02-24/2026-03638"
    assert row["title"] == 40
    assert row["part"] == "63"
    assert row["subpart"] is None
    assert row["section"] is None
    assert row["paragraph"] is None
    assert row["relation_type"] == "affects"
    assert row["raw_citation"] == "40 CFR 63"
    assert row["evidence_locator"] == "api:cfr_references[0]"
    assert row["review_status"] == "검토 전"
    assert "reference_id" not in row  # uuid 는 적재(SUU-209)에서 만든다


def test_integer_part_from_old_api_becomes_text():
    rows = cfr_reference_rows("2003-05-27/03-5521", load("2003-05-27", "03-5521"))

    assert rows[0]["part"] == "63"  # fixture 에는 63(정수)로 들어있다
    assert rows[0]["title"] == 40


def test_effective_on_becomes_one_effective_event():
    rows = date_event_rows("2026-02-24/2026-03638", load("2026-02-24", "2026-03638"))

    assert rows == [{
        "document_key": "2026-02-24/2026-03638",
        "event_kind": "effective",
        "event_date": "2026-04-27",
        "applies_to": None,
        "raw_text": load("2026-02-24", "2026-03638")["dates"],  # 문장은 해석하지 않고 그대로 둔다
        "evidence_locator": "api:effective_on",
        "review_status": "검토 전",
    }]


def test_no_effective_on_means_no_event():
    assert date_event_rows("2003-08-28/03-5521", load("2003-08-28", "03-5521")) == []
