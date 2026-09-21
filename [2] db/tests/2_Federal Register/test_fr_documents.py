"""SUU-207: 상세 JSON 한 건 → fr_document 행 하나 + fr_identifier 행들.

네트워크 없음. fixtures/detail_*.json 은 실제 API 응답이다.
"""
import json
from pathlib import Path

from fr_documents import document_key, document_row, identifier_rows

FIXTURES = Path(__file__).parent / "fixtures"


def load(pub, num) -> dict:
    return json.loads((FIXTURES / f"detail_{pub}_{num}.json").read_text(encoding="utf-8"))


def manifest(detail_sha="d" * 64, *, xml=True, pdf=True) -> list[dict]:
    """fr_raw.store_raw 가 남기는 manifest 모양(필요한 키만)."""
    rows = [{"kind": "detail", "sha256": detail_sha}]
    if xml:
        rows.append({"kind": "xml", "sha256": "x" * 64})
    if pdf:
        rows.append({"kind": "pdf", "sha256": "p" * 64})
    return rows


def test_document_key_is_publication_date_slash_number():
    assert document_key("2026-02-24", "2026-03638") == "2026-02-24/2026-03638"
    assert document_key("2003-05-27", "03-5521") == "2003-05-27/03-5521"  # 과거 번호를 바꾸지 않는다


def test_document_row_copies_api_fields_and_keeps_whole_json():
    detail = load("2026-02-24", "2026-03638")

    row = document_row(detail, manifest("a" * 64))

    assert row["document_key"] == "2026-02-24/2026-03638"
    assert row["publication_date"] == "2026-02-24"
    assert row["document_number"] == "2026-03638"
    assert row["canonical_url"] == detail["html_url"]
    assert row["title"].startswith("National Emission Standards for Hazardous Air Pollutants")
    assert row["type_raw"] == "Rule"
    assert row["action"] == "Final rule."
    assert row["citation"] == "91 FR 9088"
    assert (row["volume"], row["start_page"], row["end_page"]) == (91, 9088, 9134)
    assert row["effective_on"] == "2026-04-27"
    assert row["agencies"] == detail["agencies"]
    assert row["docket_ids"] == ["EPA-HQ-OAR-2018-0794", "FRL-6716.4-02-OAR"]  # 문자열 그대로
    assert row["regulation_id_numbers"] == ["2060-AW68"]
    assert row["full_text_xml_url"] == detail["full_text_xml_url"]
    assert row["pdf_url"] == detail["pdf_url"]
    assert row["content_hash"] == "a" * 64  # 상세 JSON 파일의 sha256
    assert row["raw_metadata"] == detail  # 원본 전체
    assert row["scope_status"] == "part63_list"
    assert row["body_status"] == "xml"


def test_subtype_null_stays_null_not_empty_string():
    row = document_row(load("2026-02-24", "2026-03638"), manifest())

    assert row["subtype"] is None
    assert row["signing_date"] is None
    assert row["comments_close_on"] is None


def test_correction_without_effective_on_still_becomes_a_document():
    row = document_row(load("2003-08-28", "03-5521"), manifest())

    assert row["document_key"] == "2003-08-28/03-5521"
    assert row["type_raw"] == "Correction"
    assert row["effective_on"] is None
    assert row["abstract"] is None


def test_body_status_follows_manifest_kinds():
    detail = load("2003-05-27", "03-5521")

    assert document_row(detail, manifest(xml=True, pdf=True))["body_status"] == "xml"
    assert document_row(detail, manifest(xml=False, pdf=True))["body_status"] == "pdf_only"
    assert document_row(detail, manifest(xml=False, pdf=False))["body_status"] == "missing"


def test_identifiers_come_from_dockets_and_rin_lists():
    rows = identifier_rows("2026-02-24/2026-03638", load("2026-02-24", "2026-03638"))

    assert rows == [
        {"document_key": "2026-02-24/2026-03638", "identifier_kind": "docket", "identifier_value": "EPA-HQ-OAR-2018-0794"},
        {"document_key": "2026-02-24/2026-03638", "identifier_kind": "rin", "identifier_value": "2060-AW68"},
    ]  # FRL-6716.4-02-OAR 은 docket 이 아니라 docket_ids 열에만 남는다


def test_old_document_with_no_structured_docket_gets_only_rin():
    rows = identifier_rows("2003-05-27/03-5521", load("2003-05-27", "03-5521"))

    assert rows == [
        {"document_key": "2003-05-27/03-5521", "identifier_kind": "rin", "identifier_value": "2060-A174"},
    ]  # docket_ids 의 "OAR-2002-0040, FRL-7461-4" 를 쪼개지 않는다
