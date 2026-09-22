"""SUU-236: ECHO 표를 세어 대시보드용 echo-stats.json(summary·subparts·yearly)을 만든다.

실제 Postgres 없음. ``fetch_rows``가 DB에서 가져올 모양(표 이름 → dict 행 리스트)을 손으로 만든 fixture로
``compute_stats``를 부르고, 손으로 센 값과 같은지 본다. 실제 DB 검증은 SUPABASE_DB_URL이 있을 때만 돈다.
"""
from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal

import pytest

from echo_stats import compute_stats, current_release_id, fetch_rows, write_stats

# ── fixture: 시설 3(F1·F2·F3) · Part 63 Subpart 2(ZZZZ·DDDDD) · 위반 2(V1·V2) · 벌금 2(A1·A2, 금액>0) ──
#
# 시설      NAICS     Part 63 Subpart        위반        Title V 인증(deviation)   벌금(formal)
# F1       331110    ZZZZ, DDDDD            V1, V2      T1=Y                     A2 2019 $12,000
# F2       493110    ZZZZ                   -           T2=N                     A1 2014 $5,000 (2015 전 → summary 제외)
# F3       325199    DDDDD (+XXXX unmapped, +Part 60 Dc)   V2   T3=Y            A3 2020 $0 (금액 0 → 제외)
#
# 손으로 센 값
#   summary: facilities 3, mfg 2(F1·F3), violation_facility_pct 66.7(F1·F3), penalty_count 1(A2), median 12000, deviation_y_pct 66.7(T1·T3 / T1·T2·T3)
#   ZZZZ  (F1·F2): facilities 2, mfg 1, violation 50.0, penalty 1/12000, deviation 50.0
#   DDDDD (F1·F3): facilities 2, mfg 2, violation 100.0, penalty 1/12000, deviation 100.0
#   yearly: 2014 벌금 1 · 2016 위반 1 · 2019 벌금 1 · 2021 위반 1 (V2는 시설 2곳에 붙어도 1건)


