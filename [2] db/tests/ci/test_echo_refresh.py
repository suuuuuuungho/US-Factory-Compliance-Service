"""SUU-294: ECHO 를 매주 자동으로 받아 Part 63 만 적재하는 GitHub Actions 워크플로.

db-refresh.yml(SUU-293) 과 같은 모양이지만 파일은 따로 둔다 — 그쪽 테스트가 매일 cron 하나만 있다고 고정하기 때문.
실제로 돌리지는 않는다. YAML 만 읽는다. 진짜 1회 실행은 사람이 수동 버튼으로 확인한다.
"""
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "echo-refresh.yml"


def _load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data, data.get("on", data.get(True))  # PyYAML 은 `on:` 을 True 로 읽는다


def _run_text(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_runs_every_tuesday_at_0517_utc_and_by_manual_button():
    _, triggers = _load()
    assert [s["cron"] for s in triggers["schedule"]] == ["17 5 * * 2"]  # EPA 가 일요일에 올린다 → 화요일
    assert "workflow_dispatch" in triggers


def test_never_runs_two_echo_refreshes_at_once():
    data, _ = _load()
    assert data.get("concurrency"), "concurrency 로 겹침을 막아야 한다"


def test_echo_job_runs_collect_parse_ingest_in_order():
    data, _ = _load()
    text = _run_text(data["jobs"]["echo"])
    positions = [text.index(f"echo_{step}.py") for step in ("collect", "parse", "ingest")]
    assert positions == sorted(positions)
    assert data["jobs"]["echo"].get("timeout-minutes", 0) >= 120  # 750만 행 파싱


def test_only_the_raw_zips_are_kept_as_artifact_and_only_when_new():
    data, _ = _load()
    uploads = [s for s in data["jobs"]["echo"]["steps"] if str(s.get("uses", "")).startswith("actions/upload-artifact")]
    assert uploads and "new" in str(uploads[0].get("if", ""))
    path = str(uploads[0]["with"]["path"])
    assert "ECHO/raw" in path and "parsed" not in path  # parsed 는 크다. 원본 ZIP 만


def test_uses_the_four_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_DB_URL", "SLACK_WEBHOOK_URL"):
        assert f"secrets.{name}" in text


def test_slack_tells_changed_unchanged_or_failed():
    data, _ = _load()
    notify = data["jobs"]["notify"]
    assert "always()" in str(notify.get("if", ""))
    text = _run_text(notify)
    for word in ("ECHO", "바뀜", "안 바뀜", "실패"):
        assert word in text
