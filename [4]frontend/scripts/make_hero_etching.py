"""Build the monochrome etched hero artwork from the repository source image."""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE = SCRIPT_DIR.parents[1] / "Hero Image.png"
TARGET = SCRIPT_DIR.parent / "public" / "hero-etching.png"
TARGET_WIDTH = 1600


def make_etching(source: Path = SOURCE, target: Path = TARGET) -> None:
    with Image.open(source) as original:
        height = round(original.height * TARGET_WIDTH / original.width)
        gray = ImageOps.grayscale(original).resize(
            (TARGET_WIDTH, height), Image.Resampling.LANCZOS
        )

    gray = ImageOps.autocontrast(gray, cutoff=1)
    base = ImageEnhance.Contrast(gray).enhance(1.35)

    edges = base.filter(ImageFilter.FIND_EDGES)
    edge_ink = ImageOps.invert(ImageEnhance.Contrast(edges).enhance(1.8))
    etched = ImageChops.multiply(base, edge_ink)

    # Horizontal hatch marks appear only in the darker parts of the scene.
    hatch_mask = Image.new("L", etched.size, 0)
    hatch_lines = Image.new("L", etched.size, 0)
    line_draw = ImageDraw.Draw(hatch_lines)
    for y in range(0, etched.height, 4):
        line_draw.line((0, y, etched.width, y), fill=255, width=1)

    dark_areas = etched.point(lambda value: 255 if value < 175 else 0)
    hatch_mask = ImageChops.multiply(dark_areas, hatch_lines)
    hatching = Image.new("L", etched.size, 255)
    hatching.paste(105, mask=hatch_mask)
    etched = ImageChops.multiply(etched, hatching)

    # A small palette keeps the committed PNG comfortably below 500 KB.
    output = ImageOps.autocontrast(etched).quantize(colors=64)
    target.parent.mkdir(parents=True, exist_ok=True)
    output.save(target, format="PNG", optimize=True, compress_level=9)


if __name__ == "__main__":
    make_etching()
