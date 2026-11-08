"""Cleanup: raw AI/manual image → print-ready pure black & white line art at 300 DPI.

Steps
1. ImageMagick: flatten on white, grayscale, threshold to pure black/white (PBM).
2. Despeckle: drop tiny black specks (connected components smaller than `min_speck_px`).
3. potrace: vectorise to SVG (smooth curves, resolution-independent).
4. cairosvg: render the SVG to fit the 300 DPI design box (max 7.5 × 10 in), white background.
5. Threshold again → 1-bit-looking 8-bit grayscale PNG with 300 DPI metadata.
6. Optional upscaler hook (off by default; potrace already makes resolution a non-issue).
Then QA is re-run on the cleaned file by the caller.
"""

from __future__ import annotations

import io
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DPI = 300
DESIGN_BOX_IN = (7.5, 10.0)  # fits inside 8.5x11 with ≥0.5 in margins; scaled down for others


@dataclass
class CleanupResult:
    png: bytes
    svg: bytes
    width: int
    height: int
    specks_removed: int


class ToolMissing(RuntimeError):
    pass


def _magick() -> list[str]:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise ToolMissing("ImageMagick not installed (run inside the worker image)")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)


def threshold_to_pbm(src: Path, dest: Path, threshold_pct: int = 55) -> None:
    """ImageMagick: transparent → white, grayscale, hard threshold, write 1-bit PBM."""
    _run(
        [
            *_magick(),
            str(src),
            "-background",
            "white",
            "-alpha",
            "remove",
            "-alpha",
            "off",
            "-colorspace",
            "Gray",
            "-threshold",
            f"{threshold_pct}%",
            "-type",
            "Bilevel",
            str(dest),
        ]
    )


def despeckle(mask_black: np.ndarray, min_speck_px: int) -> tuple[np.ndarray, int]:
    """Remove connected black components smaller than min_speck_px. mask: 1 = black."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask_black.astype(np.uint8), connectivity=8
    )
    small = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] < min_speck_px]
    if small:
        mask_black = mask_black.copy()
        mask_black[np.isin(labels, small)] = 0
    return mask_black, len(small)


def potrace_svg(pbm: Path, dest: Path, turdsize: int = 8) -> None:
    if not shutil.which("potrace"):
        raise ToolMissing("potrace not installed (run inside the worker image)")
    _run(
        [
            "potrace",
            str(pbm),
            "-s",
            "-o",
            str(dest),
            "--turdsize",
            str(turdsize),
            "--alphamax",
            "1.0",
            "--opttolerance",
            "0.2",
        ]
    )


def render_svg(svg: bytes, box_px: tuple[int, int]) -> np.ndarray:
    """Render SVG to fit inside box_px keeping aspect ratio; returns 8-bit gray array."""
    import cairosvg

    probe = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg, output_width=200)))
    aspect = probe.height / probe.width
    bw, bh = box_px
    if bw * aspect <= bh:
        out_w, out_h = bw, round(bw * aspect)
    else:
        out_w, out_h = round(bh / aspect), bh
    png = cairosvg.svg2png(
        bytestring=svg, output_width=out_w, output_height=out_h, background_color="white"
    )
    return np.asarray(Image.open(io.BytesIO(png)).convert("L"), dtype=np.uint8)


def maybe_upscale(path: Path) -> None:
    """Optional external upscaler (e.g. Real-ESRGAN ncnn). Command from UPSCALE_COMMAND with
    {in} and {out} placeholders. Off unless UPSCALE_ENABLED=true."""
    if os.environ.get("UPSCALE_ENABLED", "false").lower() != "true":
        return
    template = os.environ.get("UPSCALE_COMMAND", "")
    if not template:
        return
    out = path.with_suffix(".up.png")
    _run(shlex.split(template.format(**{"in": str(path), "out": str(out)})))
    out.replace(path)


def clean_image(
    data: bytes, min_speck_px: int | None = None, threshold_pct: int = 55
) -> CleanupResult:
    box_px = (int(DESIGN_BOX_IN[0] * DPI), int(DESIGN_BOX_IN[1] * DPI))
    with tempfile.TemporaryDirectory(prefix="clean-") as tmp:
        t = Path(tmp)
        src = t / "in.png"
        Image.open(io.BytesIO(data)).save(src)
        maybe_upscale(src)
        pbm = t / "bw.pbm"
        threshold_to_pbm(src, pbm, threshold_pct)

        bw = np.asarray(Image.open(pbm).convert("L"))
        black = (bw < 128).astype(np.uint8)
        # specks: anything smaller than ~0.008% of the image (≈250 px on a 1536x2048 image);
        # real details like eyes are several times larger.
        speck = min_speck_px if min_speck_px is not None else max(40, int(black.size * 8e-5))
        black, removed = despeckle(black, speck)
        Image.fromarray(((1 - black) * 255).astype(np.uint8)).convert("1").save(pbm)

        svg_path = t / "out.svg"
        potrace_svg(pbm, svg_path)
        svg = svg_path.read_bytes()

    gray = render_svg(svg, box_px)
    pure = np.where(gray < 128, 0, 255).astype(np.uint8)
    img = Image.fromarray(pure, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(DPI, DPI), optimize=True)
    return CleanupResult(
        png=buf.getvalue(), svg=svg, width=img.width, height=img.height, specks_removed=removed
    )
