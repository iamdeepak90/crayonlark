"""Auto-colour a black & white coloring page for cover art: fill each closed white region
with a palette colour (lines stay black). Regions touching the image border stay white."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

PALETTE = [
    (255, 201, 60),
    (91, 192, 235),
    (255, 111, 89),
    (140, 214, 140),
    (196, 160, 240),
    (255, 160, 122),
    (120, 200, 200),
]  # brand sun/sky/coral + soft friends


def colorize(png: bytes, seed: int = 0, min_region_frac: float = 0.0004) -> bytes:
    gray = np.asarray(Image.open(io.BytesIO(png)).convert("L"))
    white = (gray >= 128).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    h, w = gray.shape
    out = np.full((h, w, 3), 255, dtype=np.uint8)
    out[gray < 128] = (31, 35, 51)  # brand ink instead of pure black
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    rng = np.random.default_rng(seed)
    min_area = int(h * w * min_region_frac)
    for lab in range(1, n):
        if lab in border or stats[lab, cv2.CC_STAT_AREA] < min_area:
            continue
        out[labels == lab] = PALETTE[int(rng.integers(len(PALETTE)))]
    buf = io.BytesIO()
    Image.fromarray(out, "RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# --------------------------------------------------------------------------- colour references


def _gray(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("L")


def scaled_png(png: bytes, max_h: int) -> bytes:
    """Smaller copy (keeps the aspect ratio); AI inputs and corner thumbnails need no more."""
    img: Image.Image = Image.open(io.BytesIO(png))
    img = img.convert("RGB") if img.mode not in ("L", "RGB") else img
    if img.height > max_h:
        img = img.resize((round(img.width * max_h / img.height), max_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def keep_lines(line_png: bytes, colored: bytes, max_h: int = 1200) -> bytes:
    """Put the original black lines on top of an AI-coloured version, so the colour example
    always matches the page exactly (an AI may move or add lines). Multiply blend."""
    line = _gray(scaled_png(line_png, max_h))
    color = Image.open(io.BytesIO(colored)).convert("RGB")
    color = color.resize(line.size, Image.Resampling.LANCZOS)
    lines = np.asarray(line, dtype=np.float32)[..., None] / 255.0
    out = (np.asarray(color, dtype=np.float32) * lines).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(out, "RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def print_jpeg(png: bytes, max_h: int = 600) -> bytes:
    """Compact copy for the PDF corner (1.6 in tall: 600 px is ~375 DPI). Keeps PDFs small."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if img.height > max_h:
        img = img.resize((round(img.width * max_h / img.height), max_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def colourfulness(png: bytes) -> float:
    """Share of pixels with clearly visible colour (0..1). An "AI colouring" that came back
    black & white scores ~0 and is replaced by the auto-fill."""
    hsv = np.asarray(Image.open(io.BytesIO(png)).convert("RGB").convert("HSV"))
    return float(((hsv[..., 1] > 60) & (hsv[..., 2] > 60)).mean())
