"""KDP paperback full-wrap cover geometry (inches). Pure functions, unit-tested.

KDP formula (paperback):
  spine width  = page_count × per-page thickness
                 (white paper 0.002252 in, cream 0.0025 in, premium colour 0.002347 in)
  cover width  = bleed + back trim width + spine + front trim width + bleed
  cover height = bleed + trim height + bleed
  bleed        = 0.125 in on every outside edge
Spine text only when the book has at least SPINE_TEXT_MIN_PAGES pages (default 100; KDP's own
minimum is 79), with 0.0625 in clearance on each side of the spine.
The barcode area (2 × 1.2 in, bottom right of the back cover) must stay empty.
"""

from __future__ import annotations

from dataclasses import dataclass

from crayonlark.print.layout import TRIMS_IN

BLEED_IN = 0.125
SPINE_PER_PAGE_IN = {"white": 0.002252, "cream": 0.0025, "color": 0.002347}
SPINE_TEXT_CLEARANCE_IN = 0.0625
BARCODE_W_IN, BARCODE_H_IN = 2.0, 1.2
BARCODE_EDGE_IN = 0.25  # distance of the barcode box from the trim edges
TEXT_SAFE_IN = 0.375  # keep important text this far inside the trim


@dataclass(frozen=True)
class Rect:
    x: float  # from left edge of the full wrap (bleed included)
    y: float  # from TOP edge of the full wrap (CSS-friendly)
    w: float
    h: float


@dataclass(frozen=True)
class CoverGeometry:
    trim_w: float
    trim_h: float
    page_count: int
    paper: str
    spine: float
    width: float
    height: float
    back: Rect  # trim area of the back cover
    spine_rect: Rect
    front: Rect
    barcode: Rect
    spine_text: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "trim_w": self.trim_w,
            "trim_h": self.trim_h,
            "page_count": self.page_count,
            "paper": self.paper,
            "spine": round(self.spine, 4),
            "width": round(self.width, 4),
            "height": round(self.height, 4),
            "spine_text": self.spine_text,
        }


def spine_width(page_count: int, paper: str = "white") -> float:
    if page_count < 24:
        raise ValueError("KDP paperbacks need at least 24 pages")
    return page_count * SPINE_PER_PAGE_IN[paper]


def geometry(
    trim: str, page_count: int, paper: str = "white", spine_text_min_pages: int = 100
) -> CoverGeometry:
    tw, th = TRIMS_IN[trim]
    spine = spine_width(page_count, paper)
    width = BLEED_IN + tw + spine + tw + BLEED_IN
    height = BLEED_IN + th + BLEED_IN
    back = Rect(BLEED_IN, BLEED_IN, tw, th)
    spine_rect = Rect(BLEED_IN + tw, BLEED_IN, spine, th)
    front = Rect(BLEED_IN + tw + spine, BLEED_IN, tw, th)
    barcode = Rect(
        back.x + back.w - BARCODE_EDGE_IN - BARCODE_W_IN,
        back.y + back.h - BARCODE_EDGE_IN - BARCODE_H_IN,
        BARCODE_W_IN,
        BARCODE_H_IN,
    )
    return CoverGeometry(
        tw,
        th,
        page_count,
        paper,
        spine,
        width,
        height,
        back,
        spine_rect,
        front,
        barcode,
        spine_text=page_count >= spine_text_min_pages,
    )
