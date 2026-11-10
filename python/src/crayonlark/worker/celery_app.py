"""Celery app. Queues:
- llm        : LLM agent calls (research, concept, listing, vision QA, website content)
- images     : image generation / uploads
- publish    : Etsy / Pinterest API calls, notifications
- cpu-heavy  : cleanup (potrace), PDF builds, covers, mockups. Runs on worker-heavy, concurrency 1.
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.signals import worker_process_init
from kombu import Queue

from crayonlark.core.config import env_settings

QUEUES = ("default", "llm", "images", "publish", "cpu-heavy")

# env_settings(): the Redis URL is an infra secret and must not touch the database here. The full
# get_settings() also reads saved integrations from Postgres; doing that at import time opened a
# pooled connection in the Celery parent, which the forked workers then shared, and their
# queries broke with "consuming input failed: server closed the connection unexpectedly".
_redis = env_settings().redis_url
celery = Celery("crayonlark", broker=_redis, backend=_redis)


@worker_process_init.connect
def _fresh_db_pool(**_: Any) -> None:
    """Each forked worker process opens its own DB connections (never the parent's)."""
    from crayonlark.core.db import get_engine

    get_engine().dispose(close=False)


celery.conf.update(
    task_queues=[Queue(q) for q in QUEUES],
    task_default_queue="default",
    task_acks_late=True,  # with idempotent tasks: a crashed worker's job is re-run
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3 * 24 * 3600,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    imports=["crayonlark.worker.tasks"],
)

from crayonlark.worker.schedule import BEAT_SCHEDULE  # noqa: E402

celery.conf.beat_schedule = BEAT_SCHEDULE
