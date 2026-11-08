"""Brand constants and the mascot as an embeddable raster (colour or grayscale)."""

from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image

from crayonlark.core.config import ASSETS_DIR

NAME = "Crayonlark"
TAGLINE = "Little books for big imaginations"
SITE = "crayonlark.com"
COLORS = {
    "sun": "#FFC93C",
    "sky": "#5BC0EB",
    "coral": "#FF6F59",
    "cream": "#FFF8EE",
    "ink": "#1F2333",
}

LICENSE_LINES = [
    "Thank you for your purchase! Please read this short license.",
    "",
    "You MAY:",
    "• Print these pages as many times as you like for your own family.",
    "• Print copies for ONE classroom or homeschool group that you teach.",
    "",
    "You may NOT:",
    "• Share, resell or give away the PDF file or printed copies.",
    "• Upload the files to any website, shared drive or file-sharing service.",
    "• Use the designs in products for sale (print-on-demand, stickers, etc.).",
    "",
    "License: personal and single classroom use only.",
    "Copyright stays with Crayonlark. Questions? Visit crayonlark.com/contact",
]


AI_LICENSE_LINE = "Designed by Crayonlark. Artwork made with AI tools and edited by Crayonlark."
NON_AI_LICENSE_LINE = "Designed by Crayonlark."


@lru_cache
def mascot_png(gray: bool = False, width: int = 900) -> bytes:
    import cairosvg

    png = cairosvg.svg2png(url=str(ASSETS_DIR / "brand" / "lark.svg"), output_width=width)
    if not gray:
        return png
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.alpha_composite(img)
    out = io.BytesIO()
    bg.convert("L").save(out, format="PNG")
    return out.getvalue()
