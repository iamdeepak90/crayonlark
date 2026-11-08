"""Kids' sudoku (4x4 with 2x2 boxes, 6x6 with 2x3 boxes) with a unique solution."""

from __future__ import annotations

import random
from dataclasses import dataclass

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print import fonts
from crayonlark.print.activities.base import draw_heading
from crayonlark.print.layout import Box

BOXES = {4: (2, 2), 6: (2, 3)}
Grid = list[list[int]]


@dataclass
class Sudoku:
    size: int
    puzzle: Grid
    solution: Grid
    kind: str = "sudoku"
    title: str = "Number Puzzle"
    instructions: str = ""
    has_answer: bool = True

    def __post_init__(self) -> None:
        br, bc = BOXES[self.size]
        self.instructions = (
            f"Fill in 1 to {self.size}. Each row, column and {br}x{bc} box uses every number once."
        )

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None:
        fonts.register_fonts()
        area = draw_heading(c, box, self.title + (" (Answer)" if answer else ""), self.instructions)
        side = min(area.w, area.h) * 0.85
        cell = side / self.size
        ox, oy = area.cx - side / 2, area.y + (area.h - side) / 2
        br, bc = BOXES[self.size]
        for i in range(self.size + 1):
            c.setLineWidth(4 if i % bc == 0 else 1.2)
            c.line(ox + i * cell, oy, ox + i * cell, oy + side)
            c.setLineWidth(4 if i % br == 0 else 1.2)
            c.line(ox, oy + i * cell, ox + side, oy + i * cell)
        c.setFont(fonts.DISPLAY_SEMI, cell * 0.55)
        grid = self.solution if answer else self.puzzle
        for r in range(self.size):
            for col in range(self.size):
                v = grid[r][col]
                if v:
                    c.setFillGray(0 if self.puzzle[r][col] else 0.45)
                    c.drawCentredString(
                        ox + col * cell + cell / 2, oy + side - r * cell - cell * 0.7, str(v)
                    )
        c.setFillGray(0)


def _valid(g: Grid, r: int, c: int, v: int, size: int) -> bool:
    br, bc = BOXES[size]
    if v in g[r] or any(g[i][c] == v for i in range(size)):
        return False
    r0, c0 = r - r % br, c - c % bc
    return all(g[i][j] != v for i in range(r0, r0 + br) for j in range(c0, c0 + bc))


def count_solutions(g: Grid, size: int, limit: int = 2) -> int:
    for r in range(size):
        for c in range(size):
            if g[r][c] == 0:
                total = 0
                for v in range(1, size + 1):
                    if _valid(g, r, c, v, size):
                        g[r][c] = v
                        total += count_solutions(g, size, limit - total)
                        g[r][c] = 0
                        if total >= limit:
                            return total
                return total
    return 1


def _full(size: int, rng: random.Random) -> Grid:
    g: Grid = [[0] * size for _ in range(size)]

    def fill(pos: int) -> bool:
        if pos == size * size:
            return True
        r, c = divmod(pos, size)
        vals = list(range(1, size + 1))
        rng.shuffle(vals)
        for v in vals:
            if _valid(g, r, c, v, size):
                g[r][c] = v
                if fill(pos + 1):
                    return True
                g[r][c] = 0
        return False

    fill(0)
    return g


def generate(size: int = 4, seed: int = 0, holes: int | None = None) -> Sudoku:
    if size not in BOXES:
        raise ValueError("size must be 4 or 6")
    rng = random.Random(seed)
    solution = _full(size, rng)
    puzzle = [row[:] for row in solution]
    target = holes if holes is not None else (8 if size == 4 else 18)
    cells = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(cells)
    removed = 0
    for r, c in cells:
        if removed >= target:
            break
        keep = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions([row[:] for row in puzzle], size) != 1:
            puzzle[r][c] = keep
        else:
            removed += 1
    return Sudoku(size, puzzle, solution)
