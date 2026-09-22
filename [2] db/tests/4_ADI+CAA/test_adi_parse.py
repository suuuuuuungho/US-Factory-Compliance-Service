"""SUU-221: raw 전부 → parsed/{as_of}/adi_*.jsonl 5개 + quality_report.json.

네트워크 없음. SUU-114 수집기가 남기는 폴더 모양 그대로 tmp_path 에 만들고 돌린다:
  raw/{raw_as_of}/run.json(html_sha256) + {sha}/adi-results.html          ← SUU-50
  caa_dashboard/raw/{raw_as_of}/run.json + {sha}/caa-dashboard.html        ← SUU-51
  adi_details/raw/{raw_as_of}/details.json                                  ← SUU-58
  adi_letters/shard_*/raw/{raw_as_of}/manifest.json + {sha}/{control}.pdf   ← SUU-54 (name = control_number.pdf)
  dashboard_letters/raw/{raw_as_of}/manifest.json + {sha}/{urlhash}.pdf     ← SUU-56 (source_url = canonical_url)
성공 + held = 목록 행 수(조용히 사라지는 항목 0). PDF 없는 항목은 text_status=text_missing 으로 남는다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from adi_parse import TABLES, main, parse_all
from ecfr_raw import save_raw

FIXTURES = Path(__file__).parent / "fixtures"
RAW_AS_OF = date(2026, 9, 17)
AS_OF = "2026-09-22"
KING_URL = "https://www.epa.gov/system/files/documents/2022-05/King%20Systems%20Corp%20Response_6-16-20.pdf"
WESTVACO_URL = "https://www.epa.gov/system/files/documents/2022-01/genesis-alkali-westvaco_40-cfr-60-subpart-aaaaa_1-15-21.pdf"


def _save(root, name, body, url):
    return save_raw(root, RAW_AS_OF, name, body, source_url=url, final_url=url, http_status=200, media_type="application/pdf")


def _run_json(root, dataset, sha):
    path = root / "raw" / RAW_AS_OF.isoformat() / "run.json"
    path.write_text(json.dumps({"dataset": dataset, "as_of": RAW_AS_OF.isoformat(), "status": "succeeded", "html_sha256": sha}), encoding="utf-8")


def put_lists(root: Path, *, details=True):
    adi_html = (FIXTURES / "adi_results_sample.html").read_bytes()  # 39행
    entry = _save(root, "adi-results.html", adi_html, "https://cfpub.epa.gov/adi/index.cfm?CFID=1&CFTOKEN=x")
    _run_json(root, "adi", entry["sha256"])

    dash_html = (FIXTURES / "adi_dashboard_sample.html").read_bytes()  # 236행
    entry = _save(root / "caa_dashboard", "caa-dashboard.html", dash_html, "https://www.epa.gov/complying-air-emissions-standards-stationary-sources/epa-determinations-compliance-and")
    _run_json(root / "caa_dashboard", "caa_dashboard", entry["sha256"])

    if details:
        path = root / "adi_details" / "raw" / RAW_AS_OF.isoformat() / "details.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps([{
            "control_number": "1800013", "title": "Alternative Monitoring Plan for Internal Floating Roof Storage Tanks",
            "letter_date_raw": "05/11/2018", "author": "Sara Breneman", "categories": ["MACT", "NSPS"],
            "office": "Region 5", "abstract": "Q: Does EPA approve an AMP? A: Yes.",
        }]), encoding="utf-8")


def put_letters(root: Path, make_pdf, *, broken_dashboard_pdf=True):
    shared = make_pdf(["Shared response letter"])
    _save(root / "adi_letters" / "shard_0", "1800013.pdf", shared, "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=1800013")
    _save(root / "adi_letters" / "shard_1", "M170010.pdf", make_pdf(["Engines at pump station", None]), "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M170010")
    _save(root / "dashboard_letters", hashlib.sha256(KING_URL.encode()).hexdigest() + ".pdf", shared, KING_URL)
    if broken_dashboard_pdf:
        _save(root / "dashboard_letters", hashlib.sha256(WESTVACO_URL.encode()).hexdigest() + ".pdf", b"not a pdf", WESTVACO_URL)


def put_all(root, make_pdf):
    put_lists(root)
    put_letters(root, make_pdf)


def out_dir(root):
    return root / "parsed" / AS_OF


def read_jsonl(root, table):
    return [json.loads(line) for line in (out_dir(root) / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


def read_report(root):
    return json.loads((out_dir(root) / "quality_report.json").read_text(encoding="utf-8"))


def test_entries_plus_held_equals_list_rows_and_keys_are_unique(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_all(root, make_pdf)

    report = parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())

    assert report["status"] == "succeeded"
    assert report["entries"] == 39 + 236
    assert report["succeeded"] + len(report["held"]) == report["entries"]
    assert len(report["held"]) == 1
    held = report["held"][0]
    assert held["source_system"] == "caa_dashboard"
    assert held["reason"]

    entries = read_jsonl(root, "adi_source_entry")
    assert len(entries) == 275  # held 항목도 목록 행으로는 남는다
    keys = [(e["source_system"], e["source_key"]) for e in entries]
    assert len(set(keys)) == 275

    by_key = {k: e for k, e in zip(keys, entries)}
    assert by_key[("adi", "1800013")]["text_status"] == "ok"
    assert by_key[("adi", "1800013")]["abstract"] == "Q: Does EPA approve an AMP? A: Yes."
    assert by_key[("adi", "M170010")]["text_status"] == "ok"
    assert by_key[("adi", "1800038")]["text_status"] == "text_missing"  # PDF 안 받은 항목(2005년 이전 등)
    westvaco = next(e for e in entries if e["canonical_url"] == WESTVACO_URL)
    assert westvaco["text_status"] == "text_failed"
    assert (westvaco["source_system"], westvaco["source_key"]) == (held["source_system"], held["source_key"])


def test_shared_pdf_across_lists_is_one_document_linked_twice(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_all(root, make_pdf)

    parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())

    docs = read_jsonl(root, "adi_document")
    versions = read_jsonl(root, "adi_document_version")
    links = read_jsonl(root, "adi_entry_document")
    pages = read_jsonl(root, "adi_page")
    assert len(docs) == 2  # shared(1800013 = King) + M170010. 깨진 PDF 는 문서가 아니다
    assert len(versions) == 2
    assert len(links) == 3
    shared_sha = next(v["sha256"] for v in versions if v["text_content"] == "Shared response letter")
    shared_version = next(v["version_id"] for v in versions if v["sha256"] == shared_sha)
    linked = sorted(l["source_system"] for l in links if l["version_id"] == shared_version)
    assert linked == ["adi", "caa_dashboard"]
    assert len(pages) == 3  # 1 + 2
    assert sorted(p["status"] for p in pages) == ["empty", "ok", "ok"]
    assert {v["version_id"] for v in versions} == {p["version_id"] for p in pages}


def test_missing_details_file_only_blanks_abstract(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_lists(root, details=False)
    put_letters(root, make_pdf)

    report = parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())

    assert report["status"] == "succeeded"
    assert report["details_missing"] == 39
    assert all(e["abstract"] is None for e in read_jsonl(root, "adi_source_entry") if e["source_system"] == "adi")


def test_report_counts_rows_per_table_and_matches_file(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_all(root, make_pdf)

    report = parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())

    assert report["as_of"] == AS_OF
    assert report["raw_as_of"] == RAW_AS_OF.isoformat()
    assert report["files"] == 4
    assert report["details_missing"] == 38
    assert report["rows"] == {
        "adi_source_entry": 275, "adi_document": 2, "adi_document_version": 2, "adi_entry_document": 3, "adi_page": 3,
    }
    assert report == read_report(root)
    assert set(TABLES) == set(report["rows"])


def test_rerun_on_same_input_writes_identical_files(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_all(root, make_pdf)

    parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())
    first = {t: (out_dir(root) / f"{t}.jsonl").read_bytes() for t in TABLES}
    first_report = read_report(root)
    parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())
    second = {t: (out_dir(root) / f"{t}.jsonl").read_bytes() for t in TABLES}
    second_report = read_report(root)

    assert first == second
    for key in ("started_at", "finished_at"):
        first_report.pop(key), second_report.pop(key)
    assert first_report == second_report


def test_latest_raw_folder_is_used_when_raw_as_of_is_omitted(tmp_path, make_pdf):
    root = tmp_path / "adi"
    put_all(root, make_pdf)
    (root / "raw" / "2026-01-01").mkdir()  # 더 오래된 빈 폴더는 무시

    report = parse_all(root, AS_OF)

    assert report["raw_as_of"] == RAW_AS_OF.isoformat()
    assert report["entries"] == 275


def test_main_prints_report_and_returns_exit_code(tmp_path, make_pdf, capsys):
    root = tmp_path / "adi"
    put_all(root, make_pdf)

    code = main(["--root", str(root), "--as-of", AS_OF, "--raw-as-of", RAW_AS_OF.isoformat()])

    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "succeeded"
    assert printed["entries"] == 275
    assert (out_dir(root) / "quality_report.json").exists()


def test_same_pdf_collected_twice_under_one_control_number_is_linked_once(tmp_path, make_pdf):
    """SUU-225: 실수집에서 PDF 5개가 adi_letters/raw 와 shard_* 에 두 번 받아졌다(같은 이름·URL·sha256).
    같은 (source_system, source_key, sha256) 는 한 번만 세어 adi_entry_document 에 중복 행이 생기지 않아야 한다."""
    root = tmp_path / "adi"
    put_all(root, make_pdf)
    m170010 = next((root / "adi_letters" / "shard_1").glob(f"raw/{RAW_AS_OF.isoformat()}/*/M170010.pdf")).read_bytes()
    _save(root / "adi_letters", "M170010.pdf", m170010, "https://cfpub.epa.gov/adi/index.cfm?fuseaction=home.dsp_show_file_contents&id=M170010")

    report = parse_all(root, AS_OF, raw_as_of=RAW_AS_OF.isoformat())

    links = read_jsonl(root, "adi_entry_document")
    keys = [(l["source_system"], l["source_key"], l["version_id"]) for l in links]
    assert len(keys) == len(set(keys)) == 3
    assert len(read_jsonl(root, "adi_document_version")) == 2
    assert report["files"] == 4  # 1800013 + M170010 + King + Westvaco. 두 번 받은 파일은 하나로 센다
