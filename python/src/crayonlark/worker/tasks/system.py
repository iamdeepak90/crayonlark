from __future__ import annotations

from crayonlark.worker.celery_app import celery


@celery.task(name="crayonlark.ping")
def ping() -> str:
    return "pong"
