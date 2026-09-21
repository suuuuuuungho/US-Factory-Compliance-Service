"""Generate the transparent etched-flag hero asset for SUU-203."""

from __future__ import annotations

import base64
from io import BytesIO
import os
from pathlib import Path

from openai import OpenAI


PROMPT = """A waving American flag rendered as a fine-line copperplate etching / engraving,
in the style of a banknote or 19th-century intaglio print. White ink lines only,
no color, on a fully transparent background. Frozen mid-ripple with deep folds,
thin horizontal cross-hatching that follows the curves of the cloth; stars and
stripes readable but loose. Elegant, restrained, museum quality. No text, no frame,
no border, no pole, no watermark. The flag's left (hoist) edge and bottom edge
dissolve softly into transparency so it can sit over a dark night sky."""

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "public" / "flag-etching.png"
MAX_BYTES = 500 * 1024


def _fit_size(png: bytes) -> bytes:
    """Keep generated PNGs within the repository's 500 KB asset budget."""
    if len(png) <= MAX_BYTES:
        return png

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Generated image exceeds 500 KB; install Pillow to optimize it."
        ) from exc

    image = Image.open(BytesIO(png)).convert("RGBA")
    for width, colors in ((1200, 128), (1152, 96), (1080, 80), (960, 64)):
        resized = image.copy()
        resized.thumbnail((width, width), Image.Resampling.LANCZOS)
        optimized = resized.quantize(
            colors=colors,
            method=Image.Quantize.FASTOCTREE,
            dither=Image.Dither.FLOYDSTEINBERG,
        )
        output = BytesIO()
        optimized.save(output, format="PNG", optimize=True, compress_level=9)
        if output.tell() <= MAX_BYTES:
            return output.getvalue()

    raise RuntimeError("Could not optimize generated image below 500 KB.")


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY must be set in the environment.")

    result = OpenAI().images.generate(
        model="gpt-image-1",
        prompt=PROMPT,
        size="1536x1024",
        quality="high",
        background="transparent",
        output_format="png",
    )
    png = _fit_size(base64.b64decode(result.data[0].b64_json))
    OUTPUT_PATH.write_bytes(png)
    print(f"Wrote {OUTPUT_PATH} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
