"""Word search with answer key. Kids' mode only places words → and ↓ (no backwards)."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import fonts
from crayonlark.print.activities.base import draw_heading
from crayonlark.print.layout import Box

EASY_DIRS = [(1, 0), (0, 1)]
HARD_DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class Placement:
    word: str
    row: int
    col: int
    dr: int
    dc: int

    def cells(self) -> list[tuple[int, int]]:
        return [(self.row + i * self.dr, self.col + i * self.dc) for i in range(len(self.word))]


@dataclass
class WordSearch:
    size: int
    grid: list[list[str]]
    placements: list[Placement] = field(default_factory=list)
    kind: str = "wordsearch"
    title: str = "Word Search"
    instructions: str = "Find and circle the words below."
    has_answer: bool = True

    @property
    def words(self) -> list[str]:
        return [p.word for p in self.placements]

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None:
        fonts.register_fonts()
        area = draw_heading(c, box, self.title + (" (Answer)" if answer else ""), self.instructions)
        list_h = 26 * ((len(self.words) + 2) // 3) + 20
        grid_area = Box(area.x, area.y + list_h, area.w, area.h - list_h)
        cell = min(grid_area.w, grid_area.h) / self.size
        ox = grid_area.cx - cell * self.size / 2
        oy = grid_area.top - 6
        hits = {rc for p in self.placements for rc in p.cells()} if answer else set()
        c.setFont(fonts.BODY_BOLD, cell * 0.55)
        for r in range(self.size):
            for col in range(self.size):
                x = ox + col * cell + cell / 2
                y = oy - r * cell - cell * 0.7
                if (r, col) in hits:
                    c.setFillGray(0.82)
                    c.circle(x, y + cell * 0.18, cell * 0.42, stroke=0, fill=1)
                    c.setFillGray(0)
                c.drawCentredString(x, y, self.grid[r][col])
        c.setLineWidth(2)
        c.roundRect(
            ox - 6, oy - cell * self.size - 6, cell * self.size + 12, cell * self.size + 12, 10
        )
        c.setFont(fonts.BODY_BOLD, 15)
        col_w = area.w / 3
        for i, w in enumerate(self.words):
            cx = area.x + col_w * (i % 3) + col_w / 2
            cy = area.y + list_h - 22 - 26 * (i // 3)
            c.drawCentredString(cx, cy, w)


def generate(words: list[str], size: int = 10, seed: int = 0, hard: bool = False) -> WordSearch:
    rng = random.Random(seed)
    dirs = HARD_DIRS if hard else EASY_DIRS
    clean = sorted({w.upper().replace(" ", "") for w in words if w.strip()}, key=len, reverse=True)
    clean = [w for w in clean if w.isalpha() and len(w) <= size]
    grid: list[list[str]] = [["" for _ in range(size)] for _ in range(size)]
    placements: list[Placement] = []
    for word in clean:
        for _ in range(300):
            dr, dc = rng.choice(dirs)
            r = rng.randrange(size)
            col = rng.randrange(size)
            p = Placement(word, r, col, dr, dc)
            cells = p.cells()
            if not all(0 <= rr < size and 0 <= cc < size for rr, cc in cells):
                continue
            if all(grid[rr][cc] in ("", word[i]) for i, (rr, cc) in enumerate(cells)):
                for i, (rr, cc) in enumerate(cells):
                    grid[rr][cc] = word[i]
                placements.append(p)
                break
    for r in range(size):
        for col in range(size):
            if not grid[r][col]:
                grid[r][col] = rng.choice(string.ascii_uppercase)
    return WordSearch(size, grid, placements)
