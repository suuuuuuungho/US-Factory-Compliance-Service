"""SUU-236: 현재 ECHO release를 세어 대시보드용 echo-stats.json(summary·subparts·yearly)을 만든다.

SUU-242: 벌금 총액(penalty_total_usd)·최대 1건(penalty_max_usd)도 같이 센다.
SUU-246: yearly 에 그 해 벌금 총액(penalty_usd), 주(state)별 통계, 벌금 크기 구간(penalty_buckets) 추가.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

from echo_release import DATASET, SCOPE_KEY

PENALTY_SINCE = date(2015, 1, 1)
# 벌금 1건 크기 구간 (상한 미포함). 마지막은 $1M 이상
PENALTY_BUCKETS = [("<$1K", 1_000), ("$1K–10K", 10_000), ("$10K–100K", 100_000), ("$100K–1M", 1_000_000), ("$1M+", None)]
YEARLY_FROM = 2000
DEFAULT_OUT = Path(__file__).resolve().parents[3] / "[4]frontend" / "public" / "echo-stats.json"

_QUERIES = {
    "echo_facility": "select pgm_sys_id, state from echo_facility where release_id = %s",
    "echo_industry": "select pgm_sys_id, code_system, code from echo_industry where release_id = %s",
    "echo_program_subpart": "select pgm_sys_id, cfr_subpart, subpart_desc, cfr_part, mapping_status"
                            " from echo_program_subpart where release_id = %s",
    "echo_violation": "select violation_id, first_frv_date from echo_violation where release_id = %s",
    "echo_violation_facility": "select violation_id, pgm_sys_id from echo_violation_facility where release_id = %s",
    "echo_activity": "select activity_kind, activity_id, activity_date, attributes from echo_activity"
                     " where release_id = %s and activity_kind in ('titlev', 'formal')",
    "echo_activity_facility": "select activity_kind, activity_id, pgm_sys_id from echo_activity_facility"
                              " where release_id = %s and activity_kind in ('titlev', 'formal')",
    "echo_penalty": "select penalty_key, activity_kind, activity_id, amount from echo_penalty where release_id = %s",
}


def current_release_id(conn: Any) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "select release_id from common_dataset_current where dataset = %s and scope_key = %s",
            (DATASET, SCOPE_KEY),
        )
        row = cur.fetchone()
    if row is None:
        raise LookupError(f"no current release for {DATASET}/{SCOPE_KEY}")
    return str(row[0])


def fetch_rows(conn: Any, release_id: str) -> dict[str, list[dict]]:
    from psycopg.rows import dict_row

    rows: dict[str, list[dict]] = {}
    with conn.cursor(row_factory=dict_row) as cur:
        for table, sql in _QUERIES.items():
            cur.execute(sql, (release_id,))
            rows[table] = cur.fetchall()
    return rows


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _number(value):
    return int(value) if value == int(value) else float(value)


def _stats_for(
    facilities: set[str],
    mfg: set[str],
    violated: set[str],
    penalties: dict[tuple, tuple[Any, set[str]]],
    certs: list[tuple[str, set[str]]],
) -> dict:
    amounts = [
        amount for (_, _, day), (amount, linked) in penalties.items()
        if day is not None and day >= PENALTY_SINCE and linked & facilities
    ]
    linked_certs = [flag for flag, linked in certs if linked & facilities]
    return {
        "facilities": len(facilities),
        "mfg_facilities": len(facilities & mfg),
        "violation_facility_pct": _pct(len(facilities & violated), len(facilities)),
        "penalty_count": len(amounts),
        "penalty_median_usd": _number(median(amounts)) if amounts else None,
        "penalty_total_usd": _number(sum(amounts)) if amounts else 0,
        "penalty_max_usd": _number(max(amounts)) if amounts else None,
        "deviation_y_pct": _pct(sum(flag == "Y" for flag in linked_certs), len(linked_certs)),
    }


def compute_stats(rows: dict[str, list[dict]]) -> dict:
    part63 = [r for r in rows["echo_program_subpart"] if r["cfr_part"] == "63" and r["mapping_status"] == "mapped"]
    facilities = {r["pgm_sys_id"] for r in part63}
    by_subpart: dict[str, set[str]] = defaultdict(set)
    descs: dict[str, Counter] = defaultdict(Counter)
    for r in part63:
        by_subpart[r["cfr_subpart"]].add(r["pgm_sys_id"])  # 원본 subpart_code(CAAMACTZZZZ)가 아니라 CFR 글자(ZZZZ)로 묶는다
        descs[r["cfr_subpart"]][r["subpart_desc"]] += 1

    mfg = {
        r["pgm_sys_id"] for r in rows["echo_industry"]
        if r["code_system"] == "NAICS" and (r["code"] or "")[:2] in ("31", "32", "33")
    }
    violated = {r["pgm_sys_id"] for r in rows["echo_violation_facility"]}

    links: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows["echo_activity_facility"]:
        links[(r["activity_kind"], r["activity_id"])].add(r["pgm_sys_id"])
    activity_date = {(r["activity_kind"], r["activity_id"]): r["activity_date"] for r in rows["echo_activity"]}

    # 처분 하나 = 1건. 같은 처분의 echo_penalty 행이 여러 개여도 (kind, id)로 묶고 금액은 max
    penalties: dict[tuple, tuple[Any, set[str]]] = {}
    for r in rows["echo_penalty"]:
        if r["amount"] is None or r["amount"] <= 0:
            continue
        key = (r["activity_kind"], r["activity_id"])
        full_key = key + (activity_date.get(key),)
        prev = penalties.get(full_key)
        amount = r["amount"] if prev is None else max(prev[0], r["amount"])
        penalties[full_key] = (amount, links.get(key, set()))

    certs = [
        ((r["attributes"] or {}).get("FACILITY_RPT_DEVIATION_FLAG"), links.get((r["activity_kind"], r["activity_id"]), set()))
        for r in rows["echo_activity"] if r["activity_kind"] == "titlev"
    ]

    summary = _stats_for(facilities, mfg, violated, penalties, certs)
    subparts = [
        {"code": code, "desc": descs[code].most_common(1)[0][0], **_stats_for(members, mfg, violated, penalties, certs)}
        for code, members in by_subpart.items()
    ]
    subparts.sort(key=lambda s: (-s["facilities"], s["code"]))

    violation_year = {r["violation_id"]: r["first_frv_date"] for r in rows["echo_violation"] if r["first_frv_date"]}
    violations = Counter(
        violation_year[v].year for v in {
            r["violation_id"] for r in rows["echo_violation_facility"] if r["pgm_sys_id"] in facilities
        } if v in violation_year
    )
    penalty_years = Counter(
        day.year for (_, _, day), (_, linked) in penalties.items() if day is not None and linked & facilities
    )
    penalty_usd_years: Counter = Counter()
    for (_, _, day), (amount, linked) in penalties.items():
        if day is not None and linked & facilities:
            penalty_usd_years[day.year] += amount
    years = [y for y in violations | penalty_years if y >= YEARLY_FROM]
    yearly = [
        {"year": y, "violations": violations.get(y, 0), "penalties": penalty_years.get(y, 0),
         "penalty_usd": _number(penalty_usd_years.get(y, 0))}
        for y in range(YEARLY_FROM, max(years) + 1)
    ] if years else []

    # 주별: 시설의 state 로 묶어 같은 통계. 벌금 총액 큰 순
    state_of = {r["pgm_sys_id"]: r.get("state") for r in rows["echo_facility"]}
    by_state: dict[str, set[str]] = defaultdict(set)
    for f in facilities:
        if state_of.get(f):
            by_state[state_of[f]].add(f)
    states = [{"state": st, **_stats_for(members, mfg, violated, penalties, certs)} for st, members in by_state.items()]
    states.sort(key=lambda s: (-s["penalty_total_usd"], s["state"]))

    # 벌금 1건 크기 구간 (summary 와 같은 2015~ 처분)
    amounts = [
        amount for (_, _, day), (amount, linked) in penalties.items()
        if day is not None and day >= PENALTY_SINCE and linked & facilities
    ]
    penalty_buckets = []
    lower = 0
    for label, upper in PENALTY_BUCKETS:
        count = sum(1 for a in amounts if a >= lower and (upper is None or a < upper))
        penalty_buckets.append({"bucket": label, "count": count})
        lower = upper or lower

    return {"summary": summary, "subparts": subparts, "yearly": yearly, "states": states, "penalty_buckets": penalty_buckets}


def write_stats(stats: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import psycopg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        release_id = current_release_id(conn)
        stats = compute_stats(fetch_rows(conn, release_id))
    write_stats(stats, args.out)
    print(f"release {release_id}: facilities={stats['summary']['facilities']} subparts={len(stats['subparts'])} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["compute_stats", "current_release_id", "fetch_rows", "main", "write_stats"]
