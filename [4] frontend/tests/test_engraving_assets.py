"""SUU-141: 판화 그림 조각 6종이 README 규약대로 존재하고 진짜 투명(RGBA)이다."""

from pathlib import Path

ENGRAVING = Path(__file__).resolve().parents[1] / "public" / "engraving"
FILES = ("factory.png", "train.png", "smoke-1.png", "smoke-2.png", "smoke-3.png", "hero.png")


def _png_color_type(path: Path) -> int:
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name}: PNG 아님"
    return b[25]  # IHDR color type. 6 = RGBA


def test_all_engraving_images_exist_and_have_alpha():
    for name in FILES:
        p = ENGRAVING / name
        assert p.exists(), f"{name} 없음"
        assert _png_color_type(p) == 6, f"{name}: 알파 채널 없음 (투명 PNG여야 함)"
