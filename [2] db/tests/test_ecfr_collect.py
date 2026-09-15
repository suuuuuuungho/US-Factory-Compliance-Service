"""SUU-38: 수집 실행 입구 — 제목 API(전) → 목차 → Part 63 XML → 저장 → 제목 API(후) 비교.

네트워크는 쓰지 않는다. 받아오기 함수 두 개(fetch_titles, fetch)를 가짜로 넣는다.
실제 폴더에 쓰지 않는다. pytest tmp_path 를 root 로 쓴다.
"""
import copy
import hashlib
import json
from pathlib import Path

from ecfr_collect import collect
from ecfr_fetch import Fetched

FIXTURES = Path(__file__).parent / "fixtures"
XML = b'<?xml version="1.0"?><DIV5 N="63" TYPE="PART"><HEAD>PART 63</HEAD></DIV5>'


def titles_json(as_of="2026-09-10", in_progress=False) -> dict:
    """저장된 제목 API 샘플을 복사해 Title 40 기준일과 작업 중 여부만 바꾼다."""
    data = copy.deepcopy(json.loads((FIXTURES / "ecfr_titles.json").read_text(encoding="utf-8")))
    next(t for t in data["titles"] if t["number"] == 40)["up_to_date_as_of"] = as_of
    data["meta"]["import_in_progress"] = in_progress
    return data


def fake_titles(before: dict, after: dict):
    """첫 호출은 before, 두 번째 호출은 after 를 돌려준다."""
    answers = iter([before, after])

    def _fetch_titles(*args, **kwargs):
        return next(answers)

    return _fetch_titles


def fake_fetch(calls: list):
    """주소에 따라 목차 샘플 JSON 또는 XML 을 돌려주고, 부른 주소를 calls 에 남긴다."""
    structure = (FIXTURES / "ecfr_structure_sample.json").read_bytes()

    def _fetch(url: str) -> Fetched:
        calls.append(url)
        body = structure if "/structure/" in url else XML
        media = "application/json" if "/structure/" in url else "application/xml"
        return Fetched(body=body, source_url=url, final_url=url, http_status=200, media_type=media, byte_size=len(body))

    return _fetch


def read_run(root, as_of="2026-09-10") -> dict:
    return json.loads((root / "raw" / as_of / "run.json").read_text(encoding="utf-8"))


def test_succeeds_when_before_and_after_match(tmp_path):
    calls = []

    run = collect(tmp_path, fetch_titles=fake_titles(titles_json(), titles_json()), fetch=fake_fetch(calls))

    assert run["status"] == "succeeded"
    assert run["as_of"] == "2026-09-10"
    assert run["counts"] == {"subpart": 5, "subject_group": 3, "section": 9, "appendix": 4}
    assert run["xml_sha256"] == hashlib.sha256(XML).hexdigest()
    assert read_run(tmp_path) == run

    # 기준일은 제목 API 값(2026-09-10)을 쓴다. PC 의 오늘 날짜가 아니다
    assert calls == [
        "https://www.ecfr.gov/api/versioner/v1/structure/2026-09-10/title-40.json",
        "https://www.ecfr.gov/api/versioner/v1/full/2026-09-10/title-40.xml?part=63",
    ]
    manifest = json.loads((tmp_path / "raw" / "2026-09-10" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(e["name"] for e in manifest) == ["title-40-part-63.xml", "title-40-structure.json"]


def test_holds_when_as_of_changes_during_run(tmp_path):
    before, after = titles_json("2026-09-10"), titles_json("2026-09-11")

    run = collect(tmp_path, fetch_titles=fake_titles(before, after), fetch=fake_fetch([]))  # 예외 없이 끝난다

    assert run["status"] == "held"
    assert read_run(tmp_path)["status"] == "held"


def test_holds_without_fetching_when_import_in_progress(tmp_path):
    calls = []
    before = titles_json(in_progress=True)

    run = collect(tmp_path, fetch_titles=fake_titles(before, before), fetch=fake_fetch(calls))

    assert run["status"] == "held"
    assert calls == []  # 목차·XML 을 받기 시작하지 않는다
    assert not (tmp_path / "raw" / "2026-09-10" / "manifest.json").exists()
    assert read_run(tmp_path)["status"] == "held"
