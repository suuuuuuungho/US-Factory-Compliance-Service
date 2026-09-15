"""SUU-37: 받은 원본을 raw/{기준일}/{sha256}/{파일명} 에 저장하고 manifest.json 에 기록한다.

실제 폴더에 쓰지 않는다. pytest tmp_path 를 root 로 쓴다. 네트워크는 쓰지 않는다.
"""
import hashlib
import json
import os
from datetime import date

from ecfr_raw import save_raw

AS_OF = date(2026, 9, 10)
BODY = b'<?xml version="1.0"?><DIV5 N="63" TYPE="PART"/>'
INFO = dict(
    source_url="https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63",
    final_url="https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63",
    http_status=200,
    media_type="application/xml; charset=utf-8",
)


def read_manifest(root):
    return json.loads((root / "raw" / "2026-09-10" / "manifest.json").read_text(encoding="utf-8"))


def test_saves_file_under_hash_folder_and_records_manifest(tmp_path):
    entry = save_raw(tmp_path, AS_OF, "title-40-part-63.xml", BODY, **INFO)

    sha = hashlib.sha256(BODY).hexdigest()
    saved = tmp_path / "raw" / "2026-09-10" / sha / "title-40-part-63.xml"
    assert saved.read_bytes() == BODY
    assert entry["sha256"] == sha
    assert entry["byte_size"] == len(BODY)
    assert entry["name"] == "title-40-part-63.xml"
    for key in ("source_url", "final_url", "http_status", "media_type", "fetched_at"):
        assert key in entry, key
    assert entry["source_url"] == INFO["source_url"]
    assert entry["http_status"] == 200

    assert read_manifest(tmp_path) == [entry]


def test_saving_same_content_twice_keeps_one_file_and_one_entry(tmp_path):
    first = save_raw(tmp_path, AS_OF, "title-40-part-63.xml", BODY, **INFO)
    second = save_raw(tmp_path, AS_OF, "title-40-part-63.xml", BODY, **INFO)

    assert second["sha256"] == first["sha256"]
    files = [p for p in (tmp_path / "raw" / "2026-09-10").rglob("*") if p.is_file() and p.name != "manifest.json"]
    assert len(files) == 1
    assert len(read_manifest(tmp_path)) == 1


def test_writes_part_file_first_then_renames(tmp_path, monkeypatch):
    real_replace = os.replace
    moves = []

    def recording_replace(src, dst):
        moves.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", recording_replace)

    entry = save_raw(tmp_path, AS_OF, "title-40-part-63.xml", BODY, **INFO)

    final = tmp_path / "raw" / "2026-09-10" / entry["sha256"] / "title-40-part-63.xml"
    assert (str(final) + ".part", str(final)) in moves  # .part 에 쓰고 이름을 바꿨다
    assert not list(tmp_path.rglob("*.part"))  # 끝나면 .part 가 남지 않는다
