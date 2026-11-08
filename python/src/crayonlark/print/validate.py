"""Re-open a built PDF and check it against KDP/Etsy print rules.

Checks: page count (≥ min, even), every page = trim size, all fonts embedded, every placed
image ≥ 300 effective DPI and inside the safe margin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pikepdf

from crayonlark.print.layout import SAFE_MARGIN_IN, TRIMS_IN

PT = 72.0


@dataclass
class ValidationReport:
    path: str
    pages: int
    width_in: float
    height_in: float
    min_image_dpi: float | None
    fonts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    size_bytes: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _fonts_on_page(page: pikepdf.Page) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    res: Any = page.obj.get("/Resources", {})
    fonts: Any = res.get("/Font", {}) if res else {}
    for _, font in fonts.items():
        name = str(font.get("/BaseFont", "?"))
        subtype = str(font.get("/Subtype", ""))
        if subtype == "/Type0":
            desc = font["/DescendantFonts"][0].get("/FontDescriptor")
        else:
            desc = font.get("/FontDescriptor")
        embedded = desc is not None and any(
            k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")
        )
        out.append((name, embedded))
    return out


def _images_on_page(page: pikepdf.Page) -> list[tuple[float, float, float, float, int, int]]:
    """(x, y, w, h) in points + pixel size for each image XObject drawn on the page."""
    res: Any = page.obj.get("/Resources", {})
    xobjs: Any = res.get("/XObject", {}) if res else {}
    placed = []
    ctm_stack: list[list[float]] = []
    ctm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]

    def mul(m: list[float], n: list[float]) -> list[float]:
        a, b, c, d, e, f = m
        a2, b2, c2, d2, e2, f2 = n
        return [
            a * a2 + b * c2,
            a * b2 + b * d2,
            c * a2 + d * c2,
            c * b2 + d * d2,
            e * a2 + f * c2 + e2,
            e * b2 + f * d2 + f2,
        ]

    for instr in pikepdf.parse_content_stream(page):
        operands: Any = instr.operands
        o = str(instr.operator)
        if o == "q":
            ctm_stack.append(ctm[:])
        elif o == "Q":
            ctm = ctm_stack.pop() if ctm_stack else [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        elif o == "cm":
            ctm = mul([float(v) for v in operands], ctm)
        elif o == "Do":
            xo = xobjs.get(operands[0])
            if xo is not None and str(xo.get("/Subtype")) == "/Image":
                w_pt, h_pt = abs(ctm[0]), abs(ctm[3])
                placed.append((ctm[4], ctm[5], w_pt, h_pt, int(xo["/Width"]), int(xo["/Height"])))
    return placed


def validate_pdf(
    path: Path,
    trim: str,
    min_pages: int = 24,
    require_even: bool = True,
    min_dpi: float = 300.0,
    margin_in: float = SAFE_MARGIN_IN,
    max_bytes: int | None = None,
    check_images_in_margin: bool = True,
) -> ValidationReport:
    exp_w, exp_h = TRIMS_IN[trim]
    with pikepdf.open(path) as pdf:
        n = len(pdf.pages)
        first = pdf.pages[0].mediabox
        rep = ValidationReport(
            path=str(path),
            pages=n,
            width_in=round(float(first[2] - first[0]) / PT, 3),
            height_in=round(float(first[3] - first[1]) / PT, 3),
            min_image_dpi=None,
            size_bytes=path.stat().st_size,
        )
        if n < min_pages:
            rep.errors.append(f"{n} pages < minimum {min_pages}")
        if require_even and n % 2:
            rep.errors.append(f"odd page count {n}")
        font_names: set[str] = set()
        dpis: list[float] = []
        for i, page in enumerate(pdf.pages, start=1):
            mb = page.mediabox
            w_in, h_in = float(mb[2] - mb[0]) / PT, float(mb[3] - mb[1]) / PT
            if abs(w_in - exp_w) > 0.01 or abs(h_in - exp_h) > 0.01:
                rep.errors.append(f"page {i}: size {w_in:.3f}x{h_in:.3f} in, expected {trim}")
            for name, embedded in _fonts_on_page(page):
                font_names.add(name)
                if not embedded:
                    rep.errors.append(f"page {i}: font {name} not embedded")
            for x, y, w, h, px_w, px_h in _images_on_page(page):
                if w < 1.5 * PT and h < 1.5 * PT:
                    continue  # small decorative images (mascot) are not checked for DPI
                dpi = min(px_w / (w / PT), px_h / (h / PT))
                dpis.append(dpi)
                if dpi + 0.5 < min_dpi:
                    rep.errors.append(f"page {i}: image at {dpi:.0f} DPI < {min_dpi:.0f}")
                if check_images_in_margin:
                    m = margin_in * PT - 0.5
                    if x < m or y < m or x + w > exp_w * PT - m or y + h > exp_h * PT - m:
                        rep.errors.append(f"page {i}: image crosses the {margin_in} in margin")
        rep.fonts = sorted(font_names)
        rep.min_image_dpi = round(min(dpis), 1) if dpis else None
        if max_bytes is not None and rep.size_bytes > max_bytes:
            rep.errors.append(f"file is {rep.size_bytes / 1e6:.1f} MB > {max_bytes / 1e6:.0f} MB")
        return rep
