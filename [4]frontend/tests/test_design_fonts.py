"""SUU-226: DESIGN.md가 SF Pro(--font-sans)·New York(--font-serif)을 고정 폰트로 명시한다.

코드(layout.tsx, globals.css)는 이미 이 둘을 쓴다. 문서가 코드와 같은 말을 하는지만 본다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "[4]frontend" / "DESIGN.md"


def test_design_md_font_family_values_are_only_sf_pro_or_new_york():
    text = DESIGN.read_text(encoding="utf-8")
    families = set(re.findall(r"fontFamily:\s*(.+)", text))
    assert families, "frontmatter에 fontFamily 토큰이 있어야 한다"
    assert families <= {"SF Pro", "New York"}, families


def test_design_md_font_family_section_fixes_two_fonts():
    text = DESIGN.read_text(encoding="utf-8")
    section = text.split("### Font Family", 1)[1].split("### Hierarchy", 1)[0]
    assert "고정 폰트" in section
    assert "SF Pro" in section and "--font-sans" in section
    assert "New York" in section and "--font-serif" in section
