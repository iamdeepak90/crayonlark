"""Celery app. Queues:
- llm        : LLM agent calls (research, concept, listing, vision QA, website content)
- images     : image generation / uploads
- publish    : Etsy / Pinterest API calls, notifications
- cpu-heavy  : cleanup (potrace), PDF builds, covers, mockups. Runs on worker-heavy, concurrency 1.
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from crayonlark.core.config import get_settings

QUEUES = ("default", "llm", "images", "publish", "cpu-heavy")

celery = Celery("crayonlark", broker=get_settings().redis_url, backend=get_settings().redis_url)
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
