"""SUU-162: [4]frontend 뼈대(Next.js + vitest)가 규약대로 놓였고 CI frontend job이 npm test를 돈다.

프론트 코드 자체는 vitest(tests/smoke.test.tsx)와 CI가 검사한다. 여기서는 파일 내용만 본다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "[4]frontend"
CI = ROOT / ".github" / "workflows" / "ci.yml"
RULES = ROOT / "[1] docs" / "4) workflow" / "2_rules.md"


def _pkg():
    return json.loads((FRONT / "package.json").read_text(encoding="utf-8"))


def test_package_json_has_next_tailwind_vitest_testing_library():
    pkg = _pkg()
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for name in ("next", "react", "react-dom", "tailwindcss", "typescript",
                 "vitest", "@vitejs/plugin-react", "jsdom", "@testing-library/react"):
        assert name in deps, f"{name} 없음"
    assert pkg["scripts"]["test"] == "vitest run"
    assert (FRONT / "package-lock.json").exists(), "npm ci 는 lock 파일이 있어야 돈다"


def test_vitest_config_uses_jsdom_and_tests_folder():
    cfg = (FRONT / "vitest.config.ts").read_text(encoding="utf-8")
    assert 'environment: "jsdom"' in cfg
    assert "tests/**/*.test.tsx" in cfg  # 2_rules.md 8번: 프론트 테스트는 tests/*.test.tsx


def test_ci_frontend_job_runs_npm_ci_and_npm_test_in_folder():
    ci = CI.read_text(encoding="utf-8")
    m = re.search(r"^  frontend:\n(?P<body>(?:    .*\n|\n)+)", ci, re.M)
    assert m, "ci.yml에 frontend job 없음"
    body = m.group("body")
    assert 'working-directory: "[4]frontend"' in body
    assert "npm ci" in body and "npm test" in body
    assert 'cache-dependency-path: "[[]4]frontend/package-lock.json"' in body  # [4]는 glob이라 이스케이프


def test_rules_doc_says_frontend_tests_are_vitest():
    section = RULES.read_text(encoding="utf-8").split("## 8. 테스트")[1].split("## 9.")[0]
    assert "vitest" in section
    assert "[4]frontend/tests/*.test.tsx" in section
