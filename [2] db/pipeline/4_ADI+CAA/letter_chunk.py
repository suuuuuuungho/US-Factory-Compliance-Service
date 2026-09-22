"""SUU-256: Dashboard 판정서한 128건 → 문단 청크 → Kanon 2 임베딩 → rag_chunk 적재.

입력은 로컬 parsed/{as_of}/ jsonl 과 decision-letters.json(SUU-252). 서한 한 통의 페이지를 이어붙인 뒤
문단 단위로 자르므로 페이지 넘어가는 문장이 끊기지 않는다. release_id 는 기존 adi release 라
eCFR 색인(match_rag_chunk 의 p_release_id)에는 절대 섞이지 않는다. LLM 컨텍스트는 안 만든다.

실행: python letter_chunk.py --parsed "[2] db/4) ADI+CAA/parsed/2026-09-22" [--limit N]
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "5_rag"))
from ecfr_chunk_index import call_kanon2_api  # noqa: E402
from ecfr_embed import build_embedding_request

LETTER_RELEASE_ID = "5cc370d0-c513-4376-981f-2d910b39ae6b"  # common_dataset_release dataset=adi
ECFR_RELEASE_ID = "0c2efcae-99ed-41ae-85b6-1af8c8fbc44c"  # 현재 eCFR 색인. 테스트 비교용
MAX_CHUNK_CHARS = 3000
EMBED_MODEL = "kanon-2-embedder"
EMBED_DIMS = 1792
DEFAULT_LETTERS = Path(__file__).resolve().parents[3] / "[4]frontend" / "public" / "decision-letters.json"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_letters(letters_json: Path) -> list[dict]:
    """decision-letters.json 에서 pdf_url 있는 서한만."""
    return [l for l in json.loads(Path(letters_json).read_text(encoding="utf-8"))["letters"] if l.get("pdf_url")]


def letter_pages(parsed_dir: Path, letters_json: Path) -> dict[str, list[str]]:
    """source_key → 페이지 텍스트 목록(page_no 순). pdf_url 없는 서한·ADI 서한·페이지 없는 서한은 뺀다."""
    parsed_dir = Path(parsed_dir)
    wanted = {l["source_key"] for l in load_letters(letters_json)}
    version_of = {
        row["source_key"]: row["version_id"]
        for row in _jsonl(parsed_dir / "adi_entry_document.jsonl")
        if row["source_system"] == "caa_dashboard" and row["source_key"] in wanted
    }
    pages_of: dict[str, list[dict]] = {}
    for row in _jsonl(parsed_dir / "adi_page.jsonl"):
        if row["status"] == "ok":
            pages_of.setdefault(row["version_id"], []).append(row)

    result = {}
    for source_key, version_id in version_of.items():
        pages = sorted(pages_of.get(version_id, []), key=lambda r: r["page_no"])
        if pages:
            result[source_key] = [p["text_content"] for p in pages]
    return result


def build_letter_chunks(source_key: str, pages: list[str], *, max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    """페이지를 "\n" 으로 이어붙이고 문단("\n\n") 단위로 max_chars 이하씩 담는다.

    pypdf 본문은 빈 줄이 거의 없어 문단 하나가 max_chars 를 넘기 일쑤다. 그런 문단은 줄("\n") 단위로 다시 담는다.
    줄 하나가 max_chars 를 넘으면 그 줄 하나가 청크 하나다(글자를 버리지 않는다).
    """
    text = "\n".join(pages)
    page_starts = []  # 각 페이지가 text 에서 시작하는 위치
    offset = 0
    for page in pages:
        page_starts.append(offset)
        offset += len(page) + 1

    pieces = []  # (text, 앞에 붙는 구분자, page_from, page_to)
    cursor = 0
    for paragraph in text.split("\n\n"):
        if paragraph.strip():
            parts = [(paragraph, "\n\n")] if len(paragraph) <= max_chars else [
                (line, "\n") for line in paragraph.split("\n") if line.strip()
            ]
            start = cursor
            for part, sep in parts:
                start = text.index(part, start)
                page_from = bisect.bisect_right(page_starts, start)
                page_to = bisect.bisect_right(page_starts, start + len(part) - 1)
                pieces.append((part, sep, page_from, page_to))
                start += len(part)
        cursor += len(paragraph) + 2

    chunks: list[dict] = []
    current: list[tuple[str, str, int, int]] = []

    def joined(items) -> str:
        return "".join(p[0] if i == 0 else p[1] + p[0] for i, p in enumerate(items))

    def flush() -> None:
        chunks.append({
            "chunk_key": f"dashboard/{source_key}/{len(chunks)}",
            "source_key": source_key,
            "chunk_text": joined(current),
            "page_from": current[0][2],
            "page_to": current[-1][3],
        })

    for piece in pieces:
        if current and len(joined(current + [piece])) > max_chars:
            flush()
            current = []
        current.append(piece)
    if current:
        flush()
    return chunks


def index_letter_chunk(
    chunk: dict[str, Any],
    *,
    client: Any,
    call_kanon2: Callable[[dict[str, Any]], list[float]] = call_kanon2_api,
) -> None:
    """청크 하나를 임베딩해 rag_chunk 에 upsert 한다."""
    chunk_text = chunk["chunk_text"]
    context_text = chunk.get("context_text")
    embedding = call_kanon2(build_embedding_request(context_text or "", chunk_text) if context_text
                            else {"texts": [chunk_text], "task": "retrieval/document", "overflow_strategy": None})
    row = {
        "release_id": LETTER_RELEASE_ID,
        "chunk_key": chunk["chunk_key"],
        "dataset": "adi",
        "doc_key": chunk["source_key"],
        "node_key": chunk["source_key"],
        "block_from": chunk["page_from"],
        "block_to": chunk["page_to"],
        "source_locator": chunk.get("pdf_url"),
        "chunk_text": chunk_text,
        "context_text": context_text,
        "content_hash": hashlib.sha256(f"{chunk_text}\n\n{context_text or ''}".encode("utf-8")).hexdigest(),
        "embed_model": EMBED_MODEL,
        "embed_dims": EMBED_DIMS,
        "embedding": embedding,
        "index_status": "embedded",
    }
    client.table("rag_chunk").upsert([row], on_conflict="release_id,chunk_key").execute()


def _context_line(letter: dict) -> str:
    subparts = ", ".join(letter.get("subparts") or []) or "unknown"
    return f"EPA applicability determination letter: {letter['title']} — {letter['facility_name']} (40 CFR Part 63 Subpart {subparts})"


def _existing_chunk_keys(client: Any) -> set[str]:
    keys, start, page = set(), 0, 1000
    while True:
        rows = (client.table("rag_chunk").select("chunk_key").eq("release_id", LETTER_RELEASE_ID)
                .range(start, start + page - 1).execute().data)
        keys.update(r["chunk_key"] for r in rows)
        if len(rows) < page:
            return keys
        start += page


def main() -> None:
    parser = argparse.ArgumentParser(description="Dashboard 판정서한 → 청크 → Kanon 2 → rag_chunk")
    parser.add_argument("--parsed", required=True, help="adi_entry_document.jsonl·adi_page.jsonl 이 있는 parsed/<날짜> 폴더")
    parser.add_argument("--letters", default=str(DEFAULT_LETTERS), help="decision-letters.json 경로")
    parser.add_argument("--limit", type=int, default=None, help="시범용: 앞에서 N통만")
    args = parser.parse_args()

    from supabase import create_client

    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    letters = {l["source_key"]: l for l in load_letters(Path(args.letters))}
    pages = letter_pages(Path(args.parsed), Path(args.letters))
    existing = _existing_chunk_keys(client)

    done = skipped = failed = 0
    for source_key in list(pages)[: args.limit]:
        letter = letters[source_key]
        for chunk in build_letter_chunks(source_key, pages[source_key]):
            if chunk["chunk_key"] in existing:
                skipped += 1
                continue
            chunk["context_text"] = _context_line(letter)
            chunk["pdf_url"] = letter["pdf_url"]
            try:
                index_letter_chunk(chunk, client=client)
                done += 1
            except Exception as error:  # 한 청크 실패로 전체를 멈추지 않는다
                failed += 1
                print(f"failed {chunk['chunk_key']}: {error}")
    print(f"letters={len(pages)} embedded={done} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()


__all__ = [
    "ECFR_RELEASE_ID", "LETTER_RELEASE_ID", "MAX_CHUNK_CHARS",
    "build_letter_chunks", "index_letter_chunk", "letter_pages", "load_letters",
]
