"""Build the sourced numbers used by the About page from current DB releases."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "[4]frontend" / "public"
OUT = PUBLIC / "about-stats.json"
YEARS = range(2018, 2026)


def database_url() -> str:
    if os.environ.get("SUPABASE_DB_URL"):
        return os.environ["SUPABASE_DB_URL"]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("SUPABASE_DB_URL="):
            return line.partition("=")[2].strip().strip('"\'')
    raise RuntimeError("SUPABASE_DB_URL is missing from the environment and root .env")


def current_release(conn: psycopg.Connection, dataset: str, scope_key: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "select release_id from common_dataset_current where dataset = %s and scope_key = %s",
            (dataset, scope_key),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"No current release for {dataset}/{scope_key}")
    return str(row[0])


def rule_years(conn: psycopg.Connection, release_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """select extract(year from publication_date)::int, count(*)
               from fr_document
               where release_id = %s and type_raw = 'Rule' and scope_status = 'part63_list'
                 and publication_date >= date '2018-01-01'
                 and publication_date < date '2026-01-01'
               group by 1 order by 1""",
            (release_id,),
        )
        counts = dict(cur.fetchall())
    data = [{"year": year, "count": counts.get(year, 0)} for year in YEARS]
    if sum(row["count"] for row in data) != 136:
        raise RuntimeError("Current FR release rule count is not 136; refusing to write JSON")
    return data


def letter_years(conn: psycopg.Connection, release_id: str) -> tuple[list[dict], int, int]:
    dashboard = json.loads((PUBLIC / "decision-letters.json").read_text(encoding="utf-8"))["letters"]
    dashboard_dates = {row["source_key"]: datetime.fromisoformat(row["date"]).year for row in dashboard}
    if len(dashboard_dates) != 132 or len(dashboard) != 132:
        raise RuntimeError("Decision letter export does not contain 132 distinct Dashboard entries")
    with conn.cursor() as cur:
        cur.execute(
            """select e.source_system, e.source_key, e.letter_date_raw
               from adi_source_entry e
               where e.release_id = %s and e.scope_status = 'part63_candidate'
               """,
            (release_id,),
        )
        rows = cur.fetchall()
    counts: Counter[int] = Counter()
    unknown = 0
    seen_dashboard: set[str] = set()
    for system, source_key, raw_date in rows:
        if system == "adi":
            if not raw_date or raw_date == "12/30/1899":
                unknown += 1
                continue
            year = datetime.strptime(raw_date, "%m/%d/%Y").year
        elif system == "caa_dashboard":
            if source_key not in dashboard_dates or source_key in seen_dashboard:
                raise RuntimeError(f"Missing or duplicate Dashboard date for {source_key}")
            seen_dashboard.add(source_key)
            year = dashboard_dates[source_key]
        else:
            raise RuntimeError(f"Unexpected ADI source system: {system}")
        counts[year] += 1
    if seen_dashboard != set(dashboard_dates):
        raise RuntimeError(
            f"Dashboard export and current ADI release do not match: "
            f"DB={len(seen_dashboard)}, export={len(dashboard_dates)}, "
            f"missing={len(dashboard_dates.keys() - seen_dashboard)}"
        )
    before_1993 = sum(count for year, count in counts.items() if year < 1993)
    data = [{"year": year, "count": counts[year]} for year in range(1993, 2026)]
    if sum(counts.values()) + unknown != 1127:
        raise RuntimeError("Current ADI release letter count is not 1127; refusing to write JSON")
    if sum(row["count"] for row in data) + before_1993 + unknown != 1127:
        raise RuntimeError("Letter years fall outside 1993–2025")
    return data, before_1993, unknown


def build_stats(rules: list[dict], letters: list[dict], before_1993: int, unknown: int, echo: dict) -> dict:
    stats = {}

    def add(key: str, value: int | float, unit: str, source: str) -> None:
        stats[key] = {"value": value, "unit": unit, "source": source}

    fixed = {
        "part63_pages": (957, "pages", "1_project.md (40 CFR Part 63 PDF)"),
        "part63_words": (3300000, "words", "1_project.md"),
        "part63_tokens_min": (4000000, "tokens", "1_project.md"),
        "part63_tokens_max": (5000000, "tokens", "1_project.md"),
        "llm_context_tokens": (1000000, "tokens", "1_project.md"),
        "rule_changes": (136, "rules", "DB fr_document (current FR release, 2018–2025)"),
        "sections_changed": (1126, "sections", "1_project.md"),
        "sections_changed_pct": (45, "%", "1_project.md"),
        "epa_median_days": (138, "days", "1_project.md (Part 63 판정서한 n=235)"),
        "epa_over_6mo_pct": (40, "%", "1_project.md (n=235)"),
        "epa_letters_sample": (235, "letters", "1_project.md"),
        "letters_total": (1127, "letters", "DB adi_source_entry (ADI 995 + CAA Dashboard 132)"),
        "prison_years": (2, "years", "CAA §113(c)(2), 42 U.S.C. 7413(c)(2)"),
        "rag_chunks": (5625, "chunks", "3_rag 검색 품질 개선 과정.md"),
        "rag_eval_cases": (102, "cases", "3_rag 검색 품질 개선 과정.md (평가셋 v2)"),
        "rag_hit20_pct": (96.1, "%", "3_rag §4, hybrid+규칙+LLM Hit@20 0.961"),
        "rag_subpart_pct": (96.1, "%", "4_rag §5, 상위 10 Subpart 적중 0.961 (SUU-152)"),
        "rag_citation_grounded_pct": (99.6, "%", "4_rag §5, 인용 근거율 0.996 (SUU-152)"),
    }
    for key, (value, unit, source) in fixed.items():
        add(key, value, unit, source)

    summary = echo["summary"]
    for key, echo_key, unit in (
        ("violation_pct", "violation_facility_pct", "%"),
        ("facilities", "facilities", "facilities"),
        ("penalty_total_usd", "penalty_total_usd", "USD"),
        ("penalty_max_usd", "penalty_max_usd", "USD"),
    ):
        add(key, summary[echo_key], unit, "echo-stats.json (ECHO, 2015~)")

    subparts = sorted(echo["subparts"], key=lambda row: (-row["penalty_total_usd"], row["code"]))[:10]
    series = {
        "rule_changes_by_year": {"data": rules, "source": "DB fr_document (current FR release, Rule / part63_list)"},
        "letters_by_year": {"data": letters, "before_1993": before_1993, "unknown": unknown, "source": "DB adi_source_entry; CAA dates from decision-letters.json by source_key (current ADI release)"},
        "penalty_by_subpart": {
            "data": [{key: row[key] for key in ("code", "desc", "penalty_total_usd")} for row in subparts],
            "source": "echo-stats.json subparts (ECHO, 2015~)",
        },
        "rag_ndcg_steps": {
            "data": [
                {"step": "baseline", "ndcg": 0.264},
                {"step": "Kanon 2 + context", "ndcg": 0.437},
                {"step": "reranker", "ndcg": 0.561},
                {"step": "rules", "ndcg": 0.631},
                {"step": "LLM rerank", "ndcg": 0.692},
            ],
            "source": "3_rag 검색 품질 개선 과정.md §4",
        },
        "rag_funnel": {
            "data": [
                {"stage": "chunks", "count": 5625},
                {"stage": "candidates", "count": 150},
                {"stage": "reranked", "count": 20},
                {"stage": "sent to model", "count": 10},
            ],
            "source": "3_rag 검색 품질 개선 과정.md §6; 4_rag SUU-152",
        },
    }
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "stats": stats, "series": series}


def main() -> None:
    echo = json.loads((PUBLIC / "echo-stats.json").read_text(encoding="utf-8"))
    with psycopg.connect(database_url(), sslmode="require") as conn:
        fr_release = current_release(conn, "fr", "part63_metadata")
        adi_release = current_release(conn, "adi", "adi+caa_dashboard")
        rules = rule_years(conn, fr_release)
        letters, before_1993, unknown = letter_years(conn, adi_release)
    result = build_stats(rules, letters, before_1993, unknown, echo)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} (FR {fr_release}, ADI {adi_release})")


if __name__ == "__main__":
    main()
