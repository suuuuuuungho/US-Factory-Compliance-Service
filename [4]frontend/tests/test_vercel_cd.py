"""SUU-165: Vercel 자동 배포. 코드로 남는 것 세 가지를 파일 내용으로 확인한다.
- render.yaml FRONTEND_ORIGIN에 Vercel 주소(https://*.vercel.app)가 들어 있다 (CORS)
- slack.yml이 Vercel의 deployment_status(Production, success/failure)를 알린다
- 1_workflow.md 7절 6번 행이 Vercel 연결 완료
Vercel 프로젝트 연결·환경변수·실제 배포는 사람이 대시보드에서 한다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "render.yaml"
SLACK = ROOT / ".github" / "workflows" / "slack.yml"
WORKFLOW = ROOT / "[1] docs" / "4) workflow" / "1_workflow.md"


def test_render_frontend_origin_has_vercel_url_and_localhost():
    text = RENDER.read_text(encoding="utf-8")
    m = re.search(r"- key: FRONTEND_ORIGIN\n\s+value: ['\"]?([^'\"\n]+)", text)
    assert m, "FRONTEND_ORIGIN에 value가 있어야 한다"
    origins = [o.strip() for o in m.group(1).split(",")]
    assert "http://localhost:3000" in origins
    assert any(re.fullmatch(r"https://[a-z0-9-]+\.vercel\.app", o) for o in origins), origins


def test_slack_notifies_vercel_production_deployment_status():
    text = SLACK.read_text(encoding="utf-8")
    on = text.split("\njobs:")[0]
    assert re.search(r"^  deployment_status:", on, re.M), "on: 에 deployment_status 없음"
    # 프리뷰 배포는 안 알린다. Production 이고 success/failure 만
    cond = re.search(r"    if: >-\n((?:      .*\n)+)", text).group(1)
    assert "github.event_name == 'deployment_status'" in cond
    assert "github.event.deployment.environment == 'Production'" in cond
    assert "github.event.deployment_status.state" in cond
    # 메시지에 배포 결과와 주소
    assert "DEPLOY_STATE: ${{ github.event.deployment_status.state }}" in text
    assert "DEPLOY_URL: ${{ github.event.deployment_status.environment_url }}" in text
    assert '"$EVENT" = deployment_status' in text


def test_workflow_doc_marks_vercel_done():
    row = re.search(r"^\| 6 \|.*$", WORKFLOW.read_text(encoding="utf-8"), re.M).group(0)
    assert "✅" in row and "SUU-165" in row
