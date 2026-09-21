"""SUU-206: FR 수집 진입점 — 목록 → 문서마다 상세 JSON·XML·PDF → 보관 → 요약.

네트워크 없음. fetch 를 가짜로 넣는다. 목록은 fixtures/list_page{1,2,3}.json, 상세는 fixtures/detail_*.json.
"""
import json
from datetime import date
from pathlib import Path
from urllib.error import HTTPError

from fr_collect import collect, main
from fr_fetch import detail_url
from fr_list import list_url

FIXTURES = Path(__file__).parent / "fixtures"
END = date(2026, 9, 21)

DOCS = [  # (발행일, 문서번호) — fixtures 목록 5행과 같다
    ("1994-01-11", "94-752"),
    ("2003-05-27", "03-5521"),
    ("2003-08-28", "03-5521"),
    ("2026-02-24", "2026-03638"),
    ("2026-09-01", "2026-09999"),
]


def _xml_url(pub, num):
    return f"https://www.federalregister.gov/documents/full_text/xml/{pub.replace('-', '/')}/{num}.xml"


def _pdf_url(pub, num):
    return f"https://www.govinfo.gov/content/pkg/FR-{pub}/pdf/{num}.pdf"


def _detail(pub, num) -> dict:
    """실제 상세 JSON 이 있으면 그것, 없으면 최소 상세를 만든다."""
    path = FIXTURES / f"detail_{pub}_{num}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "document_number": num, "publication_date": pub, "type": "Rule",
        "full_text_xml_url": _xml_url(pub, num) if num != "94-752" else None,  # 1994 문서는 XML 없음
        "pdf_url": _pdf_url(pub, num),
    }


def make_fetch(calls: list, *, broken: dict | None = None):
    """url → bytes. broken 에 있는 url 은 그 값(예외나 바이트)을 대신 돌려준다."""
    pages = [json.loads((FIXTURES / f"list_page{i}.json").read_text(encoding="utf-8")) for i in (1, 2, 3)]
    bodies: dict[str, bytes] = {list_url(END): json.dumps(pages[0]).encode()}
    bodies[pages[0]["next_page_url"]] = json.dumps(pages[1]).encode()
    bodies[pages[1]["next_page_url"]] = json.dumps(pages[2]).encode()
    for pub, num in DOCS:
        detail = _detail(pub, num)
        bodies[detail_url(num, pub)] = json.dumps(detail).encode()
        if detail.get("full_text_xml_url"):
            bodies[detail["full_text_xml_url"]] = f"<RULE>{num} {pub}</RULE>".encode()
        if detail.get("pdf_url"):
            bodies[detail["pdf_url"]] = f"%PDF-1.7 {num} {pub}".encode()
    broken = broken or {}

    def _fetch(url: str) -> bytes:
        calls.append(url)
        if url in broken:
            value = broken[url]
            if isinstance(value, Exception):
                raise value
            return value
        return bodies[url]

    return _fetch


def _not_found(url):
    return HTTPError(url, 404, "Not Found", hdrs=None, fp=None)


def _manifest(root, pub, num):
    return json.loads((root / "raw" / pub[:4] / f"{pub}_{num}" / "manifest.json").read_text(encoding="utf-8"))


def test_collects_detail_xml_pdf_for_every_listed_document(tmp_path):
    root = tmp_path / "fr"
    calls: list[str] = []

    run = collect(root, END, fetch=make_fetch(calls))

    assert run["status"] == "succeeded"
    assert run["end_date"] == "2026-09-21"
    assert run["pages"] == 3
    assert run["count"] == 5
    assert run["documents"] == 5
    assert run["obtained"] == {"detail": 5, "xml": 4, "pdf": 5}  # 94-752 는 XML 주소가 없다
    assert run["missing"] == [
        {"publication_date": "1994-01-11", "document_number": "94-752", "kind": "xml", "reason": "no url"},
    ]
    kinds = sorted(e["kind"] for e in _manifest(root, "2026-02-24", "2026-03638"))
    assert kinds == ["detail", "pdf", "xml"]
    assert sorted(e["kind"] for e in _manifest(root, "1994-01-11", "94-752")) == ["detail", "pdf"]


