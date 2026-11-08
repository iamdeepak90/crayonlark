"""Rectangular mazes (recursive backtracker) with BFS solution for the answer key."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from reportlab.pdfgen.canvas import Canvas

from crayonlark.print.activities.base import draw_heading
from crayonlark.print.layout import Box

Cell = tuple[int, int]


@dataclass
class Maze:
    cols: int
    rows: int
    # passages[(c, r)] = set of neighbour cells reachable without a wall
    passages: dict[Cell, set[Cell]] = field(default_factory=dict)
    solution: list[Cell] = field(default_factory=list)
    kind: str = "maze"
    title: str = "Find the Way!"
    instructions: str = "Draw a line from START to FINISH."
    has_answer: bool = True

    @property
    def start(self) -> Cell:
        return (0, 0)

    @property
    def end(self) -> Cell:
        return (self.cols - 1, self.rows - 1)

    def draw(self, c: Canvas, box: Box, answer: bool = False) -> None:
        area = draw_heading(c, box, self.title + (" (Answer)" if answer else ""), self.instructions)
        area = area.inset(18)
        cell = min(area.w / self.cols, (area.h - 30) / self.rows)
        ox = area.cx - cell * self.cols / 2
        oy = area.y + 15 + (area.h - 30 - cell * self.rows) / 2

        def xy(col: int, row: int) -> tuple[float, float]:  # row 0 at top
            return ox + col * cell, oy + (self.rows - row) * cell

        c.setLineWidth(max(2.0, cell * 0.12))
        c.setLineCap(1)
        c.setStrokeGray(0)
        for r in range(self.rows):
            for col in range(self.cols):
                x, y = xy(col, r)
                nbrs = self.passages.get((col, r), set())
                # top wall (entrance gap above START)
                if (r == 0 and (col, r) != self.start) or (r > 0 and (col, r - 1) not in nbrs):
                    c.line(x, y, x + cell, y)
                # left wall
                if col == 0 or (col - 1, r) not in nbrs:
                    c.line(x, y, x, y - cell)
        # outer right and bottom borders (exit gap below FINISH)
        rx, _ = xy(self.cols, 0)
        c.line(rx, xy(0, 0)[1], rx, xy(0, self.rows)[1])
        for col in range(self.cols):
            if (col, self.rows - 1) != self.end:
                x, y = xy(col, self.rows)
                c.line(x, y, x + cell, y)
        from crayonlark.print import fonts

        c.setFont(fonts.DISPLAY_SEMI, 12)
        sx, sy = xy(0, 0)
        c.drawString(sx, sy + 6, "START")
        ex, ey = xy(self.cols - 1, self.rows - 1)
        c.drawRightString(ex + cell, ey - cell - 16, "FINISH")
        if answer and self.solution:
            c.setStrokeGray(0.35)
            c.setLineWidth(max(2.0, cell * 0.25))
            c.setDash(1, 0)
            pts = [(xy(col, r)[0] + cell / 2, xy(col, r)[1] - cell / 2) for col, r in self.solution]
            p = c.beginPath()
            p.moveTo(*pts[0])
            for pt in pts[1:]:
                p.lineTo(*pt)
            c.drawPath(p, stroke=1, fill=0)
            c.setStrokeGray(0)


def generate(cols: int = 10, rows: int = 12, seed: int = 0) -> Maze:
    rng = random.Random(seed)
    maze = Maze(cols, rows, {(x, y): set() for x in range(cols) for y in range(rows)})
    stack: list[Cell] = [(0, 0)]
    seen = {(0, 0)}
    while stack:
        x, y = stack[-1]
        options = [
            (x + dx, y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= x + dx < cols and 0 <= y + dy < rows and (x + dx, y + dy) not in seen
        ]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        maze.passages[(x, y)].add(nxt)
        maze.passages[nxt].add((x, y))
        seen.add(nxt)
        stack.append(nxt)
    maze.solution = solve(maze)
    return maze


def solve(maze: Maze) -> list[Cell]:
    prev: dict[Cell, Cell | None] = {maze.start: None}
    q: deque[Cell] = deque([maze.start])
    while q:
        cur = q.popleft()
        if cur == maze.end:
            break
        for n in maze.passages[cur]:
            if n not in prev:
                prev[n] = cur
                q.append(n)
    path: list[Cell] = []
    node: Cell | None = maze.end
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return path[::-1]
