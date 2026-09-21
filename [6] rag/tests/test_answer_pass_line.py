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
