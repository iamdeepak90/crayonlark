"""Etsy printable PDFs: US Letter and A4 versions of each product, single-sided, with a
cover page and a license page ("personal and single classroom use only"). Max 20 MB each."""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import brand, fonts
from crayonlark.print.activities.base import Activity
from crayonlark.print.interior import draw_answers, draw_design
from crayonlark.print.layout import Box, page_size, safe_box
from crayonlark.print.validate import ValidationReport, validate_pdf

ETSY_MAX_BYTES = 20 * 1024 * 1024
PAPER_SIZES = ("letter", "a4")


@dataclass
class EtsyProduct:
    slug: str  # file name stem, e.g. "dinosaur-coloring-pages-full"
    title: str
    designs: Sequence[Path] = ()
    activities: Sequence[Activity] = ()
    ai_artwork: bool = True


def _cover(c: Canvas, box: Box, product: EtsyProduct) -> None:
    c.setFillColor(brand.COLORS["ink"])
    c.setFont(fonts.DISPLAY, 34)
    size = 34.0
    while c.stringWidth(product.title, fonts.DISPLAY, size) > box.w and size > 14:
        size -= 1
    c.setFont(fonts.DISPLAY, size)
    c.drawCentredString(box.cx, box.top - 1.6 * inch, product.title)
    c.setFont(fonts.BODY, 16)
    n_d, n_a = len(product.designs), len(product.activities)
    parts = [f"{n_d} coloring pages" if n_d else "", f"{n_a} activity pages" if n_a else ""]
    c.drawCentredString(box.cx, box.top - 2.1 * inch, " + ".join(p for p in parts if p))
    logo = ImageReader(io.BytesIO(brand.mascot_png(gray=False)))
    c.drawImage(logo, box.cx - 1.5 * inch, box.y + box.h * 0.3, 3 * inch, 3 * inch, mask="auto")
    c.setFont(fonts.DISPLAY_SEMI, 18)
    c.drawCentredString(box.cx, box.y + 0.9 * inch, f"{brand.NAME} · {brand.TAGLINE}")
    c.setFont(fonts.BODY, 12)
    c.drawCentredString(
        box.cx, box.y + 0.55 * inch, "Printable PDF · personal and single classroom use only"
    )


def _license(c: Canvas, box: Box, ai_artwork: bool) -> None:
    c.setFillColor(brand.COLORS["ink"])
    c.setFont(fonts.DISPLAY, 30)
    c.drawCentredString(box.cx, box.top - 0.8 * inch, "License & Printing Tips")
    y = box.top - 1.5 * inch
    ai_line = brand.AI_LICENSE_LINE if ai_artwork else brand.NON_AI_LICENSE_LINE
    for line in [*brand.LICENSE_LINES[:-1], ai_line, brand.LICENSE_LINES[-1]]:
        bold = line.endswith(":")
        c.setFont(fonts.BODY_BOLD if bold else fonts.BODY, 13)
        c.drawString(box.x + 0.3 * inch, y, line)
        y -= 20
    y -= 16
    c.setFont(fonts.BODY_BOLD, 13)
    c.drawString(box.x + 0.3 * inch, y, "Printing tips:")
    c.setFont(fonts.BODY, 13)
    for tip in (
        "Print at 100% / 'Actual size' (not 'Fit to page') for the best lines.",
        "Use thicker paper (cardstock) for markers.",
        "Choose the Letter file in the US/Canada and the A4 file elsewhere.",
    ):
        y -= 20
        c.drawString(box.x + 0.3 * inch, y, f"• {tip}")


def render(product: EtsyProduct, paper: str, out: Path) -> ValidationReport:
    fonts.register_fonts()
    c = Canvas(
        str(out),
        pagesize=page_size(paper),
        pageCompression=1,
        initialFontName=fonts.BODY,
        initialFontSize=12,
    )
    c.setTitle(product.title)
    c.setAuthor("Crayonlark")
    pages = 0

    def box() -> Box:
        return safe_box(paper, 1, 24, mirror=False)

    _cover(c, box(), product)
    c.showPage()
    _license(c, box(), product.ai_artwork)
    c.showPage()
    pages += 2
    for d in product.designs:
        draw_design(c, box(), Path(d))
        c.showPage()
        pages += 1
    for a in product.activities:
        a.draw(c, box())
        c.showPage()
        pages += 1
    answers = [a for a in product.activities if a.has_answer]
    for j in range(0, len(answers), 2):
        draw_answers(c, box(), answers[j : j + 2])
        c.showPage()
        pages += 1
    c.save()
    return validate_pdf(out, paper, min_pages=1, require_even=False, max_bytes=ETSY_MAX_BYTES)


def render_both(product: EtsyProduct, out_dir: Path) -> dict[str, ValidationReport]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        paper: render(product, paper, out_dir / f"{product.slug}-{paper}.pdf")
        for paper in PAPER_SIZES
    }
