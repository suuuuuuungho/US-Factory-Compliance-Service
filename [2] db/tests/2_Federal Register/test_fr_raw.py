"""SUU-206: 받은 파일을 raw/{연도}/{발행일}_{문서번호}/{sha256}/ 에 두고 manifest.json 에 기록한다.

네트워크 없음. Fetched 는 값만 채워 넘긴다.
"""
import hashlib
import json

from fr_fetch import Fetched
from fr_raw import store_raw


def _fetched(body: bytes, url: str, media_type: str) -> Fetched:
    return Fetched(
        body=body, source_url=url, final_url=url, http_status=200,
        media_type=media_type, byte_size=len(body), sha256=hashlib.sha256(body).hexdigest(),
    )


def _manifest(root, year, folder):
    return json.loads((root / "raw" / year / folder / "manifest.json").read_text(encoding="utf-8"))


def test_stores_under_year_date_number_hash_and_records_manifest(tmp_path):
    root = tmp_path / "fr"
    body = b'{"document_number": "2026-03638"}'
    fetched = _fetched(body, "https://www.federalregister.gov/api/v1/documents/2026-03638.json?publication_date=2026-02-24", "application/json")

    entry = store_raw(root, "2026-02-24", "2026-03638", fetched, kind="detail")

    final = root / "raw" / "2026" / "2026-02-24_2026-03638" / fetched.sha256 / "2026-03638.json"
    assert final.read_bytes() == body
    manifest = _manifest(root, "2026", "2026-02-24_2026-03638")
    assert len(manifest) == 1
    assert manifest[0] == entry
    assert entry["kind"] == "detail"
    assert entry["sha256"] == fetched.sha256
    assert entry["source_url"] == fetched.source_url
    assert entry["path"] == "raw/2026/2026-02-24_2026-03638/" + fetched.sha256 + "/2026-03638.json"
    assert entry["fetched_at"]


def test_kind_decides_file_extension(tmp_path):
    root = tmp_path / "fr"
    xml = store_raw(root, "2026-02-24", "2026-03638", _fetched(b"<RULE/>", "https://x/a.xml", "text/xml"), kind="xml")
    pdf = store_raw(root, "2026-02-24", "2026-03638", _fetched(b"%PDF-1.7", "https://x/a.pdf", "application/pdf"), kind="pdf")

    assert xml["path"].endswith("/2026-03638.xml")
    assert pdf["path"].endswith("/2026-03638.pdf")
    assert len(_manifest(root, "2026", "2026-02-24_2026-03638")) == 2


def test_same_bytes_twice_makes_no_second_folder_or_entry(tmp_path):
    root = tmp_path / "fr"
    fetched = _fetched(b"<RULE/>", "https://x/a.xml", "text/xml")

    first = store_raw(root, "2003-05-27", "03-5521", fetched, kind="xml")
    second = store_raw(root, "2003-05-27", "03-5521", fetched, kind="xml")

    assert second == first
    doc_dir = root / "raw" / "2003" / "2003-05-27_03-5521"
    assert [p.name for p in doc_dir.iterdir() if p.is_dir()] == [fetched.sha256]
    assert len(_manifest(root, "2003", "2003-05-27_03-5521")) == 1


def test_two_publications_of_one_number_live_in_separate_folders(tmp_path):
    root = tmp_path / "fr"
    store_raw(root, "2003-05-27", "03-5521", _fetched(b'{"a":1}', "https://x/1", "application/json"), kind="detail")
    store_raw(root, "2003-08-28", "03-5521", _fetched(b'{"a":2}', "https://x/2", "application/json"), kind="detail")

    assert (root / "raw" / "2003" / "2003-05-27_03-5521" / "manifest.json").exists()
    assert (root / "raw" / "2003" / "2003-08-28_03-5521" / "manifest.json").exists()
