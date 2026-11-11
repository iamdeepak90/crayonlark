"""Runtime settings in the `settings` table, falling back to DEFAULTS below.

Env vars hold secrets and infra. Only a few rows are written by the owner (the monthly budget,
the Autopilot switch); the rest are code defaults that a stored row can still override.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.core.db import session_scope
from crayonlark.core.models import Setting

HOUSE_PROMPT_TEMPLATE = (
    "Black and white coloring page for young children: {scene}. "
    "Thick bold black outlines, simple large shapes, pure white background, "
    "no shading, no grey, no gradients, no text, no letters, no border, no frame, "
    "cute friendly style, centered single subject, portrait orientation, "
    "plenty of empty space inside shapes for coloring."
)

DEFAULTS: dict[str, Any] = {
    # Models are fixed in code (providers/llm/base.py AUTO_MODELS, providers/image/base.py):
    # they follow the keys you add. A stored value still wins (tests, emergencies).
    "agent_models": {},
    "image_provider": None,
    "house_prompt_template": HOUSE_PROMPT_TEMPLATE,
    "blocklist_extra": [],  # added on top of assets/blocklist.txt
    "images_per_book": {"min": 25, "max": 50},
    "concepts_per_niche": 40,  # ~25 pictures are kept per book; unused prompts are wasted text
    "autopilot": {"enabled": True},  # the owner only approves; switch off on the Today page
    "pinterest": {"pins_per_day": 4, "start_hour_utc": 13, "end_hour_utc": 23},
    "free_printable_key": None,  # outputs/free/sample-pack.pdf once built
    "qa_thresholds": {
        "min_side_px": 840,  # potrace re-renders at 300 DPI; 1024x1536 API output is fine
        "max_grey_ratio": 0.06,
        "max_black_fill": 0.35,
        "min_line_px": 3.0,
        "max_text_chars": 0,
    },
}


def get(key: str, session: Session | None = None) -> Any:
    def _get(s: Session) -> Any:
        row = s.get(Setting, key)
        return row.value if row is not None else DEFAULTS.get(key)

    if session is not None:
        return _get(session)
    with session_scope() as s:
        return _get(s)


def set_value(key: str, value: Any, actor: str, session: Session) -> None:
    from crayonlark.core.audit import record

    row = session.get(Setting, key)
    old = row.value if row else None
    if row is None:
        session.add(Setting(key=key, value=value, updated_by=actor))
    else:
        row.value = value
        row.updated_by = actor
    record(session, actor, "settings.update", "setting", key, {"old": old, "new": value})


def all_settings(session: Session) -> dict[str, Any]:
    stored = {r.key: r.value for r in session.scalars(select(Setting))}
    return {**DEFAULTS, **stored}
