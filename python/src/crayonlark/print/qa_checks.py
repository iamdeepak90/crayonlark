"""Python image QA for coloring pages (no AI): resolution, grey pixels, line thickness,
black fill, frame/border and text detection.

Scores are 0-100 per check; `recommendation` is "keep" unless a hard check fails.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import asdict, dataclass, field
from typing import Any

import cv2
import numpy as np
from PIL import Image

PRINT_LONG_SIDE_PX = 3000  # long side of a full page design at 300 DPI (10 in)


@dataclass
class QAThresholds:
    min_side_px: int = 1000
    max_grey_ratio: float = 0.06
    max_black_fill: float = 0.35
    min_line_px: float = 4.0  # stroke width at print size (300 DPI); ~0.34 mm
    max_text_chars: int = 0
    max_border_ratio: float = 0.6

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> QAThresholds:
        if not d:
            return cls()
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class QAResult:
    width: int
    height: int
    grey_ratio: float
    black_fill: float
    line_px_at_print: float
    border_ratio: float
    text_chars: int
    text_found: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def recommendation(self) -> str:
        return "reject" if self.failures else "keep"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = self.recommendation
        return d


def load_gray(data: bytes) -> np.ndarray:
    """Decode any image to 8-bit grayscale, flattening transparency onto white."""
    img: Image.Image = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return np.asarray(img.convert("L"), dtype=np.uint8)


def grey_ratio(gray: np.ndarray) -> float:
    """Share of pixels that are neither near-white nor near-black (shading, gradients)."""
    mid = (gray > 40) & (gray < 215)
    return float(mid.mean())


def black_fill(gray: np.ndarray) -> float:
    return float((gray < 128).mean())


def line_thickness_px(gray: np.ndarray) -> float:
    """Median stroke width in pixels, estimated as 2 * area / perimeter of dark regions.

    For long thin strokes the perimeter is ~2 × length, so area / (perimeter / 2) ≈ width.
    """
    mask = (gray < 128).astype(np.uint8)
    if mask.sum() == 0:
        return 0.0
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    if perimeter == 0:
        return 0.0
    return float(2.0 * mask.sum() / perimeter)


def border_ratio(gray: np.ndarray, band: float = 0.03) -> float:
    """How much of a thin band near each edge is dark. A drawn frame gives ~1.0 on all sides."""
    h, w = gray.shape
    bh, bw = max(2, int(h * band)), max(2, int(w * band))
    dark = gray < 128
    sides = [
        dark[:bh, :].any(axis=0).mean(),
        dark[-bh:, :].any(axis=0).mean(),
        dark[:, :bw].any(axis=1).mean(),
        dark[:, -bw:].any(axis=1).mean(),
    ]
    return float(min(sides))  # all four sides must be covered to count as a frame


def detect_text(gray: np.ndarray) -> tuple[int, str]:
    """Count confident alphabetic words found by Tesseract. Returns (chars, words)."""
    if shutil.which("tesseract") is None:
        return 0, ""
    import pytesseract

    h, w = gray.shape
    scale = 1600 / max(h, w)
    small = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    data = pytesseract.image_to_data(small, config="--psm 11", output_type=pytesseract.Output.DICT)
    words = [
        t.strip()
        for t, conf in zip(data["text"], data["conf"], strict=False)
        if t.strip().isalpha() and len(t.strip()) >= 3 and float(conf) >= 75
    ]
    return sum(len(x) for x in words), " ".join(words)


def run_checks(
    data: bytes, thresholds: QAThresholds | None = None, check_text: bool = True
) -> QAResult:
    th = thresholds or QAThresholds()
    gray = load_gray(data)
    h, w = gray.shape
    line_px = line_thickness_px(gray) * PRINT_LONG_SIDE_PX / max(h, w)
    chars, words = detect_text(gray) if check_text else (0, "")
    r = QAResult(
        width=w,
        height=h,
        grey_ratio=round(grey_ratio(gray), 4),
        black_fill=round(black_fill(gray), 4),
        line_px_at_print=round(line_px, 2),
        border_ratio=round(border_ratio(gray), 3),
        text_chars=chars,
        text_found=words,
    )
    if min(w, h) < th.min_side_px:
        r.failures.append(f"resolution {w}x{h} below {th.min_side_px}px")
    if h < w:
        r.warnings.append("landscape image; pages are portrait")
    if r.grey_ratio > th.max_grey_ratio:
        r.warnings.append(f"grey/shading {r.grey_ratio:.1%} (cleanup will threshold it)")
    if r.grey_ratio > th.max_grey_ratio * 4:
        r.failures.append(f"heavy shading {r.grey_ratio:.1%}")
    if r.black_fill > th.max_black_fill:
        r.failures.append(f"too much solid black {r.black_fill:.1%}")
    if r.black_fill < 0.01:
        r.failures.append("almost empty image")
    if 0 < r.line_px_at_print < th.min_line_px:
        r.failures.append(f"lines too thin ({r.line_px_at_print}px at 300 DPI)")
    if r.border_ratio > th.max_border_ratio:
        r.warnings.append("looks like it has a frame/border")
    if r.text_chars > th.max_text_chars:
        r.failures.append(f"text detected: {words[:60]}")

    score = 100.0
    score -= min(30.0, r.grey_ratio * 300)
    score -= max(0.0, (r.black_fill - 0.2) * 150)
    score -= 10.0 * len(r.warnings) + 35.0 * len(r.failures)
    r.score = round(max(0.0, min(100.0, score)), 1)
    return r
