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
