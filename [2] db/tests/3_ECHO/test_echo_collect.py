"""SUU-97: ECHO 수집 진입점 — ZIP 2개를 받고 → 검사하고 → 보관하고 → 요약을 돌려준다.

네트워크·실제 ZIP 없음. fetch_to_file / inspect_zip / store_raw 를 가짜로 넣는다.
"""
import hashlib
from datetime import date

from echo_collect import ICIS_AIR_URL, PIPELINE_URL, collect, main
from echo_fetch import Fetched
from echo_zip import ICIS_AIR_MEMBERS, PIPELINE_MEMBERS, MemberSpec, ZipCheckError

AS_OF = date(2026, 9, 17)
BODIES = {
    ICIS_AIR_URL: b"PK\x03\x04 icis-air",
    PIPELINE_URL: b"PK\x03\x04 pipeline",
}
SPECS = {
    "ICIS-AIR_downloads.zip": [
        MemberSpec(name="ICIS-AIR_FACILITIES.csv", byte_size=120, header=["PGM_SYS_ID"], row_count=3),
        MemberSpec(name="ICIS-AIR_PROGRAMS.csv", byte_size=80, header=["PGM_SYS_ID"], row_count=2),
        MemberSpec(name="README.txt", byte_size=5, header=None, row_count=None),
    ],
    "pipeline_caa_downloads.zip": [
        MemberSpec(name="PIPELINE_CAA_00_COMPLETE.csv", byte_size=60, header=["SOURCE_ID"], row_count=7),
    ],
}


def fake_fetch(calls: list):
    """dest 에 가짜 ZIP 바이트를 쓰고 Fetched 를 돌려준다. 부른 주소를 calls 에 남긴다."""

    def _fetch(url, dest):
        calls.append(url)
        body = BODIES[url]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return Fetched(
            path=dest,
            sha256=hashlib.sha256(body).hexdigest(),
            source_url=url,
            final_url=url,
            http_status=200,
            media_type="application/zip",
            etag=None,
            last_modified=None,
            byte_size=len(body),
        )

    return _fetch


def fake_inspect(calls: list, *, fail_on: str | None = None):
    """이름별 MemberSpec 을 돌려준다. fail_on 이름이면 ZipCheckError."""

    def _inspect(path, *, required):
        calls.append((path.name, tuple(required)))
        if path.name == fail_on:
            raise ZipCheckError(f"missing required members: {required[0]}")
        return SPECS[path.name]

    return _inspect


def fake_store(calls: list):
    def _store(root, as_of, fetched, members):
        calls.append((as_of, fetched.path.name, fetched.sha256, len(members)))
        return {"name": fetched.path.name, "sha256": fetched.sha256}

    return _store


def test_summarizes_each_zip_with_hash_member_and_row_counts(tmp_path):
    fetched, inspected, stored = [], [], []

    run = collect(
        tmp_path,
        as_of=AS_OF,
        fetch_to_file=fake_fetch(fetched),
        inspect_zip=fake_inspect(inspected),
        store_raw=fake_store(stored),
    )

    assert run["status"] == "succeeded"
    assert run["as_of"] == "2026-09-17"
    assert fetched == [ICIS_AIR_URL, PIPELINE_URL]  # 순서: ICIS-Air 먼저
    assert inspected == [
        ("ICIS-AIR_downloads.zip", tuple(ICIS_AIR_MEMBERS)),
        ("pipeline_caa_downloads.zip", tuple(PIPELINE_MEMBERS)),
    ]
    assert stored == [
        (AS_OF, "ICIS-AIR_downloads.zip", hashlib.sha256(BODIES[ICIS_AIR_URL]).hexdigest(), 3),
        (AS_OF, "pipeline_caa_downloads.zip", hashlib.sha256(BODIES[PIPELINE_URL]).hexdigest(), 1),
    ]
    assert run["zips"] == [
        {
            "name": "ICIS-AIR_downloads.zip",
            "sha256": hashlib.sha256(BODIES[ICIS_AIR_URL]).hexdigest(),
            "byte_size": len(BODIES[ICIS_AIR_URL]),
            "member_count": 3,
            "row_count": 5,  # CSV 행만 더한다. README 는 None 이라 뺀다
        },
        {
            "name": "pipeline_caa_downloads.zip",
            "sha256": hashlib.sha256(BODIES[PIPELINE_URL]).hexdigest(),
            "byte_size": len(BODIES[PIPELINE_URL]),
            "member_count": 1,
            "row_count": 7,
        },
    ]


def test_check_failure_stores_nothing(tmp_path):
    stored = []

    run = collect(
        tmp_path,
        as_of=AS_OF,
        fetch_to_file=fake_fetch([]),
        inspect_zip=fake_inspect([], fail_on="pipeline_caa_downloads.zip"),  # 두 번째 ZIP 만 실패
        store_raw=fake_store(stored),
    )

    assert run["status"] == "failed"
    assert "pipeline_caa_downloads.zip" in run["reason"]
    assert "missing required members" in run["reason"]
    assert stored == []  # 첫 ZIP 이 통과했어도 보관하지 않는다
    assert not (tmp_path / "raw").exists()
    assert not list((tmp_path / "work").glob("*.zip"))  # 받다 만 파일도 치운다


def test_main_exit_code_follows_status(tmp_path, monkeypatch):
    seen = []

    def _collect(root, **kwargs):
        seen.append(root)
        return {"status": "failed", "as_of": "2026-09-17", "reason": "x", "zips": []}

    monkeypatch.setattr("echo_collect.collect", _collect)

    assert main(["--root", str(tmp_path)]) == 2
    assert seen == [tmp_path]

    monkeypatch.setattr("echo_collect.collect", lambda root, **kw: {"status": "succeeded", "as_of": "2026-09-17", "reason": None, "zips": []})

    assert main(["--root", str(tmp_path)]) == 0
