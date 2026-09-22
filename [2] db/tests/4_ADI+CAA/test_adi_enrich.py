"""SUU-222: parsed/{as_of}/ 의 SUU-221 jsonl(adi_document_version·adi_page·adi_source_entry·adi_entry_document)을 읽어
adi_block·adi_cfr_reference·adi_document_relation·adi_facility_candidate jsonl + enrich_report.json 을 같은 폴더에 쓴다.
eCFR 노드는 nodes.jsonl, ECHO 시설은 echo_facility.jsonl 을 그대로 읽는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from adi_enrich import TABLES, enrich_all, main

FIXTURES = Path(__file__).parent / "fixtures"
V_QA = "11111111-1111-5111-8111-111111111111"
V_NEG = "22222222-2222-5222-8222-222222222222"
V_OLD = "33333333-3333-5333-8333-333333333333"
D_QA = "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"
D_NEG = "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"
D_OLD = "cccccccc-cccc-5ccc-8ccc-cccccccccccc"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _pages(version_id: str, name: str) -> list[dict]:
    text = (FIXTURES / name).read_text(encoding="utf-8").rstrip("\n")
    return [
        {"version_id": version_id, "page_no": no, "text_content": chunk.strip("\n"), "status": "ok", "extraction_method": "pypdf",
         "ocr_confidence": None, "failure_reason": None, "review_status": "검토 전"}
        for no, chunk in enumerate(text.split("<<<PAGE>>>"), start=1)
    ]


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "adi"
    parsed = root / "parsed" / "2026-09-22"
    pages = _pages(V_QA, "adi_letter_qa.txt") + _pages(V_NEG, "adi_letter_negative.txt")
    _write_jsonl(parsed / "adi_page.jsonl", pages)
    _write_jsonl(parsed / "adi_document_version.jsonl", [
        {"version_id": V_QA, "document_id": D_QA, "sha256": "a" * 64, "text_content": "\n\n".join(p["text_content"] for p in pages if p["version_id"] == V_QA)},
        {"version_id": V_NEG, "document_id": D_NEG, "sha256": "b" * 64, "text_content": "\n\n".join(p["text_content"] for p in pages if p["version_id"] == V_NEG)},
        {"version_id": V_OLD, "document_id": D_OLD, "sha256": "c" * 64, "text_content": None},
    ])
    _write_jsonl(parsed / "adi_source_entry.jsonl", [
        {"source_system": "adi", "source_key": "M050030", "control_number": "M050030", "facility_name": "Essroc Cement Corp."},
        {"source_system": "adi", "source_key": "M090020", "control_number": "M090020", "facility_name": "Stamas Yacht Inc."},
        {"source_system": "adi", "source_key": "M080027", "control_number": "M080027", "facility_name": "Jupiter Aluminum"},
        {"source_system": "adi", "source_key": "M050031", "control_number": "M050031", "facility_name": "Essroc Cement Corp."},
        {"source_system": "caa_dashboard", "source_key": "0123456789abcdef", "control_number": None, "facility_name": "Some Plant"},
    ])
    _write_jsonl(parsed / "adi_entry_document.jsonl", [
        {"source_system": "adi", "source_key": "M050030", "version_id": V_QA},
        {"source_system": "adi", "source_key": "M090020", "version_id": V_NEG},
        {"source_system": "adi", "source_key": "M080027", "version_id": V_OLD},
    ])
    nodes = tmp_path / "nodes.jsonl"
    _write_jsonl(nodes, [
        {"node_key": "40/63/subpart-A/section-63.2", "node_type": "section", "identifier": "63.2"},
        {"node_key": "40/63/subpart-A/section-63.7", "node_type": "section", "identifier": "63.7"},
        {"node_key": "40/63/subpart-EEE", "node_type": "subpart", "identifier": "EEE"},
        {"node_key": "40/63/subpart-EEE/section-63.1204", "node_type": "section", "identifier": "63.1204"},
        {"node_key": "40/63/subpart-EEE/section-63.1207", "node_type": "section", "identifier": "63.1207"},
        {"node_key": "40/63/subpart-VVVV", "node_type": "subpart", "identifier": "VVVV"},
    ])
    echo = tmp_path / "echo_facility.jsonl"
    _write_jsonl(echo, [
        {"pgm_sys_id": "IN0001", "name": "ESSROC CEMENT CORP", "state": "IN"},
        {"pgm_sys_id": "FL0001", "name": "STAMAS YACHT INC", "state": "GA"},
    ])
    return root, nodes, echo


def _read(parsed: Path, table: str) -> list[dict]:
    return [json.loads(line) for line in (parsed / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


def test_enrich_writes_four_tables_and_report(tmp_path):
    root, nodes, echo = _setup(tmp_path)

    report = enrich_all(root, "2026-09-22", ecfr_nodes=nodes, echo_facilities=echo)

    parsed = root / "parsed" / "2026-09-22"
    assert TABLES == ("adi_block", "adi_cfr_reference", "adi_document_relation", "adi_facility_candidate")
    assert all((parsed / f"{table}.jsonl").exists() for table in TABLES)

    blocks = _read(parsed, "adi_block")
    assert [b["kind"] for b in blocks if b["version_id"] == V_QA] == ["header", "question", "answer", "body", "condition", "signature"]
    assert [b["kind"] for b in blocks if b["version_id"] == V_NEG] == ["header", "question", "answer", "body", "signature"]
    assert not [b for b in blocks if b["version_id"] == V_OLD]

    refs = _read(parsed, "adi_cfr_reference")
    by_raw = {(r["version_id"], r["raw_citation"]): r for r in refs}
    assert by_raw[(V_QA, "40 CFR Part 60, Subpart AAAA")]["current_node_key"] is None
    assert by_raw[(V_QA, "40 CFR Part 60, Subpart AAAA")]["review_status"] == "미해결"
    assert by_raw[(V_QA, "40 C.F.R. 63.1207(c)(2)")]["current_node_key"] == "40/63/subpart-EEE/section-63.1207"
    assert by_raw[(V_QA, "40 C.F.R. 63.1207(c)(2)")]["block_no"] == 4
    assert by_raw[(V_NEG, "40 CFR 63.5701")]["current_node_key"] is None
    assert by_raw[(V_NEG, "40 CFR 63.2")]["current_node_key"] == "40/63/subpart-A/section-63.2"
    assert {r["reference_role"] for r in refs} == {"mention"}
    assert all(r["current_ecfr_release_id"] is None and r["historical_ecfr_release_id"] is None for r in refs)

    relations = _read(parsed, "adi_document_relation")
    assert [(r["from_document_id"], r["to_document_id"], r["relation_type"]) for r in relations] == [(D_NEG, D_OLD, "supersedes")]
    assert relations[0]["evidence_version_id"] == V_NEG and relations[0]["evidence_locator"].startswith("block:1;char:")

    candidates = _read(parsed, "adi_facility_candidate")
    assert candidates == [{"document_id": D_QA, "echo_pgm_sys_id": "IN0001", "match_evidence": "name:ESSROC CEMENT;state:IN", "review_status": "검토 전"}]

    assert report["as_of"] == "2026-09-22"
    assert report["status"] == "succeeded"
    assert report["versions"] == 3
    assert report["versions_without_text"] == 1
    assert report["rows"] == {table: len(_read(parsed, table)) for table in TABLES}
    assert report["references_unresolved"] == len([r for r in refs if r["current_node_key"] is None])
    assert report["relation_mentions_skipped"] == 1  # M050031 은 same_file 문구가 있지만 회신 PDF(문서)가 없다
    assert json.loads((parsed / "enrich_report.json").read_text(encoding="utf-8")) == report


def test_rerun_on_same_input_writes_identical_files(tmp_path):
    root, nodes, echo = _setup(tmp_path)
    parsed = root / "parsed" / "2026-09-22"

    enrich_all(root, "2026-09-22", ecfr_nodes=nodes, echo_facilities=echo)
    first = {table: (parsed / f"{table}.jsonl").read_bytes() for table in TABLES}
    enrich_all(root, "2026-09-22", ecfr_nodes=nodes, echo_facilities=echo)

    assert {table: (parsed / f"{table}.jsonl").read_bytes() for table in TABLES} == first


def test_main_prints_report_and_returns_exit_code(tmp_path, capsys):
    root, nodes, echo = _setup(tmp_path)

    code = main(["--root", str(root), "--as-of", "2026-09-22", "--ecfr-nodes", str(nodes), "--echo-facilities", str(echo)])

    assert code == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert printed["rows"]["adi_block"] == 11
