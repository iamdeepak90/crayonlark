"""Phase 7 tasks: Etsy sales sync, nightly backup and the weekly report."""

from __future__ import annotations

from typing import Any

from crayonlark.core import backup, sales
from crayonlark.core.db import session_scope
from crayonlark.core.jobs import tracked
from crayonlark.core.notify import notify
from crayonlark.integrations import etsy
from crayonlark.providers import transient_errors
from crayonlark.reports import weekly
from crayonlark.worker.celery_app import celery
from crayonlark.worker.tasks.marketing_tasks import connected


@celery.task(
    name="crayonlark.sales.etsy_sync",
    autoretry_for=transient_errors(),
    retry_backoff=True,
    max_retries=3,
)
@tracked
def etsy_sync(days: int = 30) -> dict[str, Any]:
    if not (etsy.configured() and connected(etsy.PROVIDER)):
        return {"skipped": "Etsy not connected"}
    with session_scope() as s:
        return sales.sync_etsy(s, days=days)


@celery.task(name="crayonlark.backup.run")
@tracked
def run_backup() -> dict[str, Any]:
    try:
        result = backup.run()
    except Exception as exc:
        notify(f"⚠️ Nightly backup FAILED: {type(exc).__name__}: {exc}"[:3500], kind="alert")
        raise
    return {k: v for k, v in result.items() if k != "buckets"}


@celery.task(name="crayonlark.report.weekly")
@tracked
def weekly_report() -> dict[str, Any]:
    with session_scope() as s:
        out = weekly.send(s)
    return {"telegram": out["telegram"], "email": out["email"]}
