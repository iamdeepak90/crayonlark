"""No-AI activity generators: mazes, word searches, dot-to-dot, tracing, sudoku."""

from __future__ import annotations

from typing import Any

from crayonlark.print.activities import dot2dot, maze, sudoku, tracing, wordsearch
from crayonlark.print.activities.base import Activity

__all__ = ["Activity", "build_activities"]


def build_activities(plan: dict[str, Any], seed: int = 1) -> list[Activity]:
    """Create activities from a plan like:
    {"mazes": 2, "wordsearch_words": ["DINO", ...], "dot2dot": ["star"], "tracing": "ABC",
     "numbers_upto": 0, "sudoku": [4, 6]}
    """
    acts: list[Activity] = []
    for i in range(int(plan.get("mazes", 0))):
        acts.append(maze.generate(8 + 2 * i, 10 + 2 * i, seed=seed + i))
    words = plan.get("wordsearch_words") or []
    if words:
        acts.append(
            wordsearch.generate(list(words), size=int(plan.get("wordsearch_size", 10)), seed=seed)
        )
    for shape in plan.get("dot2dot", []):
        acts.append(dot2dot.generate(shape))
    acts.extend(tracing.letters(str(plan.get("tracing", ""))))
    if int(plan.get("numbers_upto", 0)):
        acts.extend(tracing.numbers(int(plan["numbers_upto"])))
    for i, size in enumerate(plan.get("sudoku", [])):
        acts.append(sudoku.generate(int(size), seed=seed + 100 + i))
    return acts
