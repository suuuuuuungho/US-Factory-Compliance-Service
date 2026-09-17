"""SUU-96: 검사한 ZIP을 raw/{확인일}/{sha256}/ 폴더로 옮기고 manifest.json에 명세와 함께 기록.

네트워크·ZIP 검사 없음. ``Fetched``와 ``MemberSpec``은 값만 채워 넘긴다.
"""
import hashlib
import json
from datetime import date

from echo_fetch import Fetched
from echo_raw import store_raw
from echo_zip import MemberSpec

AS_OF = date(2026, 9, 17)
BODY_A = b"PK\x03\x04 icis-air"
BODY_B = b"PK\x03\x04 pipeline"
MEMBERS_A = [
    MemberSpec(name="ICIS-AIR_FACILITIES.csv", byte_size=120, header=["PGM_SYS_ID", "FACILITY_NAME"], row_count=3),
    MemberSpec(name="README.txt", byte_size=5, header=None, row_count=None),
]
MEMBERS_B = [MemberSpec(name="PIPELINE_CAA_00_COMPLETE.csv", byte_size=80, header=["SOURCE_ID"], row_count=1)]


def _fetched(tmp_path, name, body, *, url):
    path = tmp_path / "work" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return Fetched(
        path=path,
        sha256=hashlib.sha256(body).hexdigest(),
        source_url=url,
        final_url=url + "?final",
        http_status=200,
        media_type="application/zip",
        etag='"e1"',
        last_modified="Mon, 15 Sep 2026 03:12:00 GMT",
        byte_size=len(body),
    )


def _manifest(root):
    return json.loads((root / "raw" / AS_OF.isoformat() / "manifest.json").read_text(encoding="utf-8"))


def test_moves_zip_under_hash_folder_and_records_manifest(tmp_path):
    root = tmp_path / "echo"
    fetched = _fetched(tmp_path, "ICIS-AIR_downloads.zip", BODY_A, url="https://x/ICIS-AIR_downloads.zip")

    entry = store_raw(root, AS_OF, fetched, MEMBERS_A)

    final = root / "raw" / AS_OF.isoformat() / fetched.sha256 / "ICIS-AIR_downloads.zip"
    assert final.read_bytes() == BODY_A
    assert not fetched.path.exists()  # 복사가 아니라 이동
    assert entry["path"] == f"raw/{AS_OF.isoformat()}/{fetched.sha256}/ICIS-AIR_downloads.zip"
    assert entry["name"] == "ICIS-AIR_downloads.zip"
    assert entry["source_url"] == "https://x/ICIS-AIR_downloads.zip"
    assert entry["final_url"] == "https://x/ICIS-AIR_downloads.zip?final"
    assert entry["http_status"] == 200
    assert entry["media_type"] == "application/zip"
    assert entry["etag"] == '"e1"'
    assert entry["last_modified"] == "Mon, 15 Sep 2026 03:12:00 GMT"
    assert entry["sha256"] == fetched.sha256
    assert entry["byte_size"] == len(BODY_A)
    assert isinstance(entry["fetched_at"], str) and entry["fetched_at"].endswith(("+00:00", "Z"))
    assert entry["members"] == [
        {"name": "ICIS-AIR_FACILITIES.csv", "byte_size": 120, "header": ["PGM_SYS_ID", "FACILITY_NAME"], "row_count": 3},
        {"name": "README.txt", "byte_size": 5, "header": None, "row_count": None},
    ]
    assert _manifest(root) == [entry]  # 파일에 쓴 것과 돌려준 것이 같다


def test_storing_same_hash_twice_keeps_one_file_and_one_entry(tmp_path):
    root = tmp_path / "echo"
    first = _fetched(tmp_path / "1", "ICIS-AIR_downloads.zip", BODY_A, url="https://x/a.zip")
    second = _fetched(tmp_path / "2", "ICIS-AIR_downloads.zip", BODY_A, url="https://x/a.zip")

    entry1 = store_raw(root, AS_OF, first, MEMBERS_A)
    entry2 = store_raw(root, AS_OF, second, MEMBERS_A)

    assert entry2 == entry1  # fetched_at 도 처음 것 그대로
    assert _manifest(root) == [entry1]
    assert not second.path.exists()  # 두 번째 임시 파일은 치운다
    hash_dir = root / "raw" / AS_OF.isoformat() / first.sha256
    assert [p.name for p in hash_dir.iterdir()] == ["ICIS-AIR_downloads.zip"]


def test_two_different_zips_share_one_manifest(tmp_path):
    root = tmp_path / "echo"
    icis = _fetched(tmp_path / "1", "ICIS-AIR_downloads.zip", BODY_A, url="https://x/a.zip")
    pipeline = _fetched(tmp_path / "2", "pipeline_caa_downloads.zip", BODY_B, url="https://x/b.zip")

    store_raw(root, AS_OF, icis, MEMBERS_A)
    store_raw(root, AS_OF, pipeline, MEMBERS_B)

    manifest = _manifest(root)
    assert [e["name"] for e in manifest] == ["ICIS-AIR_downloads.zip", "pipeline_caa_downloads.zip"]
    assert (root / "raw" / AS_OF.isoformat() / icis.sha256 / "ICIS-AIR_downloads.zip").exists()
    assert (root / "raw" / AS_OF.isoformat() / pipeline.sha256 / "pipeline_caa_downloads.zip").exists()
