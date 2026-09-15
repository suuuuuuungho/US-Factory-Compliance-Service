"""SUU-55: 여러 canonical_url의 회신 원문을 받아 PDF만 저장하고, 성공/실패를 run.json에 남긴다.

네트워크는 쓰지 않는다. fetch_letter 를 가짜로 주입한다. 실제 폴더에 쓰지 않는다.
pytest tmp_path 를 root 로 쓴다. Dashboard는 Control Number가 없으므로 canonical_url의
sha256을 파일 이름으로 쓴다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from dashboard_letters_collect import collect

TODAY = date(2026, 9, 15)
PDF_BODY = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n%%EOF"
NOT_PDF_BODY = b"<html><body>Not Found</body></html>"
URL_A = "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"
URL_B = "https://www.epa.gov/system/files/documents/2022-05/Other%20Response.pdf"
URL_C = "https://www.epa.gov/system/files/documents/2022-05/Not%20Found.pdf"


def _letter(canonical_url: str, is_pdf: bool, body: bytes) -> dict:
    return {
        "canonical_url": canonical_url,
        "body": body,
        "source_url": canonical_url,
        "final_url": canonical_url,
        "http_status": 200,
        "media_type": "application/pdf",
        "byte_size": len(body),
        "is_pdf": is_pdf,
    }


def fake_fetch_letter(answers: dict[str, dict]):
    def _fetch_letter(canonical_url: str, **kwargs) -> dict:
        return answers[canonical_url]

    return _fetch_letter


def read_run(root: Path, as_of: date = TODAY) -> dict:
    return json.loads((root / "raw" / as_of.isoformat() / "run.json").read_text(encoding="utf-8"))


def test_saves_pdf_and_manifest_entry_for_one_canonical_url(tmp_path):
    fetch_letter = fake_fetch_letter({URL_A: _letter(URL_A, True, PDF_BODY)})

    collect(tmp_path, [URL_A], fetch_letter=fetch_letter, today=TODAY)

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["name"] == f"{hashlib.sha256(URL_A.encode()).hexdigest()}.pdf"
    assert entry["sha256"] == hashlib.sha256(PDF_BODY).hexdigest()
    saved = (tmp_path / entry["path"]).read_bytes()
    assert saved == PDF_BODY


def test_marks_not_pdf_without_saving(tmp_path):
    fetch_letter = fake_fetch_letter({URL_C: _letter(URL_C, False, NOT_PDF_BODY)})

    run = collect(tmp_path, [URL_C], fetch_letter=fetch_letter, today=TODAY)

    assert run["succeeded"] == 0
    assert run["failed"] == 1
    assert run["failures"] == [{"canonical_url": URL_C, "reason": "not_pdf"}]
    manifest_path = tmp_path / "raw" / TODAY.isoformat() / "manifest.json"
    assert not manifest_path.exists()


def test_records_success_and_failure_counts_for_multiple_urls(tmp_path):
    answers = {
        URL_A: _letter(URL_A, True, PDF_BODY),
        URL_B: _letter(URL_B, True, PDF_BODY + b"x"),
        URL_C: _letter(URL_C, False, NOT_PDF_BODY),
    }
    fetch_letter = fake_fetch_letter(answers)

    run = collect(tmp_path, [URL_A, URL_B, URL_C], fetch_letter=fetch_letter, today=TODAY)

    assert run["requested"] == 3
    assert run["succeeded"] == 2
    assert run["failed"] == 1
    assert run["failure_reasons"] == {"not_pdf": 1}
    assert run["as_of"] == "2026-09-15"
    assert read_run(tmp_path) == run

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(entry["name"] for entry in manifest) == sorted(
        f"{hashlib.sha256(url.encode()).hexdigest()}.pdf" for url in (URL_A, URL_B)
    )


def test_fetch_error_is_recorded_as_failure_not_raised(tmp_path):
    def fetch_letter(canonical_url: str, **kwargs) -> dict:
        raise TimeoutError("server too slow")

    run = collect(tmp_path, [URL_A], fetch_letter=fetch_letter, today=TODAY)

    assert run["succeeded"] == 0
    assert run["failed"] == 1
    assert run["failures"] == [{"canonical_url": URL_A, "reason": "fetch_error", "detail": "server too slow"}]
