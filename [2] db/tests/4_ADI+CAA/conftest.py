"""4_ADI+CAA 테스트 공용 fixture.

make_pdf: 페이지별 글자를 넣은 진짜 PDF 바이트를 즉석에서 만든다(디스크 fixture 없이).
None 인 페이지는 글자 없는 빈 페이지가 된다.
"""
from __future__ import annotations

import io

import pytest


def _make_pdf(page_texts: list[str | None]) -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=200, height=200)
        if text is None:
            continue

        font = DictionaryObject()
        font[NameObject("/Type")] = NameObject("/Font")
        font[NameObject("/Subtype")] = NameObject("/Type1")
        font[NameObject("/BaseFont")] = NameObject("/Helvetica")
        font_ref = writer._add_object(font)

        resources = DictionaryObject()
        fontdict = DictionaryObject()
        fontdict[NameObject("/F1")] = font_ref
        resources[NameObject("/Font")] = fontdict
        page[NameObject("/Resources")] = resources

        content = DecodedStreamObject()
        content.set_data(f"BT /F1 24 Tf 10 100 Td ({text}) Tj ET".encode("latin-1"))
        content_ref = writer._add_object(content)
        page[NameObject("/Contents")] = content_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def make_pdf():
    return _make_pdf


# ---------------------------------------------------------------------------
# SUU-224: adi fixture — raw(목록 2 + PDF 4) → parsed/{AS_OF}/ jsonl 9개를 실제 SUU-221·222 코드로 만든다.
# 네트워크·DB 없음. 폴더 모양은 test_adi_parse.py 머리말과 같다.
# ---------------------------------------------------------------------------
import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ADI_FIXTURES = Path(__file__).parent / "fixtures"
ADI_RAW_AS_OF = date(2026, 9, 17)
ADI_AS_OF = "2026-09-22"
KING_URL = "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"
WESTVACO_URL = "https://www.epa.gov/system/files/documents/2022-01/genesis-alkali-westvaco_40-cfr-60-subpart-aaaaa_1-15-21.pdf"
ADI_TABLES = (
    "adi_source_entry", "adi_document", "adi_document_version", "adi_entry_document", "adi_page",
    "adi_block", "adi_cfr_reference", "adi_document_relation", "adi_facility_candidate",
)


def _adi_save(root, name, body, url):
    from ecfr_raw import save_raw

    return save_raw(root, ADI_RAW_AS_OF, name, body, source_url=url, final_url=url, http_status=200, media_type="application/pdf")


def _adi_run_json(root, dataset, sha):
    path = root / "raw" / ADI_RAW_AS_OF.isoformat() / "run.json"
    path.write_text(json.dumps({"dataset": dataset, "as_of": ADI_RAW_AS_OF.isoformat(), "status": "succeeded", "html_sha256": sha}), encoding="utf-8")


def _adi_put_raw(root: Path) -> dict:
    """SUU-114 수집기가 남기는 모양 그대로. 반환: 이름 → (source_url, sha256) — 원본 6개(목록 2 + PDF 4, 그중 2개는 같은 파일)."""
    objects = {}
    entry = _adi_save(root, "adi-results.html", (ADI_FIXTURES / "adi_results_sample.html").read_bytes(), "https://cfpub.epa.gov/adi/index.cfm?CFID=1&CFTOKEN=x")
    _adi_run_json(root, "adi", entry["sha256"])
    objects["adi_list"] = (entry["source_url"], entry["sha256"])
    entry = _adi_save(root / "caa_dashboard", "caa-dashboard.html", (ADI_FIXTURES / "adi_dashboard_sample.html").read_bytes(), "https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and")
    _adi_run_json(root / "caa_dashboard", "caa_dashboard", entry["sha256"])
    objects["dashboard_list"] = (entry["source_url"], entry["sha256"])
    details = root / "adi_details" / "raw" / ADI_RAW_AS_OF.isoformat() / "details.json"
    details.parent.mkdir(parents=True)
    details.write_text(json.dumps([{
        "control_number": "1800013", "title": "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks",
        "letter_date_raw": "05/11/2018", "author": "Sara Breneman", "categories": ["MACT", "NSPS"],
        "office": "Region 5", "abstract": "Q: Does EPA approve an AMP? A: Yes.",
    }]), encoding="utf-8")

    shared = _make_pdf([
        "Control Number: 1800013",
        "Q: Is the tank subject to 40 CFR 63.2 and 40 CFR 63.9999?",
        "A: Yes. King Systems Corporation, Noblesville, IN 46060",
        "Sincerely,",
    ])
    e = _adi_save(root / "adi_letters" / "shard_0", "1800013.pdf", shared, "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=1800013")
    objects["1800013"] = (e["source_url"], e["sha256"])
    e = _adi_save(root / "adi_letters" / "shard_1", "M170010.pdf", _make_pdf([
        "Control Number: M170010",
        "Comments: Partially rescinds the determination issued as ADI Control Number 1800013.",
        "Letter: The engines cite 40 CFR 60.4200 and 40 CFR 63.6590.",
    ]), "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M170010")
    objects["M170010"] = (e["source_url"], e["sha256"])
    e = _adi_save(root / "dashboard_letters", hashlib.sha256(KING_URL.encode()).hexdigest() + ".pdf", shared, KING_URL)
    objects["king"] = (e["source_url"], e["sha256"])  # 1800013.pdf 와 같은 파일, 다른 URL
    e = _adi_save(root / "dashboard_letters", hashlib.sha256(WESTVACO_URL.encode()).hexdigest() + ".pdf", b"not a pdf", WESTVACO_URL)
    objects["westvaco"] = (e["source_url"], e["sha256"])  # held(text_failed) — 원본으로는 등록된다
    return objects


def _adi_read_jsonl(root, table):
    return [json.loads(line) for line in (root / "parsed" / ADI_AS_OF / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def adi(tmp_path):
    """raw/ 원본 6개 + parsed/{AS_OF}/ jsonl 9개·quality_report.json·enrich_report.json.

    adi.root, adi.as_of, adi.objects[이름] = (source_url, sha256), adi.rows(table), adi.tables, adi.nodes, adi.echo
    """
    from adi_enrich import enrich_all
    from adi_parse import parse_all

    root = tmp_path / "adi"
    objects = _adi_put_raw(root)
    parse_all(root, ADI_AS_OF, raw_as_of=ADI_RAW_AS_OF.isoformat())
    nodes, echo = tmp_path / "nodes.jsonl", tmp_path / "echo_facility.jsonl"
    nodes.write_text("".join(json.dumps(row) + "\n" for row in [
        {"node_key": "40/63/subpart-A/section-63.2", "node_type": "section", "identifier": "63.2"},
        {"node_key": "40/63/subpart-ZZZZ/section-63.6590", "node_type": "section", "identifier": "63.6590"},
    ]), encoding="utf-8")
    echo.write_text(json.dumps({"pgm_sys_id": "IN0000123", "name": "KING SYSTEMS CORP", "state": "IN"}) + "\n", encoding="utf-8")
    enrich_all(root, ADI_AS_OF, ecfr_nodes=nodes, echo_facilities=echo)
    return SimpleNamespace(root=root, as_of=ADI_AS_OF, objects=objects, nodes=nodes, echo=echo, tables=ADI_TABLES,
                           rows=lambda table: _adi_read_jsonl(root, table))
