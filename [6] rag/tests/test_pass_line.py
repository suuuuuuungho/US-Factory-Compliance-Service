"""SUU-137: 검색 합격선. runs.jsonl의 기본 조합 최신 run이 선 아래면 CI가 빨강."""
import sys
from pathlib import Path

RAG = Path(__file__).parents[1]
sys.path.insert(0, str(RAG / "eval"))

from pass_line import DEFAULT_RUN, PASS_LINE, check_pass_line, latest_default_run, load_runs  # noqa: E402


def run(run_id, run_at, ndcg10=0.7, hit20=0.96, subpart20=0.98, **overrides):
    return {
        "run_id": run_id, "run_at": run_at, **DEFAULT_RUN, **overrides,
        "metrics": {"ndcg": {"10": ndcg10}, "hit_loose": {"20": hit20}, "subpart_hit_primary": {"20": subpart20}},
    }


def test_latest_default_run_picks_newest_of_default_combo():
    runs = [
        run("old", "2026-09-17T00:00:00Z"),
        run("no-llm", "2026-09-19T00:00:00Z", llm_model=None),
        run("v1", "2026-09-19T00:00:00Z", eval_set_version="v1"),
        run("new", "2026-09-18T00:00:00Z"),
    ]
    assert latest_default_run(runs)["run_id"] == "new"
    assert latest_default_run([runs[1], runs[2]]) is None


def test_check_pass_line_flags_metrics_below_line():
    assert PASS_LINE == {"ndcg@10": 0.66, "hit@20": 0.95, "subpart@20": 0.95}
    ok = check_pass_line(run("x", "2026-09-18T00:00:00Z"))
    assert all(passed for _, _, passed in ok.values())
    bad = check_pass_line(run("x", "2026-09-18T00:00:00Z", ndcg10=0.65, subpart20=0.94))
    assert [k for k, (_, _, passed) in bad.items() if not passed] == ["ndcg@10", "subpart@20"]


def test_latest_default_run_in_runs_jsonl_passes():
    latest = latest_default_run(load_runs())
    assert latest is not None, "기본 조합(hybrid v2 + 규칙 + gpt-5-mini) run이 runs.jsonl에 없다"
    result = check_pass_line(latest)
    failed = {k: v for k, v in result.items() if not v[2]}
    assert not failed, f"{latest['run_id']} 합격선 미달: {failed}"