def test_detail_is_fetched_with_publication_date_for_both_03_5521(tmp_path):
    calls: list[str] = []

    collect(tmp_path / "fr", END, fetch=make_fetch(calls))

    assert detail_url("03-5521", "2003-05-27") in calls
    assert detail_url("03-5521", "2003-08-28") in calls
    assert "https://www.federalregister.gov/api/v1/documents/03-5521.json" not in calls


def test_404_goes_to_retry_list_and_run_continues(tmp_path):
    root = tmp_path / "fr"
    bad_xml = _xml_url("2003-05-27", "03-5521")
    calls: list[str] = []

    run = collect(root, END, fetch=make_fetch(calls, broken={bad_xml: _not_found(bad_xml)}))

    assert run["status"] == "succeeded"  # 문서 하나의 원문 실패로 전체를 멈추지 않는다
    assert run["obtained"] == {"detail": 5, "xml": 3, "pdf": 5}
    retry = [json.loads(l) for l in (root / "raw" / "lists" / "2026-09-21" / "retry.jsonl").read_text(encoding="utf-8").splitlines()]
    assert retry == [
        {"publication_date": "2003-05-27", "document_number": "03-5521", "kind": "xml",
         "url": bad_xml, "reason": "HTTP 404"},
    ]
    assert {"publication_date": "2003-05-27", "document_number": "03-5521", "kind": "xml", "reason": "HTTP 404"} in run["missing"]
    # 같은 문서의 PDF 는 그래도 받았다
    assert "pdf" in [e["kind"] for e in _manifest(root, "2003-05-27", "03-5521")]


def test_html_in_place_of_xml_is_recorded_not_stored(tmp_path):
    root = tmp_path / "fr"
    xml = _xml_url("2026-02-24", "2026-03638")

    run = collect(root, END, fetch=make_fetch([], broken={xml: b"<!DOCTYPE html><html>Sign in</html>"}))

    assert "xml" not in [e["kind"] for e in _manifest(root, "2026-02-24", "2026-03638")]
    missing = [m for m in run["missing"] if m["document_number"] == "2026-03638"]
    assert missing[0]["kind"] == "xml"
    assert "html" in missing[0]["reason"].lower() or "format" in missing[0]["reason"].lower()


def test_rerun_skips_files_already_in_manifest(tmp_path):
    root = tmp_path / "fr"
    first_calls: list[str] = []
    collect(root, END, fetch=make_fetch(first_calls))

    second_calls: list[str] = []
    run = collect(root, END, fetch=make_fetch(second_calls))

    list_calls = [c for c in second_calls if "api/v1/documents?" in c or c == list_url(END)]
    assert len(list_calls) == 3  # 목록은 다시 본다
    assert len(second_calls) == len(list_calls)  # 상세·XML·PDF 는 하나도 다시 받지 않는다
    assert run["obtained"] == {"detail": 5, "xml": 4, "pdf": 5}
    assert len(_manifest(root, "2026-02-24", "2026-03638")) == 3


def test_list_failure_stops_before_any_document(tmp_path):
    root = tmp_path / "fr"
    calls: list[str] = []
    first = list_url(END)

    run = collect(root, END, fetch=make_fetch(calls, broken={first: _not_found(first)}))

    assert run["status"] == "failed"
    assert "404" in run["reason"]
    assert calls == [first]
    assert not (root / "raw" / "2026").exists()


def test_main_prints_summary_and_returns_exit_code(tmp_path, capsys, monkeypatch):
    import fr_collect

    monkeypatch.setattr(fr_collect, "fetch", make_fetch([]))

    code = main(["--root", str(tmp_path / "fr"), "--end", "2026-09-21"])

    assert code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "succeeded"
    assert printed["obtained"]["detail"] == 5
