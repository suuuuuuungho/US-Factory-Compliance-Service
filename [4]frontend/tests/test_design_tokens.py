"""SUU-170: DESIGN.md(Framer)의 색·둥근 모서리 값이 globals.css 변수로 들어가고, layout.tsx가 Inter를 쓴다.

화면이 그려지는지는 vitest(tests/smoke.test.tsx)가 본다. 여기서는 파일 내용만 본다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "[4]frontend"
GLOBALS = FRONT / "src" / "app" / "globals.css"
LAYOUT = FRONT / "src" / "app" / "layout.tsx"


def _var(css: str, name: str) -> str | None:
    m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", css)
    return m.group(1).strip() if m else None


def test_globals_css_has_framer_color_and_radius_tokens():
    css = GLOBALS.read_text(encoding="utf-8")
    assert _var(css, "--color-canvas") == "#090909"
    assert _var(css, "--color-accent-blue") == "#0099ff"
    assert _var(css, "--color-surface-1") == "#141414"
    assert _var(css, "--radius-pill") == "100px"


def test_globals_css_registers_tokens_in_theme():
    css = GLOBALS.read_text(encoding="utf-8")
    m = re.search(r"@theme[^{]*\{(?P<body>[^}]*)\}", css)
    assert m, "globals.css에 @theme 블록 없음"
    body = m.group("body")
    assert "--color-canvas" in body
    assert "--radius-pill" in body
    assert "--font-geist-sans" not in body and "--font-geist-mono" not in body


def test_layout_uses_sf_pro_not_geist():
    """SUU-204: Inter → 로컬 SF Pro(next/font/local)."""
    src = LAYOUT.read_text(encoding="utf-8")
    assert re.search(r'from\s*"next/font/local"', src)
    assert "SF-Pro-latin.woff2" in src
    assert "Geist" not in src and "next/font/google" not in src


def test_globals_css_has_no_text_metal():
    """SUU-181: 히어로 metal utility 제거."""
    assert "text-metal" not in GLOBALS.read_text(encoding="utf-8")
