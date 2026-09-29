"""SUU-298: 자동 갱신 워크플로가 실제 러너에서 끝까지 돌고, 실패는 빨간불로 보여야 한다.

9/29 첫 수동 실행에서 드러난 것:
- pytest 는 pyproject 의 pythonpath 로 eCFR 폴더를 알려 주지만 `python 스크립트.py` 는 모른다 → ecfr_publish import 실패.
- `python ... | tee out.txt` 는 기본 셸(bash -e)에서 tee 의 성공만 본다 → 실패했는데 초록불.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
PIPELINE = REPO / "[2] db" / "pipeline"
WORKFLOWS = [REPO / ".github" / "workflows" / name for name in ("db-refresh.yml", "echo-refresh.yml")]


@pytest.mark.parametrize("script", ["3_ECHO/echo_ingest.py", "3_ECHO/echo_parse.py", "2_Federal Register/fr_ingest.py"])
def test_script_imports_its_neighbours_like_the_workflow_runs_it(script, tmp_path):
    path = PIPELINE / script
    # `python 스크립트.py` 처럼 sys.path[0] 만 스크립트 폴더. PYTHONPATH 도 없다. __main__ 은 실행하지 않는다.
    code = f"import sys; sys.path[0] = {str(path.parent)!r}; import {path.stem}"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_steps_piping_into_tee_use_bash_so_pipefail_is_on(workflow):
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    piped = [step for job in data["jobs"].values() for step in job["steps"] if "| tee" in step.get("run", "")]

    assert piped
    for step in piped:
        assert step.get("shell") == "bash", step["run"]  # GitHub: shell: bash → bash -eo pipefail