def base_rows() -> dict[str, list[dict]]:
    return {
        "echo_facility": [{"pgm_sys_id": f} for f in ("F1", "F2", "F3")],
        "echo_industry": [
            {"pgm_sys_id": "F1", "code_system": "NAICS", "code": "331110"},
            {"pgm_sys_id": "F2", "code_system": "NAICS", "code": "493110"},
            {"pgm_sys_id": "F2", "code_system": "SIC", "code": "3312"},  # SIC는 제조업 판정에 안 쓴다
            {"pgm_sys_id": "F3", "code_system": "NAICS", "code": "325199"},
        ],
        "echo_program_subpart": [
            {"pgm_sys_id": "F1", "subpart_code": "CAAMACTZZZZ", "cfr_subpart": "ZZZZ", "subpart_desc": "Stationary RICE", "cfr_part": "63", "mapping_status": "mapped"},
            {"pgm_sys_id": "F1", "subpart_code": "CAAMACTDDDDD", "cfr_subpart": "DDDDD", "subpart_desc": "Industrial Boilers", "cfr_part": "63", "mapping_status": "mapped"},
            {"pgm_sys_id": "F2", "subpart_code": "CAAMACTZZZZ", "cfr_subpart": "ZZZZ", "subpart_desc": "Stationary RICE", "cfr_part": "63", "mapping_status": "mapped"},
            {"pgm_sys_id": "F3", "subpart_code": "CAAMACTDDDDD", "cfr_subpart": "DDDDD", "subpart_desc": "Industrial Boilers", "cfr_part": "63", "mapping_status": "mapped"},
            {"pgm_sys_id": "F3", "subpart_code": "CAAMACTXXXX", "cfr_subpart": None, "subpart_desc": "Unknown", "cfr_part": "63", "mapping_status": "unmapped"},
            {"pgm_sys_id": "F3", "subpart_code": "CAANSPSDc", "cfr_subpart": "Dc", "subpart_desc": "Small Boilers", "cfr_part": "60", "mapping_status": "mapped"},
        ],
        "echo_violation": [
            {"violation_id": "V1", "first_frv_date": date(2016, 3, 1)},
            {"violation_id": "V2", "first_frv_date": date(2021, 7, 15)},
        ],
        "echo_violation_facility": [
            {"violation_id": "V1", "pgm_sys_id": "F1"},
            {"violation_id": "V2", "pgm_sys_id": "F1"},
            {"violation_id": "V2", "pgm_sys_id": "F3"},
        ],
        "echo_activity": [
            {"activity_kind": "titlev", "activity_id": "T1", "activity_date": date(2022, 1, 31), "attributes": {"FACILITY_RPT_DEVIATION_FLAG": "Y"}},
            {"activity_kind": "titlev", "activity_id": "T2", "activity_date": date(2022, 2, 28), "attributes": {"FACILITY_RPT_DEVIATION_FLAG": "N"}},
            {"activity_kind": "titlev", "activity_id": "T3", "activity_date": date(2022, 3, 31), "attributes": {"FACILITY_RPT_DEVIATION_FLAG": "Y"}},
            {"activity_kind": "formal", "activity_id": "A1", "activity_date": date(2014, 6, 30), "attributes": {}},
            {"activity_kind": "formal", "activity_id": "A2", "activity_date": date(2019, 11, 5), "attributes": {}},
            {"activity_kind": "formal", "activity_id": "A3", "activity_date": date(2020, 5, 1), "attributes": {}},
        ],
        "echo_activity_facility": [
            {"activity_kind": "titlev", "activity_id": "T1", "pgm_sys_id": "F1"},
            {"activity_kind": "titlev", "activity_id": "T2", "pgm_sys_id": "F2"},
            {"activity_kind": "titlev", "activity_id": "T3", "pgm_sys_id": "F3"},
            {"activity_kind": "formal", "activity_id": "A1", "pgm_sys_id": "F2"},
            {"activity_kind": "formal", "activity_id": "A2", "pgm_sys_id": "F1"},
            {"activity_kind": "formal", "activity_id": "A3", "pgm_sys_id": "F3"},
        ],
        "echo_penalty": [
            {"penalty_key": "formal:10", "activity_kind": "formal", "activity_id": "A1", "amount": Decimal("5000")},
            {"penalty_key": "formal:11", "activity_kind": "formal", "activity_id": "A2", "amount": Decimal("12000")},
            {"penalty_key": "formal:12", "activity_kind": "formal", "activity_id": "A3", "amount": Decimal("0")},
        ],
    }


def _subpart(stats: dict, code: str) -> dict:
    return next(s for s in stats["subparts"] if s["code"] == code)


def test_summary_matches_hand_count():
    stats = compute_stats(base_rows())

    assert stats["summary"] == {
        "facilities": 3,
        "mfg_facilities": 2,
        "violation_facility_pct": 66.7,
        "penalty_count": 1,
        "penalty_median_usd": 12000,
        "penalty_total_usd": 12000,
        "penalty_max_usd": 12000,
        "deviation_y_pct": 66.7,
    }


def test_subparts_match_hand_count_and_ignore_unmapped_and_part_60():
    stats = compute_stats(base_rows())

    assert [s["code"] for s in stats["subparts"]] == ["DDDDD", "ZZZZ"]  # facilities 같으면 code 순
    assert _subpart(stats, "ZZZZ") == {
        "code": "ZZZZ", "desc": "Stationary RICE",
        "facilities": 2, "mfg_facilities": 1, "violation_facility_pct": 50.0,
        "penalty_count": 1, "penalty_median_usd": 12000, "penalty_total_usd": 12000, "penalty_max_usd": 12000, "deviation_y_pct": 50.0,
    }
    assert _subpart(stats, "DDDDD") == {
        "code": "DDDDD", "desc": "Industrial Boilers",
        "facilities": 2, "mfg_facilities": 2, "violation_facility_pct": 100.0,
        "penalty_count": 1, "penalty_median_usd": 12000, "penalty_total_usd": 12000, "penalty_max_usd": 12000, "deviation_y_pct": 100.0,
    }


