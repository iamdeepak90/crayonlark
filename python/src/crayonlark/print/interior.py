"""KDP interior PDF builder (no bleed, black & white).

Page order (page 1 is a right-hand page):
  1 title · 2 copyright · 3 "This book belongs to" · 4 blank · [5 colour test · 6 blank]
  designs: each on a right-hand page with a blank back
  activities (start on a right page, consecutive)
  answer keys (start on a right page, two answers per page)
  thank-you / review (right) · "More Crayonlark books" (left)
  pad to an even page count; must be ≥ 24 pages.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import brand, fonts
from crayonlark.print.activities.base import Activity
from crayonlark.print.layout import Box, page_size, safe_box

MIN_PAGES = 24


@dataclass
class InteriorSpec:
    title: str
    subtitle: str = ""
    trim: str = "8.5x11"
    year: int = 2026
    designs: Sequence[Path] = ()
    activities: Sequence[Activity] = ()
    include_color_test: bool = True
    ai_interior_images: bool = True
    more_books: Sequence[str] = ()
    blank_backs: bool = True  # KDP: True. Etsy printables: False


@dataclass
class PlannedPage:
    number: int
    kind: str
    refs: list[int] = field(default_factory=list)  # design / activity indexes

    @property
    def side(self) -> str:
        return "right" if self.number % 2 == 1 else "left"


class PageCountError(ValueError):
    pass


def plan_pages(spec: InteriorSpec, min_pages: int = MIN_PAGES) -> list[PlannedPage]:
    pages: list[PlannedPage] = []

    def add(kind: str, refs: list[int] | None = None) -> None:
        pages.append(PlannedPage(len(pages) + 1, kind, refs or []))

    def ensure_right() -> None:
        if len(pages) % 2 == 1:  # next page would be even = left
            add("blank")

    add("title")
    add("copyright")
    add("belongs_to")
    add("blank")
    if spec.include_color_test:
        add("color_test")
        add("blank")
    for i in range(len(spec.designs)):
        if spec.blank_backs:
            ensure_right()
        add("design", [i])
        if spec.blank_backs:
            add("blank")
    if spec.activities:
        ensure_right()
        for i in range(len(spec.activities)):
            add("activity", [i])
    answers = [i for i, a in enumerate(spec.activities) if a.has_answer]
    if answers:
        ensure_right()
        for j in range(0, len(answers), 2):
            add("answers", answers[j : j + 2])
    ensure_right()
    add("thank_you")
    add("more_books")
    if len(pages) % 2 == 1:
        add("blank")
    if len(pages) < min_pages:
        raise PageCountError(
            f"interior has {len(pages)} pages; KDP needs at least {min_pages}. Add designs."
        )
    return pages


# --------------------------------------------------------------------------- drawing


def _centered(c: Canvas, box: Box, y: float, text: str, font: str, size: float) -> None:
    c.setFont(font, size)
    while c.stringWidth(text, font, size) > box.w and size > 8:
        size -= 1
        c.setFont(font, size)
    c.drawCentredString(box.cx, y, text)


def _mascot(c: Canvas, x: float, y: float, w: float) -> None:
    c.drawImage(
        ImageReader(io.BytesIO(brand.mascot_png(gray=True))),
        x,
        y,
        w,
        w,
        mask=None,
        preserveAspectRatio=True,
    )


def draw_design(c: Canvas, box: Box, image: Path) -> None:
    with Image.open(image) as im:
        aspect = im.height / im.width
    target = box.fit(aspect)
    c.drawImage(str(image), target.x, target.y, target.w, target.h)


def _title(c: Canvas, box: Box, spec: InteriorSpec) -> None:
    _centered(c, box, box.top - 2.2 * inch, spec.title, fonts.DISPLAY, 40)
    if spec.subtitle:
        _centered(c, box, box.top - 2.8 * inch, spec.subtitle, fonts.BODY, 18)
    _mascot(c, box.cx - 1.25 * inch, box.y + box.h * 0.25, 2.5 * inch)
    _centered(c, box, box.y + 0.4 * inch, brand.NAME, fonts.DISPLAY_SEMI, 20)


def _copyright(c: Canvas, box: Box, spec: InteriorSpec) -> None:
    lines = [
        f"© {spec.year} Crayonlark. All rights reserved.",
        "No part of this book may be copied or shared without permission,",
        "except for personal use of the printed pages by the buyer.",
    ]
    if spec.ai_interior_images:
        lines += ["", "Illustrations were created with AI tools and edited by Crayonlark."]
    lines += ["", brand.SITE]
    c.setFont(fonts.BODY, 11)
    y = box.y + 2.0 * inch
    for line in lines:
        c.drawCentredString(box.cx, y, line)
        y -= 16


def _belongs_to(c: Canvas, box: Box) -> None:
    _centered(c, box, box.top - 2.0 * inch, "This book belongs to", fonts.DISPLAY, 38)
    c.setLineWidth(3)
    c.roundRect(box.x + 0.5 * inch, box.top - 4.0 * inch, box.w - 1.0 * inch, 1.3 * inch, 24)
    _mascot(c, box.cx - 1.5 * inch, box.y + 0.6 * inch, 3.0 * inch)


def _color_test(c: Canvas, box: Box) -> None:
    _centered(c, box, box.top - 0.8 * inch, "Test Your Colors", fonts.DISPLAY, 34)
    _centered(
        c,
        box,
        box.top - 1.2 * inch,
        "Try your crayons, pencils and markers here first.",
        fonts.BODY,
        14,
    )
    c.setLineWidth(2.5)
    cols, rows = 4, 5
    size = min(box.w / cols, (box.h - 1.8 * inch) / rows) * 0.78
    gap_x = box.w / cols
    gap_y = (box.h - 1.8 * inch) / rows
    for r in range(rows):
        for col in range(cols):
            cx = box.x + gap_x * (col + 0.5)
            cy = box.y + gap_y * (r + 0.5)
            c.circle(cx, cy, size / 2) if (r + col) % 2 == 0 else c.roundRect(
                cx - size / 2, cy - size / 2, size, size, 14
            )


def _thank_you(c: Canvas, box: Box) -> None:
    _centered(c, box, box.top - 2.0 * inch, "Thank you for coloring with us!", fonts.DISPLAY, 30)
    msg = [
        "We are a tiny family publisher and we read every review.",
        "If you enjoyed this book, an honest review on Amazon",
        "helps other families find it. Thank you!",
    ]
    c.setFont(fonts.BODY, 15)
    y = box.top - 2.8 * inch
    for line in msg:
        c.drawCentredString(box.cx, y, line)
        y -= 22
    _mascot(c, box.cx - 1.25 * inch, box.y + 0.8 * inch, 2.5 * inch)


def _more_books(c: Canvas, box: Box, spec: InteriorSpec) -> None:
    _centered(c, box, box.top - 1.2 * inch, "More Crayonlark Books", fonts.DISPLAY, 32)
    c.setFont(fonts.BODY_BOLD, 16)
    y = box.top - 2.2 * inch
    for title in list(spec.more_books)[:10]:
        c.drawCentredString(box.cx, y, f"• {title}")
        y -= 28
    _centered(c, box, box.y + 1.0 * inch, f"Find them all at {brand.SITE}", fonts.BODY_BOLD, 16)


def draw_answers(c: Canvas, box: Box, acts: Sequence[Activity]) -> None:
    half = box.h / 2
    for k, act in enumerate(acts):
        sub = Box(box.x, box.top - half * (k + 1), box.w, half - 6)
        c.saveState()
        act.draw(c, sub, answer=True)
        c.restoreState()


def render(spec: InteriorSpec, out: Path, min_pages: int = MIN_PAGES) -> list[PlannedPage]:
    fonts.register_fonts()
    plan = plan_pages(spec, min_pages)
    total = len(plan)
    c = Canvas(
        str(out),
        pagesize=page_size(spec.trim),
        pageCompression=1,
        initialFontName=fonts.BODY,
        initialFontSize=12,
    )
    c.setTitle(spec.title)
    c.setAuthor("Crayonlark")
    c.setCreator("Crayonlark print engine")
    for page in plan:
        box = safe_box(spec.trim, page.number, total, mirror=spec.blank_backs)
        c.setFillGray(0)
        c.setStrokeGray(0)
        match page.kind:
            case "title":
                _title(c, box, spec)
            case "copyright":
                _copyright(c, box, spec)
            case "belongs_to":
                _belongs_to(c, box)
            case "color_test":
                _color_test(c, box)
            case "design":
                draw_design(c, box, Path(spec.designs[page.refs[0]]))
            case "activity":
                spec.activities[page.refs[0]].draw(c, box)
            case "answers":
                draw_answers(c, box, [spec.activities[i] for i in page.refs])
            case "thank_you":
                _thank_you(c, box)
            case "more_books":
                _more_books(c, box, spec)
            case "blank":
                pass
        c.showPage()
    c.save()
    return plan
