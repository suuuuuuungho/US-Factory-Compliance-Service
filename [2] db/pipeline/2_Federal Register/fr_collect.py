"""Collect the Part 63 list and each document's detail, XML, and PDF."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

from fr_fetch import Fetched, FormatMismatch, check_format, detail_url, fetch as http_fetch
from fr_list import collect_list
from fr_raw import store_raw

fetch = http_fetch


def _manifest(root: Path, publication_date: str, document_number: str) -> list[dict]:
    path = root / "raw" / publication_date[:4] / f"{publication_date}_{document_number}" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _existing(root: Path, publication_date: str, document_number: str, kind: str, url: str) -> dict | None:
    return next((e for e in _manifest(root, publication_date, document_number)
                 if e["kind"] == kind and e["source_url"] == url), None)


def _as_fetched(value: bytes | Fetched, url: str) -> Fetched:
    if isinstance(value, Fetched):
        return value
    return Fetched(value, url, url, 200, "", len(value), hashlib.sha256(value).hexdigest())


def _reason(exc: Exception) -> str:
    return f"HTTP {exc.code}" if isinstance(exc, HTTPError) else str(exc)


def collect(root: Path, end_date: date, *, fetch=None, pause: float = 0.0, workers: int = 1) -> dict:
    """Collect raw files, retaining per-file failures for later retry."""

    del pause  # Reserved for production throttling without slowing test doubles.
    root = Path(root)
    fetch = fetch or globals()["fetch"]
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        listed = collect_list(root, end_date, fetch=fetch)
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "failed", "end_date": end_date.isoformat(), "reason": _reason(exc),
                "started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat()}

    obtained = {"detail": 0, "xml": 0, "pdf": 0}
    missing: list[dict] = []
    retries: list[dict] = []

    def one(row: dict) -> tuple[dict, list[dict], list[dict]]:
        obtained = {"detail": 0, "xml": 0, "pdf": 0}
        missing: list[dict] = []
        retries: list[dict] = []

        def fail(pub: str, number: str, kind: str, url: str, exc: Exception | None = None, reason: str | None = None) -> None:
            text = reason if reason is not None else _reason(exc)  # type: ignore[arg-type]
            item = {"publication_date": pub, "document_number": number, "kind": kind, "reason": text}
            missing.append(item)
            if url:
                retries.append({**item, "url": url})

        pub, number = row["publication_date"], row["document_number"]
        url = detail_url(number, pub)
        entry = _existing(root, pub, number, "detail", url)
        try:
            if entry:
                detail = json.loads((root / entry["path"]).read_bytes())
            else:
                fetched = _as_fetched(fetch(url), url)
                check_format(fetched.body, "json")
                store_raw(root, pub, number, fetched, kind="detail")
                detail = json.loads(fetched.body)
            obtained["detail"] += 1
        except (HTTPError, URLError, OSError, FormatMismatch, ValueError, json.JSONDecodeError) as exc:
            fail(pub, number, "detail", url, exc)
            return obtained, missing, retries

        for kind, key in (("xml", "full_text_xml_url"), ("pdf", "pdf_url")):
            content_url = detail.get(key)
            if not content_url:
                fail(pub, number, kind, "", reason="no url")
                continue
            if _existing(root, pub, number, kind, content_url):
                obtained[kind] += 1
                continue
            try:
                fetched = _as_fetched(fetch(content_url), content_url)
                check_format(fetched.body, kind)
                store_raw(root, pub, number, fetched, kind=kind)
                obtained[kind] += 1
            except (HTTPError, URLError, OSError, FormatMismatch, ValueError) as exc:
                fail(pub, number, kind, content_url, exc)
        return obtained, missing, retries

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(one, listed["rows"]))
    for got, miss, retry in results:
        for kind in obtained:
            obtained[kind] += got[kind]
        missing.extend(miss)
        retries.extend(retry)

    retry_path = root / "raw" / "lists" / end_date.isoformat() / "retry.jsonl"
    if retries:
        retry_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in retries), encoding="utf-8")
    elif retry_path.exists():
        retry_path.unlink()
    return {
        "status": "succeeded", "end_date": end_date.isoformat(), "pages": listed["pages"],
        "count": listed["count"], "documents": len(listed["rows"]), "obtained": obtained,
        "missing": missing, "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2] / "2) Federal Register")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    result = collect(args.root, args.end, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
