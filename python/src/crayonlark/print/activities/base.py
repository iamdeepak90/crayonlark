"""Common bits for no-AI activity generators. Each activity can draw itself (and its answer)
into a Box on a ReportLab canvas."""

from __future__ import annotations

from typing import Protocol

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import fonts
from crayonlark.print.layout import Box


class Activity(Protocol):
    kind: str
    title: str
    instructions: str
    has_answer: bool

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None: ...


def draw_heading(c: Canvas, box: Box, title: str, instructions: str) -> Box:
    """Draw title + one line of instructions at the top of box; return the remaining box."""
    fonts.register_fonts()
    c.setFillGray(0)
    c.setFont(fonts.DISPLAY, 28)
    c.drawCentredString(box.cx, box.top - 28, title)
    c.setFont(fonts.BODY, 14)
    c.drawCentredString(box.cx, box.top - 52, instructions)
    _, rest = box.split_top(72)
    return rest
