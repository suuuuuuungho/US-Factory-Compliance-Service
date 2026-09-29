"""SUU-293: eCFR·FR 원문을 매일 자동으로 받아 적재하는 GitHub Actions 워크플로.

실제로 돌리지는 않는다. YAML 을 읽어 "매일 일정 · 수동 버튼 · eCFR/FR job · Secret 4개 · Slack" 이
빠짐없이 있는지만 본다. 진짜 1회 실행은 PR 에서 수동 버튼으로 확인한다 (완료 기준 3번).
"""
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "db-refresh.yml"


def _load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))  # PyYAML 은 `on:` 을 True 로 읽는다
    return data, triggers


def _run_text(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_runs_every_day_at_0317_utc_and_by_manual_button():
    _, triggers = _load()
    assert [s["cron"] for s in triggers["schedule"]] == ["17 3 * * *"]
    assert "workflow_dispatch" in triggers


def test_never_runs_two_refreshes_at_once():
    data, _ = _load()
    assert data.get("concurrency"), "concurrency 로 겹침을 막아야 한다"


def test_ecfr_and_fr_jobs_run_collect_parse_ingest_in_order():
    data, _ = _load()
    for job, prefix in (("ecfr", "ecfr"), ("fr", "fr")):
        text = _run_text(data["jobs"][job])
        positions = [text.index(f"{prefix}_{step}.py") for step in ("collect", "parse", "ingest")]
        assert positions == sorted(positions), f"{job}: collect → parse → ingest 순서"


def test_fr_raw_is_cached_between_runs():
    data, _ = _load()
    cache_steps = [s for s in data["jobs"]["fr"]["steps"] if str(s.get("uses", "")).startswith("actions/cache")]
    assert cache_steps and "Federal Register/raw" in str(cache_steps[0]["with"]["path"])


def test_artifacts_are_uploaded_only_when_a_new_release_was_made():
    data, _ = _load()
    for job in ("ecfr", "fr"):
        uploads = [s for s in data["jobs"][job]["steps"] if str(s.get("uses", "")).startswith("actions/upload-artifact")]
        assert uploads, f"{job}: raw·parsed Artifact 업로드 단계"
        assert "new" in str(uploads[0].get("if", "")), f"{job}: status=new 일 때만 올린다"


def test_uses_the_four_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_DB_URL", "SLACK_WEBHOOK_URL"):
        assert f"secrets.{name}" in text


def test_slack_tells_changed_unchanged_or_failed_and_asks_about_reindex():
    data, _ = _load()
    notify = data["jobs"]["notify"]
    assert "always()" in str(notify.get("if", "")), "실패해도 알린다"
    text = _run_text(notify)
    assert "SLACK_WEBHOOK_URL" in str(notify) + text
    for word in ("바뀜", "안 바뀜", "실패", "색인"):
        assert word in text
