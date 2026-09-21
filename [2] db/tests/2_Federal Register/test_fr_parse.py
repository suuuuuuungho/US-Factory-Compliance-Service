"""SUU-207: raw/ 아래 상세 JSON 전부 → parsed/{as_of}/fr_*.jsonl 4개 + quality_report.json.

네트워크 없음. fr_raw.store_raw 로 tmp_path/raw 에 원본을 넣고 돌린다.
깨진 JSON 은 held 로 사유와 함께 남고, 성공 + held = 문서 수여야 한다(조용히 사라지는 문서 0).
"""
import hashlib
import json
from pathlib import Path

from fr_fetch import Fetched, detail_url
from fr_parse import parse_all, main
from fr_raw import store_raw

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = "2026-09-21"
DOCS = [("2003-05-27", "03-5521"), ("2003-08-28", "03-5521"), ("2026-02-24", "2026-03638")]
TABLES = ["fr_document", "fr_identifier", "fr_cfr_reference", "fr_date_event"]


def _fetched(body: bytes, url: str) -> Fetched:
    return Fetched(body, url, url, 200, "", len(body), hashlib.sha256(body).hexdigest())


def put_document(root, pub, num, *, detail: bytes | None = None, xml=True, pdf=True):
    """SUU-206 수집기가 남기는 모양 그대로 raw/{연도}/{발행일}_{번호}/ 에 원본을 둔다."""
    if detail is None:
        detail = (FIXTURES / f"detail_{pub}_{num}.json").read_bytes()
    store_raw(root, pub, num, _fetched(detail, detail_url(num, pub)), kind="detail")
    if xml:
        store_raw(root, pub, num, _fetched(f"<RULE>{num}</RULE>".encode(), f"https://x.test/{pub}/{num}.xml"), kind="xml")
    if pdf:
        store_raw(root, pub, num, _fetched(f"%PDF-1.7 {num}".encode(), f"https://x.test/{pub}/{num}.pdf"), kind="pdf")


def put_all(root):
    for pub, num in DOCS:
        put_document(root, pub, num)


def out_dir(root):
    return root / "parsed" / AS_OF


def read_jsonl(root, table):
    return [json.loads(line) for line in (out_dir(root) / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


def read_report(root):
    return json.loads((out_dir(root) / "quality_report.json").read_text(encoding="utf-8"))


def test_real_2026_03638_makes_expected_rows_in_all_four_tables(tmp_path):
    root = tmp_path / "fr"
    put_document(root, "2026-02-24", "2026-03638")

    report = parse_all(root, AS_OF)

    assert report["status"] == "succeeded"
    docs = read_jsonl(root, "fr_document")
    assert len(docs) == 1
    assert docs[0]["document_key"] == "2026-02-24/2026-03638"
    assert docs[0]["subtype"] is None
    assert docs[0]["content_hash"] == hashlib.sha256((FIXTURES / "detail_2026-02-24_2026-03638.json").read_bytes()).hexdigest()
    assert docs[0]["raw_metadata"]["document_number"] == "2026-03638"
    assert docs[0]["body_status"] == "xml"

    ids = read_jsonl(root, "fr_identifier")
    assert sorted((r["identifier_kind"], r["identifier_value"]) for r in ids) == [
        ("docket", "EPA-HQ-OAR-2018-0794"), ("rin", "2060-AW68"),
    ]

    refs = read_jsonl(root, "fr_cfr_reference")
    assert len(refs) == 1
    assert (refs[0]["title"], refs[0]["part"], refs[0]["subpart"]) == (40, "63", None)
    assert refs[0]["review_status"] == "검토 전"

    events = read_jsonl(root, "fr_date_event")
    assert len(events) == 1
    assert (events[0]["event_kind"], events[0]["event_date"]) == ("effective", "2026-04-27")
    assert events[0]["review_status"] == "검토 전"


def test_both_03_5521_publications_survive_as_two_documents(tmp_path):
    root = tmp_path / "fr"
    put_all(root)

    parse_all(root, AS_OF)

    docs = read_jsonl(root, "fr_document")
    keys = sorted(d["document_key"] for d in docs)
    assert keys == ["2003-05-27/03-5521", "2003-08-28/03-5521", "2026-02-24/2026-03638"]
    correction = next(d for d in docs if d["document_key"] == "2003-08-28/03-5521")
    assert correction["effective_on"] is None
    # effective_on 없는 정정문은 사건 0행, 문서는 살아있다
    assert [e for e in read_jsonl(root, "fr_date_event") if e["document_key"] == "2003-08-28/03-5521"] == []
    assert len(read_jsonl(root, "fr_date_event")) == 2
    assert len(read_jsonl(root, "fr_cfr_reference")) == 3


def test_broken_json_is_held_with_reason_and_nothing_disappears(tmp_path):
    root = tmp_path / "fr"
    put_document(root, "2003-05-27", "03-5521")
    put_document(root, "2003-08-28", "03-5521", detail=b'{"document_number": "03-5521", "publication_date": ')  # 잘린 JSON
    put_document(root, "2026-02-24", "2026-03638")

    report = parse_all(root, AS_OF)

    assert report["documents"] == 3
    assert report["succeeded"] == 2
    assert len(report["held"]) == 1
    assert report["succeeded"] + len(report["held"]) == report["documents"]
    held = report["held"][0]
    assert (held["publication_date"], held["document_number"]) == ("2003-08-28", "03-5521")
    assert held["reason"]  # 사유가 비어있지 않다
    assert sorted(d["document_key"] for d in read_jsonl(root, "fr_document")) == ["2003-05-27/03-5521", "2026-02-24/2026-03638"]
    assert report["status"] == "succeeded"  # 한 건 보류로 전체를 실패로 만들지 않는다


def test_folder_without_detail_is_held_not_skipped(tmp_path):
    root = tmp_path / "fr"
    put_document(root, "2026-02-24", "2026-03638")
    store_raw(root, "1994-01-11", "94-752", _fetched(b"%PDF-1.7 94-752", "https://x.test/94-752.pdf"), kind="pdf")  # 상세 없이 PDF 만

    report = parse_all(root, AS_OF)

    assert report["documents"] == 2
    assert report["succeeded"] == 1
    assert [(h["publication_date"], h["document_number"]) for h in report["held"]] == [("1994-01-11", "94-752")]


def test_report_counts_rows_per_table(tmp_path):
    root = tmp_path / "fr"
    put_all(root)

    report = parse_all(root, AS_OF)

    assert report["as_of"] == AS_OF
    assert report["rows"] == {"fr_document": 3, "fr_identifier": 4, "fr_cfr_reference": 3, "fr_date_event": 2}
    assert report == read_report(root)


def test_rerun_on_same_input_writes_identical_files(tmp_path):
    root = tmp_path / "fr"
    put_all(root)

    parse_all(root, AS_OF)
    first = {t: (out_dir(root) / f"{t}.jsonl").read_bytes() for t in TABLES}
    first_report = read_report(root)
    parse_all(root, AS_OF)
    second = {t: (out_dir(root) / f"{t}.jsonl").read_bytes() for t in TABLES}
    second_report = read_report(root)

    assert first == second
    for key in ("started_at", "finished_at"):
        first_report.pop(key), second_report.pop(key)
    assert first_report == second_report


def test_main_prints_report_and_returns_exit_code(tmp_path, capsys):
    root = tmp_path / "fr"
    put_all(root)

    code = main(["--root", str(root), "--as-of", AS_OF])

    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "succeeded"
    assert printed["documents"] == 3
    assert (out_dir(root) / "quality_report.json").exists()
