"""Letter and number tracing pages: big dashed glyphs + handwriting lines."""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import fonts
from crayonlark.print.activities.base import draw_heading
from crayonlark.print.layout import Box

# Simple, correct, kid-friendly words. Reviewed by hand.
LETTER_WORDS: dict[str, str] = {
    "A": "Apple",
    "B": "Ball",
    "C": "Cat",
    "D": "Dog",
    "E": "Egg",
    "F": "Fish",
    "G": "Goat",
    "H": "Hat",
    "I": "Igloo",
    "J": "Jam",
    "K": "Kite",
    "L": "Lion",
    "M": "Moon",
    "N": "Nest",
    "O": "Owl",
    "P": "Pig",
    "Q": "Queen",
    "R": "Rain",
    "S": "Sun",
    "T": "Tree",
    "U": "Umbrella",
    "V": "Van",
    "W": "Whale",
    "X": "Xylophone",
    "Y": "Yak",
    "Z": "Zebra",
}
NUMBER_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
]


@dataclass
class Tracing:
    target: str  # "A".."Z" or "0".."10"
    kind: str = "tracing"
    title: str = "Trace and Write"
    instructions: str = "Trace the dashed lines, then try on your own."
    has_answer: bool = False

    @property
    def is_number(self) -> bool:
        return self.target.isdigit()

    @property
    def glyphs(self) -> str:
        return self.target if self.is_number else f"{self.target}{self.target.lower()}"

    @property
    def caption(self) -> str:
        if self.is_number:
            return f"{self.target} is for {NUMBER_WORDS[int(self.target)]}"
        return f"{self.target} is for {LETTER_WORDS[self.target]}"

    def _dashed_text(self, c: Canvas, x: float, y: float, text: str, size: float) -> None:
        c.saveState()
        c.setDash(6, 5)
        c.setLineWidth(2.2)
        t = c.beginText(x, y)
        t.setFont(fonts.BODY_BOLD, size)
        t.setTextRenderMode(1)  # stroke only
        t.textLine(text)
        c.drawText(t)
        c.restoreState()

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None:
        fonts.register_fonts()
        area = draw_heading(c, box, self.title, self.instructions)
        big = min(area.h * 0.32, 200)
        w = c.stringWidth(self.glyphs, fonts.BODY_BOLD, big)
        self._dashed_text(c, area.cx - w / 2, area.top - big * 0.95, self.glyphs, big)
        c.setFont(fonts.DISPLAY_SEMI, 20)
        c.drawCentredString(area.cx, area.top - big * 1.15, self.caption)
        if self.is_number:  # counting dots
            n = int(self.target)
            for i in range(n):
                cx = area.cx + (i - (n - 1) / 2) * 26
                c.circle(cx, area.top - big * 1.15 - 30, 9, stroke=1, fill=0)

        # handwriting rows: top line, dashed midline, baseline
        rows_top = area.top - big * 1.15 - 60
        row_h = 70.0
        n_rows = int((rows_top - area.y) // (row_h + 14))
        size = row_h * 0.95
        for i in range(n_rows):
            base = rows_top - (i + 1) * (row_h + 14) + 14
            c.setLineWidth(1)
            c.setDash()
            c.line(area.x, base, area.x + area.w, base)
            c.line(area.x, base + row_h * 0.72, area.x + area.w, base + row_h * 0.72)
            c.setDash(3, 4)
            c.line(area.x, base + row_h * 0.36, area.x + area.w, base + row_h * 0.36)
            c.setDash()
            if i < n_rows - 1:  # last row empty for free writing
                gw = c.stringWidth(self.glyphs + "  ", fonts.BODY_BOLD, size * 0.72)
                reps = max(1, int(area.w // gw))
                self._dashed_text(c, area.x + 6, base, "  ".join([self.glyphs] * reps), size * 0.72)


def letters(chars: str) -> list[Tracing]:
    return [Tracing(ch.upper()) for ch in chars if ch.upper() in LETTER_WORDS]


def numbers(upto: int = 10) -> list[Tracing]:
    return [Tracing(str(n)) for n in range(1, upto + 1)]
