"""SUU-221: 받아둔 회신 PDF 파일들 → adi_document·adi_document_version·adi_entry_document·adi_page 행.

입력 `files` 는 항목(source_system, source_key)과 파일(sha256, path)의 쌍이다. 같은 sha256 이 두 항목에 붙으면
문서 1개·버전 1개·항목 연결 2개다. 페이지 글자는 SUU-59 extract_pages 로 뽑는다(reader_factory 주입 가능).
PDF 를 열지 못하면 그 항목은 held 로 남기고 버전·페이지를 쓰지 않는다.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from adi_documents import PARSER_VERSION, build_documents, document_id, version_id


def _file(tmp_path: Path, name: str, body: bytes, source_system: str, source_key: str, letter_date_raw=None) -> dict:
    path = tmp_path / name
    path.write_bytes(body)
    return {
        "source_system": source_system,
        "source_key": source_key,
        "sha256": hashlib.sha256(body).hexdigest(),
        "path": path,
        "letter_date_raw": letter_date_raw,
    }


def test_ids_are_deterministic_uuids_from_sha256():
    sha = "da3f9387a6c176117448676c5835b280ddadf557cbe92709107587563cfaabc5"

    assert document_id(sha) == document_id(sha)
    assert uuid.UUID(document_id(sha)).version == 5
    assert version_id(sha) == version_id(sha, PARSER_VERSION)
    assert version_id(sha) != version_id(sha, "999")
    assert document_id(sha) != version_id(sha)


def test_same_sha256_in_both_lists_gives_one_document_two_entry_links(tmp_path, make_pdf):
    body = make_pdf(["Dear Sir, this is the response."])
    files = [
        _file(tmp_path, "1800013.pdf", body, "adi", "1800013", letter_date_raw="05/11/2018"),
        _file(tmp_path, "king.pdf", body, "caa_dashboard", "dash-king"),
    ]

    out = build_documents(files)

    sha = hashlib.sha256(body).hexdigest()
    assert len(out["adi_document"]) == 1
    assert out["adi_document"][0] == {"document_id": document_id(sha), "canonical_identity": f"sha256:{sha}"}

    assert len(out["adi_document_version"]) == 1
    version = out["adi_document_version"][0]
    assert version["version_id"] == version_id(sha)
    assert version["document_id"] == document_id(sha)
    assert version["sha256"] == sha
    assert version["parser_version"] == PARSER_VERSION
    assert version["extraction_method"] == "pypdf"
    assert version["signed_on"] is None  # 서명일은 본문 확인 전이라 확정하지 않는다
    assert version["signed_on_raw"] == "05/11/2018"  # ADI 목록의 날짜 문자열은 보존
    assert version["date_source"] == "adi_list"
    assert version["legal_status"] == "unknown"
    assert version["quality_status"] == "ok"
    assert version["text_content"] == "Dear Sir, this is the response."

    links = sorted((l["source_system"], l["source_key"]) for l in out["adi_entry_document"])
    assert links == [("adi", "1800013"), ("caa_dashboard", "dash-king")]
    assert {l["version_id"] for l in out["adi_entry_document"]} == {version_id(sha)}
    assert {l["match_method"] for l in out["adi_entry_document"]} == {"fetched_from_entry"}
    assert out["held"] == []


def test_pages_keep_empty_status_and_every_version_has_pages(tmp_path, make_pdf):
    body = make_pdf(["Hello ADI", None, "Third page"])
    files = [_file(tmp_path, "M200005.pdf", body, "adi", "M200005")]

    out = build_documents(files)

    sha = hashlib.sha256(body).hexdigest()
    pages = sorted(out["adi_page"], key=lambda p: p["page_no"])
    assert [p["page_no"] for p in pages] == [1, 2, 3]
    assert all(p["version_id"] == version_id(sha) for p in pages)
    assert [p["status"] for p in pages] == ["ok", "empty", "ok"]
    assert pages[1]["text_content"] == ""
    assert pages[1]["failure_reason"] is None
    assert all(p["extraction_method"] == "pypdf" for p in pages)
    assert all(p["ocr_confidence"] is None for p in pages)  # OCR 안 했으니 점수를 지어내지 않는다
    assert all(p["review_status"] == "검토 전" for p in pages)

    version = out["adi_document_version"][0]
    assert version["quality_status"] == "partial"  # 빈 페이지가 있으면 partial
    assert version["text_content"] == "Hello ADI\n\nThird page"
    assert version["signed_on_raw"] is None and version["date_source"] is None  # Dashboard/날짜 없는 항목

    version_ids = {v["version_id"] for v in out["adi_document_version"]}
    assert version_ids == {p["version_id"] for p in out["adi_page"]}  # 페이지 없는 버전 0


def test_failed_page_is_kept_with_reason_and_no_text_version_is_flagged(tmp_path):
    class FakePage:
        def __init__(self, text, fail):
            self._text, self._fail = text, fail

        def extract_text(self):
            if self._fail:
                raise ValueError("corrupted content stream")
            return self._text

    class FakeReader:
        def __init__(self, pdf_bytes):
            self.pages = [FakePage("", True), FakePage("", False)]

    files = [_file(tmp_path, "x.pdf", b"%PDF-fake", "adi", "X1")]

    out = build_documents(files, reader_factory=FakeReader)

    pages = sorted(out["adi_page"], key=lambda p: p["page_no"])
    assert [p["status"] for p in pages] == ["failed", "empty"]
    assert pages[0]["failure_reason"] == "corrupted content stream"
    assert out["adi_document_version"][0]["quality_status"] == "no_text"
    assert out["adi_document_version"][0]["text_content"] == ""
    assert out["held"] == []  # 페이지 실패는 held 가 아니라 상태로 남긴다


def test_unreadable_pdf_is_held_and_writes_nothing_for_it(tmp_path, make_pdf):
    good = make_pdf(["fine"])
    files = [
        _file(tmp_path, "good.pdf", good, "adi", "G1"),
        _file(tmp_path, "bad.pdf", b"this is not a pdf at all", "caa_dashboard", "dash-bad"),
    ]

    out = build_documents(files)

    assert len(out["adi_document"]) == 1
    assert len(out["adi_document_version"]) == 1
    assert [(l["source_system"], l["source_key"]) for l in out["adi_entry_document"]] == [("adi", "G1")]
    assert len(out["held"]) == 1
    held = out["held"][0]
    assert (held["source_system"], held["source_key"]) == ("caa_dashboard", "dash-bad")
    assert held["sha256"] == hashlib.sha256(b"this is not a pdf at all").hexdigest()
    assert held["reason"]  # 사유가 비어있지 않다
