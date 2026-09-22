"""SUU-256: Dashboard 판정서한 128건 → 청크 → Kanon 2 임베딩 → rag_chunk 적재.

입력(로컬, 네트워크 없음):
  decision-letters.json            ← SUU-252 (pdf_url 있는 것만 = 128건)
  parsed/{as_of}/adi_entry_document.jsonl   source_key → version_id
  parsed/{as_of}/adi_page.jsonl             version_id → 페이지 텍스트
청크는 서한 한 통의 페이지를 이어붙인 뒤 문단 단위로 자른다(페이지 넘어가는 문장이 안 끊긴다).
저장은 rag_chunk, release_id 는 기존 adi release(LETTER_RELEASE_ID). eCFR release 와 섞이지 않는다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from letter_chunk import (
    ECFR_RELEASE_ID,
    LETTER_RELEASE_ID,
    MAX_CHUNK_CHARS,
    build_letter_chunks,
    index_letter_chunk,
    letter_pages,
)

ROOT = Path(__file__).resolve().parents[3]
REAL_PARSED = ROOT / "[2] db" / "4) ADI+CAA" / "parsed" / "2026-09-22"
REAL_LETTERS = ROOT / "[4]frontend" / "public" / "decision-letters.json"

EMBEDDING = [0.1] * 1792


# ---------------------------------------------------------------------------
# fixture: 서한 2건, 페이지 3장. A 는 1쪽→2쪽으로 문장이 넘어간다. C 는 pdf_url 없음(제외).
# ---------------------------------------------------------------------------
def _jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


@pytest.fixture
def parsed(tmp_path: Path):
    letters = tmp_path / "decision-letters.json"
    letters.write_text(json.dumps({"letters": [
        {"source_key": "aaaa", "facility_name": "Domtar", "title": "Kraft Pulp Mills", "subparts": ["S"],
         "date": "2025-03-10", "pdf_url": "https://www.epa.gov/a.pdf"},
        {"source_key": "bbbb", "facility_name": "Ash Grove", "title": "Cement", "subparts": ["LLL"],
         "date": "2024-01-01", "pdf_url": "https://www.epa.gov/b.pdf"},
        {"source_key": "cccc", "facility_name": "No PDF", "title": "Held", "subparts": [], "date": None, "pdf_url": None},
    ]}), encoding="utf-8")

    parsed_dir = tmp_path / "parsed" / "2026-09-22"
    _jsonl(parsed_dir / "adi_entry_document.jsonl", [
        {"source_system": "caa_dashboard", "source_key": "aaaa", "version_id": "v-a", "match_method": "fetched_from_entry", "match_status": "confirmed"},
        {"source_system": "caa_dashboard", "source_key": "bbbb", "version_id": "v-b", "match_method": "fetched_from_entry", "match_status": "confirmed"},
        {"source_system": "adi", "source_key": "1800013", "version_id": "v-adi", "match_method": "fetched_from_entry", "match_status": "confirmed"},
    ])
    _jsonl(parsed_dir / "adi_page.jsonl", [
        {"version_id": "v-a", "page_no": 2, "text_content": "the next page without a break.\n\nSincerely, EPA Region 6.", "status": "ok"},
        {"version_id": "v-a", "page_no": 1, "text_content": "Dear Mr. Smith,\n\nThe mill is subject to Subpart S because the sentence continues on", "status": "ok"},
        {"version_id": "v-b", "page_no": 1, "text_content": "Cement kiln determination.", "status": "ok"},
        {"version_id": "v-adi", "page_no": 1, "text_content": "ADI letter, must be ignored.", "status": "ok"},
    ])
    return parsed_dir, letters


class _Result:
    def __init__(self, rows):
        self.data = rows


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def execute(self):
        return _Result(self._rows)


class _Table:
    def __init__(self, store, name):
        self._store, self._name = store, name

    def upsert(self, rows, on_conflict=None):
        rows_list = rows if isinstance(rows, list) else [rows]
        self._store.setdefault(self._name, []).extend(dict(row) for row in rows_list)
        return _Query(list(rows_list))


class FakeClient:
    """supabase-py 의 .table(name).upsert(rows, on_conflict=...).execute() 모양."""

    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


def _match_rag_chunk(client: FakeClient, release_id: str) -> list[dict]:
    """match_rag_chunk 함수의 where 절과 같다: release_id 가 같고 embedded 인 것만."""
    return [r for r in client.store.get("rag_chunk", []) if r["release_id"] == release_id and r["index_status"] == "embedded"]


# ---------------------------------------------------------------------------
# 완료 기준 1: fixture 서한 2건(3페이지) → 청크마다 source_key·chunk_text, 페이지 경계에서 안 잘린다
# ---------------------------------------------------------------------------
def test_fixture_letters_give_chunks_with_source_key_and_text_not_cut_at_page_break(parsed):
    parsed_dir, letters = parsed
    pages = letter_pages(parsed_dir, letters)

    assert set(pages) == {"aaaa", "bbbb"}  # pdf_url 없는 cccc, ADI 1800013 은 없다
    assert pages["aaaa"] == [
        "Dear Mr. Smith,\n\nThe mill is subject to Subpart S because the sentence continues on",
        "the next page without a break.\n\nSincerely, EPA Region 6.",
    ]  # page_no 순서

    chunks = [c for key in pages for c in build_letter_chunks(key, pages[key])]

    assert chunks and all(c["source_key"] and c["chunk_text"].strip() for c in chunks)
    joined = " ".join(c["chunk_text"] for c in chunks if c["source_key"] == "aaaa")
    assert "continues on the next page without a break." in joined  # 1쪽 끝 + 2쪽 첫 줄이 한 문장으로
    assert any(c["chunk_text"] == "Cement kiln determination." for c in chunks if c["source_key"] == "bbbb")


def test_long_letter_splits_into_paragraph_chunks_no_bigger_than_max():
    paragraphs = [f"Paragraph {i}. " + "word " * 200 for i in range(12)]  # 문단 하나 ≈ 1,000자
    pages = ["\n\n".join(paragraphs[:6]), "\n\n".join(paragraphs[6:])]

    chunks = build_letter_chunks("aaaa", pages)

    assert len(chunks) > 1
    assert all(len(c["chunk_text"]) <= MAX_CHUNK_CHARS for c in chunks)
    assert [c["chunk_key"] for c in chunks] == [f"dashboard/aaaa/{i}" for i in range(len(chunks))]
    assert "".join(c["chunk_text"] for c in chunks).replace("\n", "") == "".join(pages).replace("\n", "")  # 글자 유실 없음


# ---------------------------------------------------------------------------
# 완료 기준 2: 실제 자료 실행 시 서한 128건 전부 청크 1개 이상 (parsed 폴더 없으면 skip)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not REAL_PARSED.exists(), reason="2026-09-22 parsed 자료는 레포에 없다(로컬 전용)")
def test_real_2026_09_22_data_every_one_of_128_letters_has_a_chunk():
    pages = letter_pages(REAL_PARSED, REAL_LETTERS)

    assert len(pages) == 128
    assert all(len(build_letter_chunks(key, texts)) >= 1 for key, texts in pages.items())


# ---------------------------------------------------------------------------
# 완료 기준 3: 기존 eCFR release_id 로 match_rag_chunk 를 부르면 서한 청크가 0건
# ---------------------------------------------------------------------------
def test_letter_chunks_land_in_adi_release_and_are_invisible_to_ecfr_release(parsed):
    parsed_dir, letters = parsed
    client = FakeClient()
    pages = letter_pages(parsed_dir, letters)
    for key, texts in pages.items():
        for chunk in build_letter_chunks(key, texts):
            index_letter_chunk(chunk, client=client, call_kanon2=lambda request: EMBEDDING)

    rows = client.store["rag_chunk"]
    assert rows and all(r["release_id"] == LETTER_RELEASE_ID for r in rows)
    assert all(r["dataset"] == "adi" and r["doc_key"] in {"aaaa", "bbbb"} for r in rows)  # doc_key = source_key
    assert {r["chunk_key"] for r in rows} == {c["chunk_key"] for k, t in pages.items() for c in build_letter_chunks(k, t)}
    assert all(r["embedding"] == EMBEDDING and r["index_status"] == "embedded" for r in rows)
    assert LETTER_RELEASE_ID != ECFR_RELEASE_ID
    assert _match_rag_chunk(client, ECFR_RELEASE_ID) == []
    assert len(_match_rag_chunk(client, LETTER_RELEASE_ID)) == len(rows)


@pytest.mark.skipif(not os.environ.get("SUPABASE_DB_URL"), reason="실제 DB가 있을 때만")
def test_real_db_ecfr_release_has_no_dashboard_chunks():
    import psycopg

    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        ecfr = conn.execute(
            "select count(*) from rag_chunk where release_id = %s and chunk_key like 'dashboard/%%'", (ECFR_RELEASE_ID,)
        ).fetchone()[0]
    assert ecfr == 0