def test_yearly_counts_violations_once_and_penalties_by_action_year():
    stats = compute_stats(base_rows())

    years = {y["year"]: y for y in stats["yearly"]}
    assert [y["year"] for y in stats["yearly"]] == list(range(2000, 2022))  # 2000부터 마지막 해까지 빈 해도 0으로
    assert years[2014] == {"year": 2014, "violations": 0, "penalties": 1}
    assert years[2016] == {"year": 2016, "violations": 1, "penalties": 0}
    assert years[2019] == {"year": 2019, "violations": 0, "penalties": 1}
    assert years[2021] == {"year": 2021, "violations": 1, "penalties": 0}  # V2는 F1·F3 둘 다 붙었지만 1건
    assert sum(y["violations"] for y in stats["yearly"]) == 2
    assert sum(y["penalties"] for y in stats["yearly"]) == 2  # A1(2014)·A2(2019). A3는 금액 0


def test_same_action_on_two_facilities_counts_penalty_once():
    rows = base_rows()
    # A2 처분이 F3에도 붙는다 → FORMAL_ACTIONS.csv 행이 하나 더 있어 echo_penalty 행도 하나 더 생긴다
    rows["echo_activity_facility"].append({"activity_kind": "formal", "activity_id": "A2", "pgm_sys_id": "F3"})
    rows["echo_penalty"].append({"penalty_key": "formal:13", "activity_kind": "formal", "activity_id": "A2", "amount": Decimal("12000")})

    stats = compute_stats(rows)

    assert stats["summary"]["penalty_count"] == 1
    assert stats["summary"]["penalty_median_usd"] == 12000
    assert _subpart(stats, "DDDDD")["penalty_count"] == 1  # F1·F3 둘 다 DDDDD인데도 1
    assert sum(y["penalties"] for y in stats["yearly"]) == 2


def test_penalty_total_and_max_over_two_actions():
    rows = base_rows()
    # SUU-242: F1에 2021년 $30,000 처분이 하나 더 → 총액 42,000 · 최대 30,000 · 중앙값 21,000
    rows["echo_activity"].append({"activity_kind": "formal", "activity_id": "A4", "activity_date": date(2021, 3, 2), "attributes": {}})
    rows["echo_activity_facility"].append({"activity_kind": "formal", "activity_id": "A4", "pgm_sys_id": "F1"})
    rows["echo_penalty"].append({"penalty_key": "formal:14", "activity_kind": "formal", "activity_id": "A4", "amount": Decimal("30000")})

    stats = compute_stats(rows)

    assert stats["summary"]["penalty_count"] == 2
    assert stats["summary"]["penalty_total_usd"] == 42000
    assert stats["summary"]["penalty_max_usd"] == 30000
    assert stats["summary"]["penalty_median_usd"] == 21000
    assert _subpart(stats, "ZZZZ")["penalty_total_usd"] == 42000  # F1 은 ZZZZ·DDDDD 둘 다


def test_empty_release_gives_zero_and_null_not_division_error():
    stats = compute_stats({table: [] for table in base_rows()})

    assert stats["summary"] == {
        "facilities": 0, "mfg_facilities": 0, "violation_facility_pct": 0.0,
        "penalty_count": 0, "penalty_median_usd": None, "penalty_total_usd": 0, "penalty_max_usd": None, "deviation_y_pct": 0.0,
    }
    assert stats["subparts"] == [] and stats["yearly"] == []


def test_write_stats_saves_json_file(tmp_path):
    out = tmp_path / "public" / "echo-stats.json"

    write_stats(compute_stats(base_rows()), out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"summary", "subparts", "yearly"}
    assert data["summary"]["facilities"] == 3


@pytest.mark.skipif(not os.environ.get("SUPABASE_DB_URL"), reason="실제 DB가 있을 때만")
def test_live_release_2026_09_17_matches_known_counts():
    import psycopg

    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        release_id = current_release_id(conn)
        stats = compute_stats(fetch_rows(conn, release_id))

    assert _subpart(stats, "ZZZZ")["facilities"] == 28174
    assert _subpart(stats, "DDDDD")["violation_facility_pct"] == pytest.approx(75.7, abs=0.1)
