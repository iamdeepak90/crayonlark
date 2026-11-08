"""Runtime settings stored in the `settings` table, editable from admin → Settings.

Env vars hold secrets and infra; this table holds things I tune: models per agent,
blocklist, prompt templates, Pinterest cadence, etc.
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

DEFAULT_AGENT_MODELS: dict[str, dict[str, str]] = {
    # provider: anthropic | openai | gemini | offline
    "research": {"provider": "offline", "model": ""},
    "concept": {"provider": "offline", "model": ""},
    "listing": {"provider": "offline", "model": ""},
    "vision_qa": {"provider": "offline", "model": ""},
    "website_content": {"provider": "offline", "model": ""},
}

DEFAULTS: dict[str, Any] = {
    "agent_models": DEFAULT_AGENT_MODELS,
    "image_provider": {"provider": "manual", "model": ""},  # manual | openai | gemini
    "house_prompt_template": HOUSE_PROMPT_TEMPLATE,
    "blocklist_extra": [],  # added on top of assets/blocklist.txt
    "images_per_book": {"min": 25, "max": 50},
    "concepts_per_niche": 60,
    "pinterest": {"pins_per_day": 4, "start_hour_utc": 13, "end_hour_utc": 23},
    "free_printable_key": None,  # outputs/free/sample-pack.pdf once built
    "qa_thresholds": {
        "min_side_px": 1500,
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


def seed_defaults() -> None:
    with session_scope() as s:
        for key, value in DEFAULTS.items():
            if s.get(Setting, key) is None:
                s.add(Setting(key=key, value=value, updated_by="system"))
