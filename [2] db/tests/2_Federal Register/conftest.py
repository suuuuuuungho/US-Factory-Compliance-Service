"""SUU-209 테스트가 같이 쓰는 도우미: raw 3건 + parsed 산출물을 실제 SUU-206·207 코드로 만든다.

네트워크·DB 없음. 문서 3건 = fixtures/detail_*.json. 2003-08-28 정정문은 XML 없이 PDF만 둔다(pdf_only).
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from fr_fetch import Fetched, detail_url
from fr_parse import parse_all
from fr_raw import store_raw

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = "2026-09-21"
DOCS = [  # (발행일, 문서번호, xml 있음?)
    ("2003-05-27", "03-5521", True),
    ("2003-08-28", "03-5521", False),
    ("2026-02-24", "2026-03638", True),
]


def fetched(body: bytes, url: str) -> Fetched:
    return Fetched(body, url, url, 200, "", len(body), hashlib.sha256(body).hexdigest())


def xml_url(pub, num):
    return f"https://www.federalregister.gov/documents/full_text/xml/{pub.replace('-', '/')}/{num}.xml"


def pdf_url(pub, num):
    return f"https://www.govinfo.gov/content/pkg/FR-{pub}/pdf/{num}.pdf"


def put_document(root, pub, num, *, xml=True):
    """SUU-206 수집기가 남기는 모양 그대로. 반환: kind → (source_url, sha256)."""
    detail = (FIXTURES / f"detail_{pub}_{num}.json").read_bytes()
    out = {}
    for kind, body, url in (
        ("detail", detail, detail_url(num, pub)),
        ("xml", f"<RULE>{num} {pub}</RULE>".encode(), xml_url(pub, num)),
        ("pdf", f"%PDF-1.7 {num} {pub}".encode(), pdf_url(pub, num)),
    ):
        if kind == "xml" and not xml:
            continue
        f = fetched(body, url)
        store_raw(root, pub, num, f, kind=kind)
        out[kind] = (url, f.sha256)
    return out


def read_jsonl(root, table):
    return [json.loads(l) for l in (root / "parsed" / AS_OF / f"{table}.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def fr(tmp_path):
    """raw/ 에 문서 3건(원본 8개) + parsed/{AS_OF}/ 에 jsonl 4개·quality_report.json.

    fr.root, fr.as_of, fr.objects[(발행일, 번호)][kind] = (source_url, sha256), fr.rows(table), fr.put_document(...)
    """
    root = tmp_path / "fr"
    objects = {(pub, num): put_document(root, pub, num, xml=xml) for pub, num, xml in DOCS}
    parse_all(root, AS_OF)
    return SimpleNamespace(
        root=root, as_of=AS_OF, objects=objects, docs=DOCS,
        rows=lambda table: read_jsonl(root, table),
        put_document=lambda pub, num, **kw: put_document(root, pub, num, **kw),
        reparse=lambda: parse_all(root, AS_OF),
    )
