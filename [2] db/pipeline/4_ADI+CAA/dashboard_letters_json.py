"""SUU-252: adi_source_entry.jsonl 에서 CAA Dashboard Part 63 후보 행만 골라 decision-letters.json 을 만든다.

프론트(/decision-letter)가 읽는다. fr-diff.json 과 같은 정적 파일 방식.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_PART63 = re.compile(r"Part 63,\s*([A-Z]+):")


def part63_subparts(raw: str | None) -> list[str]:
    """'Part 60, BB: … ; Part 63, S: …' → ['S']. Part 63 이 아닌 조각은 버린다."""
    if not raw:
        return []
    return _PART63.findall(raw)


def build(entries_path: Path) -> dict:
    letters = []
    with entries_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["source_system"] != "caa_dashboard" or row["scope_status"] != "part63_candidate":
                continue
            letters.append(
                {
                    "source_key": row["source_key"],
                    "facility_name": row["facility_name"],
                    "title": row["title"],
                    "subparts": part63_subparts(row.get("affected_subpart_raw")),
                    "date": row.get("link_text"),
                    "pdf_url": row["canonical_url"] if row.get("text_status") == "ok" else None,
                }
            )
    return {"letters": letters}


def main() -> None:
    parser = argparse.ArgumentParser(description="CAA Dashboard Part 63 판정서한 → decision-letters.json")
    parser.add_argument("--parsed", required=True, help="adi_source_entry.jsonl 이 있는 parsed/<날짜> 폴더")
    parser.add_argument("--out", required=True, help="decision-letters.json 출력 경로")
    args = parser.parse_args()

    payload = build(Path(args.parsed) / "adi_source_entry.jsonl")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"letters={len(payload['letters'])} → {out}")


if __name__ == "__main__":
    main()
