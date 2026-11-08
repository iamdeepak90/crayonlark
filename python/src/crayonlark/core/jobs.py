"""Job tracking: every background task gets a row in `jobs` (status, error, cost, retries).

enqueue() is idempotent per idempotency_key: a second call with the same key returns the
existing job instead of queueing duplicate work.
"""

from __future__ import annotations

import functools
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from crayonlark.core.db import session_scope
from crayonlark.core.enums import JobStatus
from crayonlark.core.models import Job


def enqueue(
    task_name: str,
    kwargs: dict[str, Any],
    queue: str,
    idempotency_key: str | None = None,
    book_id: int | None = None,
    countdown: int | None = None,
) -> str:
    from crayonlark.worker.celery_app import celery

    with session_scope() as s:
        if idempotency_key:
            existing = s.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
            if existing is not None and existing.status != JobStatus.FAILED:
                return existing.id
            if existing is not None:  # failed before: retry under the same key
                existing.status = JobStatus.QUEUED
                existing.error = None
                job = existing
            else:
                job = Job(
                    name=task_name,
                    queue=queue,
                    idempotency_key=idempotency_key,
                    book_id=book_id,
                    args=kwargs,
                )
                s.add(job)
        else:
            job = Job(name=task_name, queue=queue, book_id=book_id, args=kwargs)
            s.add(job)
        s.flush()
        job_id = job.id
    result = celery.send_task(
        task_name, kwargs={**kwargs, "job_id": job_id}, queue=queue, countdown=countdown
    )
    with session_scope() as s:
        j = s.get(Job, job_id)
        if j is not None:
            j.celery_task_id = result.id
    return job_id


def tracked[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """Decorator for task bodies: marks the job running/succeeded/failed."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        job_id = kwargs.pop("job_id", None)
        if job_id:
            with session_scope() as s:
                j = s.get(Job, job_id)
                if j is not None:
                    j.status, j.started_at = JobStatus.RUNNING, datetime.now(UTC)
                    j.attempts += 1
        try:
            out = fn(*args, **kwargs)
        except Exception as exc:
            if job_id:
                with session_scope() as s:
                    j = s.get(Job, job_id)
                    if j is not None:
                        j.status, j.finished_at = JobStatus.FAILED, datetime.now(UTC)
                        j.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-3000:]}"
            raise
        if job_id:
            with session_scope() as s:
                j = s.get(Job, job_id)
                if j is not None:
                    j.status, j.finished_at = JobStatus.SUCCEEDED, datetime.now(UTC)
                    j.result = out if isinstance(out, dict) else {"result": str(out)}
        return out

    return wrapper
