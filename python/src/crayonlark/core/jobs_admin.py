"""Retry failed jobs from the admin job monitor."""

from __future__ import annotations

from crayonlark.core.db import session_scope
from crayonlark.core.enums import JobStatus
from crayonlark.core.models import Job


def retry(job_id: str) -> str:
    from crayonlark.worker.celery_app import celery

    with session_scope() as s:
        job = s.get(Job, job_id)
        if job is None:
            raise ValueError("job not found")
        if job.status not in (JobStatus.FAILED, JobStatus.QUEUED):
            raise ValueError(f"job is {job.status}; only failed/stuck jobs can be retried")
        job.status, job.error = JobStatus.QUEUED, None
        name, queue, args = job.name, job.queue, dict(job.args or {})
    result = celery.send_task(name, kwargs={**args, "job_id": job_id}, queue=queue)
    with session_scope() as s:
        j = s.get(Job, job_id)
        if j is not None:
            j.celery_task_id = result.id
    return job_id
