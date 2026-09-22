"""SUU-228: Rule 문서가 고친 섹션의 eCFR 전날/시행일 본문을 문단 단위로 비교해 바뀐 것만 남긴다.

네트워크 없음. eCFR 섹션 XML은 fetch 함수를 주입해 흉내 낸다.
"""
import json

from fr_diff import amended_sections, build, diff_blocks, section_blocks

BEFORE = b"""<DIV8 N="63.2233" TYPE="SECTION">
<HEAD>\xc2\xa7 63.2233 When do I have to comply?</HEAD>
<P>(a) Keep this paragraph.</P>
<P>(b) Reports are due quarterly.</P>
<P>(c) This one goes away.</P>
<P>(d) Also unchanged.</P>
<CITA TYPE="N">[69 FR 46011, July 30, 2004]</CITA>
</DIV8>"""

AFTER = b"""<DIV8 N="63.2233" TYPE="SECTION">
<HEAD>\xc2\xa7 63.2233 When do I have to comply?</HEAD>
<P>(a) Keep this paragraph.</P>
<P>(b) Reports are due semiannually.</P>
<P>(d) Also unchanged.</P>
<P>(e) Brand new paragraph.</P>
<CITA TYPE="N">[69 FR 46011, July 30, 2004; 91 FR 41434, July 6, 2026]</CITA>
</DIV8>"""

FR_XML = b"""<RULE><REGTEXT PART="63" TITLE="40">
<AMDPAR>1. The authority citation for part 63 continues to read as follows:</AMDPAR>
<SECTION><SECTNO>\xc2\xa7 63.14 </SECTNO><SUBJECT>IBR</SUBJECT></SECTION>
<SECTION><SECTNO>\xc2\xa7 63.2233 </SECTNO><SUBJECT>Compliance</SUBJECT></SECTION>
<SECTION><SECTNO>\xc2\xa7 63.2233 </SECTNO><SUBJECT>dup is ignored</SUBJECT></SECTION>
</REGTEXT><REGTEXT PART="60" TITLE="40">
<SECTION><SECTNO>\xc2\xa7 60.1 </SECTNO></SECTION>
</REGTEXT></RULE>"""


def test_amended_sections_reads_part63_sectno_in_order_without_duplicates():
    assert amended_sections(FR_XML) == ["63.14", "63.2233"]


def test_section_blocks_drops_heading_and_citation():
    assert section_blocks(BEFORE) == [
        "(a) Keep this paragraph.",
        "(b) Reports are due quarterly.",
        "(c) This one goes away.",
        "(d) Also unchanged.",
    ]


def test_diff_blocks_keeps_only_changed_rows_plus_one_line_of_context():
    rows = diff_blocks(section_blocks(BEFORE), section_blocks(AFTER))
    kinds = [(r["kind"], r["is_context"]) for r in rows]
    assert kinds == [
        ("equal", True),      # (a) 맥락
        ("changed", False),   # (b) quarterly → semiannually
        ("removed", False),   # (c)
        ("equal", True),      # (d) 맥락
        ("added", False),     # (e)
    ]
    changed = rows[1]
    assert changed["before"] == "(b) Reports are due quarterly."
    assert changed["after"] == "(b) Reports are due semiannually."
    assert rows[2] == {"kind": "removed", "before": "(c) This one goes away.", "after": None, "is_context": False}
    assert rows[4] == {"kind": "added", "before": None, "after": "(e) Brand new paragraph.", "is_context": False}


def test_diff_blocks_identical_returns_nothing():
    assert diff_blocks(section_blocks(BEFORE), section_blocks(BEFORE)) == []


