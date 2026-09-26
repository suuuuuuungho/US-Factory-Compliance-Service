"""SUU-155: 답변 합격선. answer_runs.jsonl의 기준 조합(상위 10, 항상 A 없음) 최신 run이 선 아래면 CI가 빨강."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from answer_pass_line import DEFAULT_RUN, PASS_LINE, check_pass_line, latest_default_run, load_runs  # noqa: E402


def run(run_id, run_at, subpart=0.96, recall=0.74, grounded=0.99, judge=1.77, **overrides):
    return {
        "run_id": run_id, "run_at": run_at, **DEFAULT_RUN, **overrides,
        "metrics": {"subpart": subpart, "citation_recall": recall, "citation_grounded": grounded, "judge": judge},
    }


def test_latest_default_run_picks_newest_top10_without_always_sections():
    assert DEFAULT_RUN == {"eval_set_version": "v2", "top_n": 10, "always_sections": [],
                           "answer_model": "gpt-5-mini", "judge_model": "gpt-5-mini"}
    runs = [
        run("old", "2026-09-17T00:00:00Z"),
        run("top5", "2026-09-19T00:00:00Z", top_n=5),
        run("alwaysA", "2026-09-20T00:00:00Z", always_sections=["section-63.2", "section-63.7", "section-63.8"]),
        run("claude", "2026-09-20T00:00:00Z", answer_model="claude-sonnet-5"),
        run("new", "2026-09-18T00:00:00Z"),
    ]
    assert latest_default_run(runs)["run_id"] == "new"
    assert latest_default_run(runs[1:4]) is None


def test_missing_always_sections_counts_as_empty():
    # SUU-153 이전 run에는 always_sections 키가 없다. 없으면 []로 본다
    r = run("no-key", "2026-09-19T00:00:00Z")
    del r["always_sections"]
    assert latest_default_run([r])["run_id"] == "no-key"


def test_check_pass_line_flags_only_metrics_below_line():
    assert PASS_LINE == {"subpart": 0.93, "citation_recall": 0.70, "citation_grounded": 0.96, "judge": 1.71}
    ok = check_pass_line(run("x", "2026-09-18T00:00:00Z"))
    assert all(passed for _, _, passed in ok.values())
    bad = check_pass_line(run("x", "2026-09-18T00:00:00Z", recall=0.69, judge=1.70))
    assert [k for k, (_, _, passed) in bad.items() if not passed] == ["citation_recall", "judge"]
    assert bad["citation_recall"] == (0.69, 0.70, False)


def test_latest_default_run_in_answer_runs_jsonl_passes():
    latest = latest_default_run(load_runs())
    assert latest is not None, "기준 조합(v2, 상위 10, 항상 A 없음, gpt-5-mini) run이 answer_runs.jsonl에 없다"
    result = check_pass_line(latest)
    failed = {k: v for k, v in result.items() if not v[2]}
    assert not failed, f"{latest['run_id']} 합격선 미달: {failed}"


# ---- SUU-278: 채점기 v2 합격선. 기준 조합 = v2·관문·상위 10·102건 전체·상한 20,000·검증문 적용 ----
# 합격선 = 102건 검증 run 점수에서 동점 폭 0.03(계획 [5]-4)을 뺀 퇴보 방지선. 비용은 10% 여유. v1 합격선은 그대로 둔다.

from answer_pass_line import (  # noqa: E402
    DEFAULT_RUN_V2, PASS_LINE_V2, TIE_BAND_FULL, check_pass_line_v2, is_default_run, is_default_run_v2, latest_default_run_v2,
)

V2_METRICS = ("g0_grounded", "g1_quote", "g2_subpart", "g3_citation_recall", "g4_checklist")


def run_v2(run_id, run_at, *, g0=0.99, g1=0.99, g2=0.95, g3=0.65, g4=0.99, cost=0.023, **overrides):
    return {
        "run_id": run_id, "run_at": run_at, **DEFAULT_RUN_V2, **overrides,
        "metrics": {"scorer_version": "v2", "n": 102, "g0_grounded": g0, "g1_quote": g1, "g2_subpart": g2,
                    "g3_citation_recall": g3, "g4_checklist": g4, "g5_cost_usd": cost, "g5_latency_s": 60.0, "failed": []},
    }


def test_default_run_v2_is_the_final_combination_from_the_plan():
    assert DEFAULT_RUN_V2 == {"scorer_version": "v2", "shape": "gates", "top_n": 10, "always_sections": [], "subset": False,
                              "answer_model": "gpt-5-mini", "max_completion_tokens": 20000, "verified": True}
    assert TIE_BAND_FULL == 0.03
    assert is_default_run_v2(run_v2("ok", "2026-09-27T00:00:00Z"))
    assert not is_default_run_v2(run_v2("subset", "2026-09-27T00:00:00Z", subset=True))
    assert not is_default_run_v2(run_v2("raw", "2026-09-27T00:00:00Z", verified=False))
    assert not is_default_run_v2(run_v2("criteria", "2026-09-27T00:00:00Z", shape="criteria"))
    assert not is_default_run_v2(run_v2("10k", "2026-09-27T00:00:00Z", max_completion_tokens=10000))
    assert not is_default_run(run_v2("ok", "2026-09-27T00:00:00Z"))  # v1 합격선은 v2 run을 안 본다


def test_latest_default_run_v2_picks_newest_matching_run():
    runs = [run("v1", "2026-09-30T00:00:00Z"), run_v2("old", "2026-09-27T00:00:00Z"),
            run_v2("subset", "2026-09-29T00:00:00Z", subset=True), run_v2("new", "2026-09-28T00:00:00Z")]
    assert latest_default_run_v2(runs)["run_id"] == "new"
    assert latest_default_run_v2(runs[:1]) is None


def test_check_pass_line_v2_flags_metrics_below_line_and_cost_above_line():
    assert set(PASS_LINE_V2) == {*V2_METRICS, "g5_cost_usd"}
    ok = check_pass_line_v2(run_v2("x", "2026-09-27T00:00:00Z", **{m: 1.0 for m in ("g0", "g1", "g2", "g3", "g4")}, cost=0.0))
    assert all(passed for _, _, passed in ok.values())
    bad = check_pass_line_v2(run_v2("x", "2026-09-27T00:00:00Z", g3=0.0, cost=9.0))
    assert [k for k, (_, _, passed) in bad.items() if not passed] == ["g3_citation_recall", "g5_cost_usd"]
    assert bad["g3_citation_recall"] == (0.0, PASS_LINE_V2["g3_citation_recall"], False)


def test_pass_line_v2_is_the_saved_full_verified_run_minus_the_tie_band():
    latest = latest_default_run_v2(load_runs())
    assert latest is not None, "기준 조합(v2·관문·상위 10·102건·out20k·verified) run이 answer_runs.jsonl에 없다"
    m = latest["metrics"]
    for k in V2_METRICS:
        assert PASS_LINE_V2[k] == round(m[k] - TIE_BAND_FULL, 3), k
    assert PASS_LINE_V2["g5_cost_usd"] == round(m["g5_cost_usd"] * 1.1, 4)


def test_latest_default_run_v2_in_answer_runs_jsonl_passes():
    latest = latest_default_run_v2(load_runs())
    assert latest is not None
    result = check_pass_line_v2(latest)
    failed = {k: v for k, v in result.items() if not v[2]}
    assert not failed, f"{latest['run_id']} 합격선 미달: {failed}"
