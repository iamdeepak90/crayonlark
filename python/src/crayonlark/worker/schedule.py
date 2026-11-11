"""Celery beat schedule (the `scheduler` service). Times are UTC."""

from __future__ import annotations

from typing import Any

from celery.schedules import crontab

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
    "autopilot": {
        "task": "crayonlark.autopilot.tick",
        "schedule": 600.0,  # does nothing while the Autopilot is off
        "options": {"queue": "default"},
    },
    "etsy-publish-daily": {
        "task": "crayonlark.etsy.publish_daily",
        "schedule": crontab(minute="5,35"),  # puts at most `per_day` queued books live a day
        "options": {"queue": "publish"},
    },
    "etsy-stats-sync": {
        "task": "crayonlark.etsy.sync_stats",
        "schedule": crontab(minute=40, hour=6),  # Etsy tabulates views once a day
        "options": {"queue": "publish"},
    },
    "etsy-sales-sync": {
        "task": "crayonlark.sales.etsy_sync",
        "schedule": crontab(minute=10, hour="*/6"),  # skipped quietly until Etsy is connected
        "options": {"queue": "publish"},
    },
    "nightly-backup": {
        "task": "crayonlark.backup.run",
        "schedule": crontab(minute=30, hour=21),  # 03:00 IST, the quiet hours
        "options": {"queue": "cpu-heavy"},
    },
    "weekly-report": {
        "task": "crayonlark.report.weekly",
        "schedule": crontab(minute=30, hour=3, day_of_week="mon"),  # Monday 09:00 IST
        "options": {"queue": "default"},
    },
}
