"""SUU-140: Next.js 뼈대 + 크림·세피아 테마 + CI frontend job 검사.

프론트 코드 자체는 vitest(`npm test`)와 CI `frontend` job이 검사한다.
여기서는 "뼈대가 규약대로 놓였는지"를 파일 내용으로 확인한다.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "[4]frontend"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _package_json():
    return json.loads((FRONT / "package.json").read_text(encoding="utf-8"))


def _all_deps(pkg):
    return {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}


def test_package_json_has_next_tailwind_vitest():
    pkg = _package_json()
    deps = _all_deps(pkg)
    for name in ("next", "react", "react-dom", "tailwindcss", "typescript", "vitest"):
        assert name in deps, f"{name} 없음"
    assert pkg["scripts"]["build"].startswith("next build")
    assert "vitest" in pkg["scripts"]["test"]


def test_theme_css_defines_paper_ink_line_vars():
    css = (FRONT / "src" / "app" / "globals.css").read_text(encoding="utf-8")
    assert re.search(r"--color-paper:\s*#F5F0E6", css, re.I)
    assert re.search(r"--color-ink:\s*#4A2E1E", css, re.I)
    assert re.search(r"--color-line:\s*#C9B99A", css, re.I)


def test_ci_has_frontend_job_running_test_and_build():
    ci = CI.read_text(encoding="utf-8")
    m = re.search(r"^  frontend:\n(?P<body>(?:    .*\n|\n)+)", ci, re.M)
    assert m, "ci.yml에 frontend job 없음"
    body = m.group("body")
    assert "npm ci" in body
    assert "npm test" in body
    assert "npm run build" in body
    assert "[4]frontend" in body, "working-directory가 [4]frontend 여야 함"


def test_engraving_readme_lists_all_image_files():
    readme = (FRONT / "public" / "engraving" / "README.md").read_text(encoding="utf-8")
    for name in ("factory.png", "train.png", "smoke-1.png", "smoke-2.png", "smoke-3.png", "hero.png"):
        assert name in readme, f"README에 {name} 없음"
    assert "투명" in readme


def test_vitest_smoke_test_exists():
    assert (FRONT / "src" / "app" / "page.test.tsx").exists()
