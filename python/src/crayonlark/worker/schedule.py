"""Celery beat schedule (the `scheduler` service). Times are UTC."""

from __future__ import annotations

from typing import Any

from celery.schedules import crontab  # noqa: F401  (used from Phase 3)

BEAT_SCHEDULE: dict[str, dict[str, Any]] = {
    "heartbeat": {"task": "crayonlark.ping", "schedule": 300.0},
    "inbox-scan": {
        "task": "crayonlark.inbox.scan",
        "schedule": 300.0,
        "options": {"queue": "default"},
    },
    "pinterest-post-due": {
        "task": "crayonlark.pinterest.post_due",
        "schedule": 900.0,  # every 15 min, at most one pin per run
        "options": {"queue": "publish"},
    },
}
