from __future__ import annotations

import io
import os
import shutil

import numpy as np
import pytest
from PIL import Image, ImageDraw

os.environ.setdefault("ENVIRONMENT", "test")

needs_tools = pytest.mark.skipif(
    not (shutil.which("potrace") and (shutil.which("magick") or shutil.which("convert"))),
    reason="ImageMagick/potrace not installed (runs in the worker image / CI)",
)


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def line_art() -> bytes:
    """Clean coloring-page-like image: thick circle + square outlines on white."""
    img = Image.new("L", (1536, 2048), 255)
    d = ImageDraw.Draw(img)
    d.ellipse((300, 300, 1200, 1200), outline=0, width=24)
    d.rectangle((400, 1300, 1100, 1900), outline=0, width=24)
    return png_bytes(img)


@pytest.fixture
def design_png(tmp_path, line_art):  # type: ignore[no-untyped-def]
    """A 300-DPI-sized design (7.5 x 10 in)."""
    img = Image.open(io.BytesIO(line_art)).resize((2250, 3000))
    p = tmp_path / "design.png"
    img.save(p)
    return p


def gradient(w: int = 1536, h: int = 2048) -> bytes:
    arr = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    return png_bytes(Image.fromarray(arr, mode="L"))
