"""Dot-to-dot from built-in simple shapes (no AI). Answer page shows the joined outline."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import fonts
from crayonlark.print.activities.base import draw_heading
from crayonlark.print.layout import Box

Point = tuple[float, float]


def _star(n: int = 5) -> list[Point]:
    pts = []
    for i in range(n * 2):
        r = 0.5 if i % 2 == 0 else 0.21
        a = math.pi / 2 + i * math.pi / n
        pts.append((0.5 + r * math.cos(a), 0.5 + r * math.sin(a)))
    return pts


def _heart(k: int = 14) -> list[Point]:
    pts = []
    for i in range(k):
        t = math.pi * 2 * i / k + math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.5 + x / 36, 0.47 + y / 36))
    return pts


SHAPES: dict[str, tuple[str, list[Point]]] = {
    "star": ("a Star", _star()),
    "heart": ("a Heart", _heart()),
    "fish": (
        "a Fish",
        [
            (0.08, 0.5),
            (0.22, 0.66),
            (0.42, 0.74),
            (0.6, 0.7),
            (0.74, 0.58),
            (0.92, 0.72),
            (0.86, 0.5),
            (0.92, 0.28),
            (0.74, 0.42),
            (0.6, 0.3),
            (0.42, 0.26),
            (0.22, 0.34),
        ],
    ),
    "house": (
        "a House",
        [
            (0.2, 0.1),
            (0.2, 0.55),
            (0.1, 0.55),
            (0.5, 0.9),
            (0.9, 0.55),
            (0.8, 0.55),
            (0.8, 0.1),
            (0.58, 0.1),
            (0.58, 0.35),
            (0.42, 0.35),
            (0.42, 0.1),
        ],
    ),
    "kite": ("a Kite", [(0.5, 0.95), (0.78, 0.6), (0.5, 0.2), (0.22, 0.6)]),
}


@dataclass
class DotToDot:
    shape: str
    points: list[Point] = field(default_factory=list)
    kind: str = "dot2dot"
    title: str = "Dot to Dot"
    instructions: str = "Join the dots from 1 to the end. What did you draw?"
    has_answer: bool = True

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None:
        fonts.register_fonts()
        heading = self.title + (f" (Answer: {SHAPES[self.shape][0]})" if answer else "")
        area = draw_heading(c, box, heading, self.instructions).inset(30)
        side = min(area.w, area.h)
        ox, oy = area.cx - side / 2, area.y + (area.h - side) / 2
        pts = [(ox + x * side, oy + y * side) for x, y in self.points]
        if answer:
            c.setLineWidth(4)
            p = c.beginPath()
            p.moveTo(*pts[0])
            for pt in pts[1:]:
                p.lineTo(*pt)
            p.close()
            c.drawPath(p, stroke=1, fill=0)
        c.setFont(fonts.BODY_BOLD, 14)
        for i, (x, y) in enumerate(pts, start=1):
            c.circle(x, y, 4.5, stroke=0, fill=1)
            dx, dy = x - (ox + side / 2), y - (oy + side / 2)
            norm = math.hypot(dx, dy) or 1
            c.drawCentredString(x + dx / norm * 16, y + dy / norm * 16 - 5, str(i))


def generate(shape: str = "star") -> DotToDot:
    if shape not in SHAPES:
        raise ValueError(f"unknown shape {shape}; choose from {sorted(SHAPES)}")
    return DotToDot(shape, _normalise(SHAPES[shape][1]))


def _normalise(pts: list[Point], pad: float = 0.04) -> list[Point]:
    """Fit points into [pad, 1 - pad] keeping aspect ratio and centring."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    k = (1 - 2 * pad) / span
    ox = pad + ((1 - 2 * pad) - (max(xs) - min(xs)) * k) / 2
    oy = pad + ((1 - 2 * pad) - (max(ys) - min(ys)) * k) / 2
    return [(round(ox + (x - min(xs)) * k, 4), round(oy + (y - min(ys)) * k, 4)) for x, y in pts]
