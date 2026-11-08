"""Page geometry helpers shared by interior, Etsy PDFs and activities. Units: PDF points."""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.units import inch

TRIMS_IN: dict[str, tuple[float, float]] = {
    "8.5x11": (8.5, 11.0),
    "8.5x8.5": (8.5, 8.5),
    "letter": (8.5, 11.0),
    "a4": (8.2677, 11.6929),
}


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def top(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    def inset(self, d: float) -> Box:
        return Box(self.x + d, self.y + d, self.w - 2 * d, self.h - 2 * d)

    def split_top(self, h: float) -> tuple[Box, Box]:
        """(top strip of height h, remaining box below)."""
        return Box(self.x, self.top - h, self.w, h), Box(self.x, self.y, self.w, self.h - h)

    def fit(self, aspect_h_over_w: float) -> Box:
        """Largest centred box with the given aspect ratio inside this box."""
        if self.w * aspect_h_over_w <= self.h:
            w, h = self.w, self.w * aspect_h_over_w
        else:
            w, h = self.h / aspect_h_over_w, self.h
        return Box(self.x + (self.w - w) / 2, self.y + (self.h - h) / 2, w, h)


def page_size(trim: str) -> tuple[float, float]:
    w, h = TRIMS_IN[trim]
    return w * inch, h * inch


def kdp_inside_margin_in(page_count: int) -> float:
    """KDP minimum gutter (inside margin) by page count, no-bleed paperback."""
    if page_count <= 150:
        return 0.375
    if page_count <= 300:
        return 0.5
    if page_count <= 500:
        return 0.625
    if page_count <= 700:
        return 0.75
    return 0.875


SAFE_MARGIN_IN = 0.5  # our house minimum on every side (KDP minimum outside is 0.25)


def safe_box(trim: str, page_number: int, page_count: int, mirror: bool = True) -> Box:
    """Printable area for a page. Odd pages are right-hand (recto): gutter on the left."""
    w, h = page_size(trim)
    inside = max(SAFE_MARGIN_IN, kdp_inside_margin_in(page_count)) * inch
    outside = SAFE_MARGIN_IN * inch
    if not mirror:
        return Box(outside, outside, w - 2 * outside, h - 2 * outside)
    left = inside if page_number % 2 == 1 else outside
    right = outside if page_number % 2 == 1 else inside
    return Box(left, outside, w - left - right, h - 2 * outside)
