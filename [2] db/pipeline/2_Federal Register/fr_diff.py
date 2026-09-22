"""SUU-228: Rule 문서가 고친 섹션마다 eCFR 시행 전날/시행일 본문을 비교해 바뀐 문단만 JSON 으로 쓴다.

고친 섹션은 FR XML 의 <SECTNO> 에서, 전/후 본문은 eCFR 섹션 API 에서 가져온다.
바뀌지 않은 문단은 맥락용 앞뒤 1개만 남기고 버린다.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "1_eCFR"))
from ecfr_blocks import parse_blocks  # noqa: E402
from ecfr_fetch import fetch  # noqa: E402


_SECTNO = re.compile(r"§\s*63\.(\S+)")
_SKIP_KINDS = {"citation", "heading"}


def amended_sections(fr_xml: bytes) -> list[str]:
    """FR 본문 <SECTNO> 중 Part 63 섹션 번호를 순서대로, 중복 없이."""

    root = etree.fromstring(fr_xml)
    seen: list[str] = []
    for sectno in root.iter("SECTNO"):
        match = _SECTNO.search("".join(sectno.itertext()))
        if match and f"63.{match.group(1)}" not in seen:
            seen.append(f"63.{match.group(1)}")
    return seen


def section_blocks(section_xml: bytes) -> list[str]:
    """eCFR 섹션 XML(DIV8) → 문단 텍스트 목록. 제목·개정 이력(CITA)은 뺀다."""

    root = etree.fromstring(section_xml)
    div = root if root.tag == "DIV8" else root.find(".//DIV8")
    if div is None:
        return []
    return [b["text_content"] for b in parse_blocks(div) if b["kind"] not in _SKIP_KINDS and b["text_content"]]


def diff_blocks(before: list[str], after: list[str]) -> list[dict[str, Any]]:
    """문단 단위 diff. 바뀐 행 + 그 앞뒤 맥락 1행만. 완전히 같으면 []."""

    rows: list[dict[str, Any]] = []
    keep: set[int] = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                rows.append({"kind": "equal", "before": before[k], "after": before[k], "is_context": True})
            continue
        start = len(rows)
        if tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                rows.append({"kind": "changed", "before": before[i1 + k], "after": after[j1 + k], "is_context": False})
            i1, j1 = i1 + n, j1 + n
        for k in range(i1, i2):
            rows.append({"kind": "removed", "before": before[k], "after": None, "is_context": False})
        for k in range(j1, j2):
            rows.append({"kind": "added", "before": None, "after": after[k], "is_context": False})
        keep.update(range(start - 1, len(rows) + 1))
    return [r for i, r in enumerate(rows) if i in keep]


def fetch_section(as_of: str, section: str, cache_dir: Path | None = None) -> bytes | None:
    """eCFR 섹션 XML. 그 날짜에 섹션이 없으면(404) None. cache_dir 이 있으면 디스크에 남겨 재실행 때 건너뛴다."""

    path = cache_dir / as_of / f"{section}.xml" if cache_dir else None
    if path and path.exists():
        return path.read_bytes() or None          # 빈 파일 = 404 기록
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{as_of}/title-40.xml?section={section}"
    for attempt in range(5):
        try:
            body: bytes | None = fetch(url).body
            break
        except HTTPError as error:
            if error.code == 404:
                body = None
                break
            if error.code != 429 or attempt == 4:
                raise
            time.sleep(5 * 2 ** attempt)        # 429: 5·10·20·40초 쉬고 다시
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body or b"")
    return body


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _xml_path(fr_root: Path, document_key: str) -> Path | None:
    publication_date, document_number = document_key.split("/", 1)
    folder = fr_root / "raw" / publication_date[:4] / f"{publication_date}_{document_number}"
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return None
    for entry in reversed(json.loads(manifest_path.read_text(encoding="utf-8"))):
        if entry.get("kind") == "xml":
            return fr_root / entry["path"]
    return None


def build(fr_root: Path, parsed: Path, ecfr_nodes: Path, out: Path, *, since: str,
          fetch: Callable[[str, str], bytes | None] = fetch_section) -> dict[str, Any]:
    """since 이후 게재된 Rule 문서마다 섹션별 diff 를 만들어 out 에 JSON 으로 쓴다."""

    fr_root, parsed = Path(fr_root), Path(parsed)
    node_keys = {n["identifier"]: n["node_key"] for n in _read_jsonl(Path(ecfr_nodes)) if n.get("node_type") == "section"}
    effective: dict[str, str] = {}
    for event in _read_jsonl(parsed / "fr_date_event.jsonl"):
        if event["event_kind"] == "effective":
            effective.setdefault(event["document_key"], event["event_date"])

    documents: list[dict[str, Any]] = []
    todo: list[tuple[dict[str, Any], str, str]] = []   # (doc, before_date, after_date)
    for row in _read_jsonl(parsed / "fr_document.jsonl"):
        if row["type_raw"] != "Rule" or row["publication_date"] < since:
            continue
        key = row["document_key"]
        doc: dict[str, Any] = {
            "document_key": key, "document_number": row["document_number"], "title": row["title"],
            "citation": row.get("citation"), "canonical_url": row["canonical_url"],
            "publication_date": row["publication_date"], "effective_date": effective.get(key),
            "amended_sections": [], "sections": [], "reason": None,
            "summary": {"added": 0, "removed": 0, "changed": 0},
        }
        documents.append(doc)
        xml_path = _xml_path(fr_root, key)
        if doc["effective_date"] is None:
            doc["reason"] = "no_effective_date"
            continue
        if xml_path is None:
            doc["reason"] = "no_xml"
            continue
        doc["amended_sections"] = amended_sections(xml_path.read_bytes())
        if not doc["amended_sections"]:
            doc["reason"] = "no_sectno"
            continue
        after_date = doc["effective_date"]
        todo.append((doc, (date.fromisoformat(after_date) - timedelta(days=1)).isoformat(), after_date))

    # 전/후 섹션 XML 을 한꺼번에 받는다 (eCFR 응답이 건당 ~2초라 4개 동시. 더 늘리면 429).
    pairs = sorted({(d, s) for doc, b, a in todo for d in (b, a) for s in doc["amended_sections"]})
    print(f"documents={len(documents)} fetches={len(pairs)}", file=sys.stderr, flush=True)
    cache: dict[tuple[str, str], bytes | None] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, (pair, body) in enumerate(zip(pairs, pool.map(lambda p: fetch(*p), pairs)), 1):
            cache[pair] = body
            if i % 50 == 0 or i == len(pairs):
                print(f"fetched {i}/{len(pairs)}", file=sys.stderr, flush=True)

    for doc, before_date, after_date in todo:
        for section in doc["amended_sections"]:
            before_xml, after_xml = cache[(before_date, section)], cache[(after_date, section)]
            if before_xml is None and after_xml is None:
                continue
            rows = diff_blocks(section_blocks(before_xml) if before_xml else [],
                               section_blocks(after_xml) if after_xml else [])
            if not rows:
                continue
            for r in rows:
                if r["kind"] in doc["summary"]:
                    doc["summary"][r["kind"]] += 1
            doc["sections"].append({
                "section": section, "node_key": node_keys.get(section),
                "before_date": before_date, "after_date": after_date, "rows": rows,
            })
        if not doc["sections"]:
            doc["reason"] = "no_text_change"

    documents.sort(key=lambda d: d["publication_date"], reverse=True)
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "since": since, "documents": documents}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fr-root", required=True, help="[2] db/2) Federal Register")
    parser.add_argument("--parsed", required=True, help="parsed/{as_of} 폴더 (fr_document·fr_date_event)")
    parser.add_argument("--ecfr-nodes", required=True, help="eCFR parsed nodes.jsonl (node_key 매핑)")
    parser.add_argument("--out", required=True, help="fr-diff.json 출력 경로")
    parser.add_argument("--since", default="2024-01-01")
    parser.add_argument("--cache", help="받은 eCFR 섹션 XML을 둘 폴더 (기본: {fr-root}/ecfr_sections)")
    args = parser.parse_args(argv)
    cache_dir = Path(args.cache) if args.cache else Path(args.fr_root) / "ecfr_sections"
    socket.setdefaulttimeout(30)
    result = build(args.fr_root, args.parsed, args.ecfr_nodes, args.out, since=args.since,
                   fetch=lambda as_of, section: fetch_section(as_of, section, cache_dir))
    docs = result["documents"]
    print(f"documents={len(docs)} with_diff={sum(1 for d in docs if d['sections'])} "
          f"reasons={ {d['reason'] for d in docs if d['reason']} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
