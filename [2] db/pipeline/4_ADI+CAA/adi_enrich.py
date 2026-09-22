"""Build ADI enrichment JSONL tables from parsed ADI documents."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from adi_blocks import split_blocks
from adi_facilities import build_facility_index, extract_facility_candidates
from adi_references import build_node_index, extract_references
from adi_relations import extract_relations


TABLES = ("adi_block", "adi_cfr_reference", "adi_document_relation", "adi_facility_candidate")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def enrich_all(root, as_of, *, ecfr_nodes, echo_facilities) -> dict:
    root, parsed = Path(root), Path(root) / "parsed" / as_of
    started_at = _now()
    versions = _read_jsonl(parsed / "adi_document_version.jsonl")
    pages = _read_jsonl(parsed / "adi_page.jsonl")
    entries = _read_jsonl(parsed / "adi_source_entry.jsonl")
    links = _read_jsonl(parsed / "adi_entry_document.jsonl")
    node_index = build_node_index(_read_jsonl(Path(ecfr_nodes)))
    facility_index = build_facility_index(_read_jsonl(Path(echo_facilities)))
    pages_by_version: dict[str, list[dict]] = {}
    for page in pages:
        pages_by_version.setdefault(page["version_id"], []).append(page)
    version_by_id = {row["version_id"]: row for row in versions}
    entry_by_key = {(row.get("source_system"), row.get("source_key")): row for row in entries}
    entries_by_version: dict[str, list[dict]] = {}
    control_to_document = {}
    for link in links:
        entry = entry_by_key.get((link.get("source_system"), link.get("source_key")))
        version = version_by_id.get(link.get("version_id"))
        if entry:
            entries_by_version.setdefault(link["version_id"], []).append(entry)
        if entry and version and entry.get("control_number"):
            control_to_document[entry["control_number"]] = version["document_id"]
    rows = {table: [] for table in TABLES}
    without_text = 0
    relation_mentions_skipped = 0
    for version in versions:
        version_id = version["version_id"]
        if not version.get("text_content"):
            without_text += 1
            continue
        blocks = split_blocks(version_id, pages_by_version.get(version_id, []))
        rows["adi_block"].extend(blocks)
        rows["adi_cfr_reference"].extend(extract_references(version_id, blocks, node_index))
        relations = extract_relations(version_id, version["document_id"], blocks, control_to_document)
        rows["adi_document_relation"].extend(relations)
        # Count explicit relationship mentions whose control number has no fetched document.
        import re
        for block in blocks:
            # ADI headers put the relationship phrase and its control number on one line;
            # retain abbreviations such as "Control No." while counting it.
            for sentence in block["text_content"].splitlines():
                lower = sentence.lower()
                if any(word in lower for word in ("withdraw", "rescind", "supersed", "replace", "also filed", "also appears in", "also filed under")):
                    relation_mentions_skipped += sum(1 for control in re.findall(r"\b[A-Z]?\d{6,8}\b", sentence) if control not in control_to_document)
        names = [entry.get("facility_name") for entry in entries_by_version.get(version_id, [])]
        rows["adi_facility_candidate"].extend(extract_facility_candidates(version["document_id"], names, version["text_content"], facility_index))
    for table in TABLES:
        _write_jsonl(parsed / f"{table}.jsonl", rows[table])
    report = {
        "as_of": as_of, "status": "succeeded", "versions": len(versions), "versions_without_text": without_text,
        "rows": {table: len(rows[table]) for table in TABLES},
        "references_unresolved": sum(1 for row in rows["adi_cfr_reference"] if row["current_node_key"] is None),
        "relation_mentions_skipped": relation_mentions_skipped, "started_at": started_at, "finished_at": _now(),
    }
    (parsed / "enrich_report.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return report


def _latest(path: Path) -> Path:
    folders = [item for item in path.iterdir() if item.is_dir()]
    if not folders:
        raise ValueError(f"no folders in {path}")
    return max(folders, key=lambda item: item.name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2] / "4) ADI+CAA")
    parser.add_argument("--as-of")
    parser.add_argument("--ecfr-nodes", type=Path)
    parser.add_argument("--echo-facilities", type=Path)
    args = parser.parse_args(argv)
    as_of = args.as_of or _latest(args.root / "parsed").name
    ecfr = args.ecfr_nodes or (_latest(Path("[2] db") / "1) eCFR" / "parsed") / "v1" / "nodes.jsonl")
    echo = args.echo_facilities or (_latest(Path("[2] db") / "3) ECHO" / "parsed") / "echo_facility.jsonl")
    print(json.dumps(enrich_all(args.root, as_of, ecfr_nodes=ecfr, echo_facilities=echo), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
