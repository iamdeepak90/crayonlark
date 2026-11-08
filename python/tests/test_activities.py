from __future__ import annotations

from crayonlark.print.activities import build_activities, dot2dot, maze, sudoku, tracing, wordsearch


def test_maze_is_perfect_and_solvable() -> None:
    m = maze.generate(10, 12, seed=3)
    edges = sum(len(v) for v in m.passages.values()) // 2
    assert edges == 10 * 12 - 1  # spanning tree: every cell reachable, no loops
    assert m.solution[0] == m.start and m.solution[-1] == m.end
    for a, b in zip(m.solution, m.solution[1:], strict=False):
        assert b in m.passages[a]


def test_maze_is_deterministic_per_seed() -> None:
    assert maze.generate(8, 8, seed=1).solution == maze.generate(8, 8, seed=1).solution


def test_wordsearch_words_read_correctly() -> None:
    ws = wordsearch.generate(["dino", "egg", "tail", "roar", "bones"], size=9, seed=2)
    assert sorted(ws.words) == sorted(["DINO", "EGG", "TAIL", "ROAR", "BONES"])
    for p in ws.placements:
        assert "".join(ws.grid[r][c] for r, c in p.cells()) == p.word
        assert (p.dr, p.dc) in wordsearch.EASY_DIRS  # kids' mode: no backwards/diagonal
    assert all(len(row) == 9 and all(ch.isalpha() for ch in row) for row in ws.grid)


def test_wordsearch_skips_words_longer_than_grid() -> None:
    ws = wordsearch.generate(["supercalifragilistic", "cat"], size=6)
    assert ws.words == ["CAT"]


def _valid_solution(g: list[list[int]], size: int) -> bool:
    br, bc = sudoku.BOXES[size]
    full = set(range(1, size + 1))
    rows = all(set(r) == full for r in g)
    cols = all({g[r][c] for r in range(size)} == full for c in range(size))
    boxes = all(
        {g[r][c] for r in range(r0, r0 + br) for c in range(c0, c0 + bc)} == full
        for r0 in range(0, size, br)
        for c0 in range(0, size, bc)
    )
    return rows and cols and boxes


def test_sudoku_unique_and_consistent() -> None:
    for size in (4, 6):
        s = sudoku.generate(size, seed=7)
        assert _valid_solution(s.solution, size)
        for r in range(size):
            for c in range(size):
                if s.puzzle[r][c]:
                    assert s.puzzle[r][c] == s.solution[r][c]
        assert sudoku.count_solutions([row[:] for row in s.puzzle], size) == 1
        assert sum(v == 0 for row in s.puzzle for v in row) > 0


def test_tracing_words_start_with_their_letter() -> None:
    for letter, word in tracing.LETTER_WORDS.items():
        assert word[0].upper() == letter
    assert tracing.Tracing("7").caption == "7 is for seven"
    assert len(tracing.LETTER_WORDS) == 26


def test_dot2dot_shapes_inside_unit_square() -> None:
    for name in dot2dot.SHAPES:
        pts = dot2dot.generate(name).points
        assert len(pts) >= 4
        assert all(0 <= x <= 1 and 0 <= y <= 1 for x, y in pts)


def test_build_activities_from_plan() -> None:
    acts = build_activities(
        {
            "mazes": 2,
            "wordsearch_words": ["SUN"],
            "dot2dot": ["star"],
            "tracing": "AB",
            "numbers_upto": 3,
            "sudoku": [4],
        }
    )
    kinds = [a.kind for a in acts]
    assert kinds == [
        "maze",
        "maze",
        "wordsearch",
        "dot2dot",
        "tracing",
        "tracing",
        "tracing",
        "tracing",
        "tracing",
        "sudoku",
    ]
