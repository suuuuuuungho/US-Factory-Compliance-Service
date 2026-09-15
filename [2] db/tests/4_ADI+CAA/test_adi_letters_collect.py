"""SUU-52: 여러 Control Number의 회신 원문을 받아 PDF만 저장하고, 성공/실패를 run.json에 남긴다.

네트워크는 쓰지 않는다. fetch_letter 를 가짜로 주입한다. 실제 폴더에 쓰지 않는다.
pytest tmp_path 를 root 로 쓴다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from adi_letters_collect import collect

TODAY = date(2026, 9, 15)
PDF_BODY = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\n%%EOF"
NOT_PDF_BODY = b"<html><body>Not Found</body></html>"


def _letter(control_number: str, is_pdf: bool, body: bytes) -> dict:
    return {
        "control_number": control_number,
        "body": body,
        "source_url": f"https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id={control_number}",
        "final_url": f"https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id={control_number}",
        "http_status": 200,
        "media_type": "application/pdf",
        "byte_size": len(body),
        "is_pdf": is_pdf,
    }


def fake_fetch_letter(answers: dict[str, dict]):
    def _fetch_letter(control_number: str, **kwargs) -> dict:
        return answers[control_number]

    return _fetch_letter


def read_run(root: Path, as_of: date = TODAY) -> dict:
    return json.loads((root / "raw" / as_of.isoformat() / "run.json").read_text(encoding="utf-8"))


def test_saves_pdf_and_manifest_entry_for_one_control_number(tmp_path):
    import hashlib

    fetch_letter = fake_fetch_letter({"M200005": _letter("M200005", True, PDF_BODY)})

    collect(tmp_path, ["M200005"], fetch_letter=fetch_letter, today=TODAY)

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["name"] == "M200005.pdf"
    assert entry["sha256"] == hashlib.sha256(PDF_BODY).hexdigest()
    saved = (tmp_path / entry["path"]).read_bytes()
    assert saved == PDF_BODY


def test_marks_not_pdf_without_saving(tmp_path):
    fetch_letter = fake_fetch_letter({"Z900001": _letter("Z900001", False, NOT_PDF_BODY)})

    run = collect(tmp_path, ["Z900001"], fetch_letter=fetch_letter, today=TODAY)

    assert run["succeeded"] == 0
    assert run["failed"] == 1
    assert run["failures"] == [{"control_number": "Z900001", "reason": "not_pdf"}]
    manifest_path = tmp_path / "raw" / TODAY.isoformat() / "manifest.json"
    assert not manifest_path.exists()


def test_records_success_and_failure_counts_for_multiple_control_numbers(tmp_path):
    answers = {
        "M200005": _letter("M200005", True, PDF_BODY),
        "1800013": _letter("1800013", True, PDF_BODY + b"x"),
        "Z900001": _letter("Z900001", False, NOT_PDF_BODY),
    }
    fetch_letter = fake_fetch_letter(answers)

    run = collect(tmp_path, ["M200005", "1800013", "Z900001"], fetch_letter=fetch_letter, today=TODAY)

    assert run["requested"] == 3
    assert run["succeeded"] == 2
    assert run["failed"] == 1
    assert run["failure_reasons"] == {"not_pdf": 1}
    assert run["as_of"] == "2026-09-15"
    assert read_run(tmp_path) == run

    manifest = json.loads((tmp_path / "raw" / TODAY.isoformat() / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(entry["name"] for entry in manifest) == ["1800013.pdf", "M200005.pdf"]


def test_fetch_error_is_recorded_as_failure_not_raised(tmp_path):
    def fetch_letter(control_number: str, **kwargs) -> dict:
        raise TimeoutError("server too slow")

    run = collect(tmp_path, ["M200005"], fetch_letter=fetch_letter, today=TODAY)

    assert run["succeeded"] == 0
    assert run["failed"] == 1
    assert run["failures"] == [{"control_number": "M200005", "reason": "fetch_error", "detail": "server too slow"}]