def _fr_root(tmp_path, xml: bytes | None):
    """fr_collect 가 남기는 모양: raw/{연도}/{발행일}_{번호}/manifest.json + 본문."""
    folder = tmp_path / "fr" / "raw" / "2026" / "2026-07-06_2026-13550"
    folder.mkdir(parents=True)
    manifest = []
    if xml is not None:
        (folder / "sha").mkdir()
        (folder / "sha" / "2026-13550.xml").write_bytes(xml)
        manifest.append({"kind": "xml", "path": "raw/2026/2026-07-06_2026-13550/sha/2026-13550.xml"})
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path / "fr"


def _parsed(tmp_path, *, effective: bool = True):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    docs = [
        {"document_key": "2026-07-06/2026-13550", "document_number": "2026-13550", "publication_date": "2026-07-06",
         "type_raw": "Rule", "title": "PCWP NESHAP", "citation": "91 FR 41434", "canonical_url": "https://x/1"},
        {"document_key": "2026-07-01/2026-1", "document_number": "2026-1", "publication_date": "2026-07-01",
         "type_raw": "Proposed Rule", "title": "ignored", "citation": None, "canonical_url": "https://x/2"},
        {"document_key": "2023-12-31/2023-9", "document_number": "2023-9", "publication_date": "2023-12-31",
         "type_raw": "Rule", "title": "too old", "citation": None, "canonical_url": "https://x/3"},
    ]
    (parsed / "fr_document.jsonl").write_text("".join(json.dumps(d) + "\n" for d in docs), encoding="utf-8")
    events = []
    if effective:
        events.append({"document_key": "2026-07-06/2026-13550", "event_kind": "effective", "event_date": "2026-07-06"})
    events.append({"document_key": "2026-07-06/2026-13550", "event_kind": "compliance", "event_date": "2029-07-06"})
    (parsed / "fr_date_event.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return parsed


def _nodes(tmp_path):
    path = tmp_path / "nodes.jsonl"
    rows = [{"node_key": "40/63/subpart-DDDD/section-63.2233", "node_type": "section", "identifier": "63.2233"},
            {"node_key": "40/63/subpart-A/section-63.14", "node_type": "section", "identifier": "63.14"}]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_build_fetches_day_before_and_effective_day_per_amended_section(tmp_path):
    calls = []

    def fake_fetch(as_of, section):
        calls.append((as_of, section))
        if section == "63.14":
            return None  # 63.14 는 두 날 다 없음(404) → 섹션 자체가 diff 에서 빠진다
        return BEFORE if as_of == "2026-07-05" else AFTER

    out = tmp_path / "fr-diff.json"
    build(_fr_root(tmp_path, FR_XML), _parsed(tmp_path), _nodes(tmp_path), out, since="2024-01-01", fetch=fake_fetch)

    assert sorted(calls) == [("2026-07-05", "63.14"), ("2026-07-05", "63.2233"), ("2026-07-06", "63.14"), ("2026-07-06", "63.2233")]
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [d["document_key"] for d in data["documents"]] == ["2026-07-06/2026-13550"]
    doc = data["documents"][0]
    assert doc["effective_date"] == "2026-07-06"
    assert doc["amended_sections"] == ["63.14", "63.2233"]
    assert doc["summary"] == {"added": 1, "removed": 1, "changed": 1}
    assert [s["section"] for s in doc["sections"]] == ["63.2233"]
    assert doc["sections"][0]["node_key"] == "40/63/subpart-DDDD/section-63.2233"
    assert len(doc["sections"][0]["rows"]) == 5


def test_build_marks_documents_without_effective_date_or_xml(tmp_path):
    out = tmp_path / "fr-diff.json"
    build(_fr_root(tmp_path, None), _parsed(tmp_path, effective=False), _nodes(tmp_path), out,
          since="2024-01-01", fetch=lambda *_: (_ for _ in ()).throw(AssertionError("no fetch")))
    doc = json.loads(out.read_text(encoding="utf-8"))["documents"][0]
    assert doc["sections"] == []
    assert doc["reason"] == "no_effective_date"
    assert doc["summary"] == {"added": 0, "removed": 0, "changed": 0}
