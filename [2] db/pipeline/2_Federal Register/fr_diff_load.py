"""SUU-230: fr-diff.json(SUU-228) 을 fr_diff 표에 COPY 로 넣는다."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

COLUMNS = ("release_id", "document_key", "section", "node_key", "seq", "change_kind",
           "before_text", "after_text", "is_context", "before_date", "after_date")


def diff_rows(data: dict[str, Any], release_id: str):
    """JSON 문서 → fr_diff 행 tuple. 섹션 없는 문서(reason 있음)는 행이 없다."""

    for doc in data["documents"]:
        for sec in doc["sections"]:
            for seq, row in enumerate(sec["rows"], 1):
                yield (release_id, doc["document_key"], sec["section"], sec["node_key"], seq, row["kind"],
                       row["before"], row["after"], row["is_context"], sec["before_date"], sec["after_date"])


def load_diff(json_path: Path, release_id: str, *, conn: Any) -> int:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    count = 0
    with conn.cursor() as cur:
        cur.execute("delete from fr_diff where release_id = %s", (release_id,))
        with cur.copy(f"COPY fr_diff ({', '.join(COLUMNS)}) FROM STDIN") as copy:
            for row in diff_rows(data, release_id):
                copy.write_row(row)
                count += 1
    conn.commit()
    return count


def main(argv: list[str] | None = None) -> int:
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, help="[4]frontend/public/fr-diff.json")
    parser.add_argument("--release-id", required=True, help="fr_document 가 들어 있는 release_id")
    args = parser.parse_args(argv)
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        print(f"fr_diff rows={load_diff(args.json, args.release_id, conn=conn)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
