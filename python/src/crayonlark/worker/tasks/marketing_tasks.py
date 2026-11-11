"""Phase 4 tasks: mockups (cpu-heavy), Etsy drafts/publish and Pinterest (publish/default)."""

from __future__ import annotations

from typing import Any

from crayonlark.core import flows, marketing
from crayonlark.core.actors import SYSTEM
from crayonlark.core.db import session_scope
from crayonlark.core.enums import BookStatus
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book, OAuthToken
from crayonlark.core.state_machine import transition
from crayonlark.integrations import etsy, pinterest
from crayonlark.worker.celery_app import celery

RETRYABLE = (ConnectionError, TimeoutError)


def _book(s: Any, book_id: int) -> Book:
    book = s.get(Book, book_id)
    if book is None:
        raise ValueError(f"book {book_id} not found")
    return book


def connected(provider: str) -> bool:
    with session_scope() as s:
        return s.get(OAuthToken, provider) is not None


@celery.task(
    name="crayonlark.book.build_mockups",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=3,
)
@tracked
def build_mockups(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = _book(s, book_id)
        out = marketing.build_mockups(s, book)
        ready = book.status == BookStatus.LISTING_DRAFT
        if ready:  # Etsy PDF + mockups done: approval 1
            transition(s, book, BookStatus.AWAITING_ETSY_APPROVAL, SYSTEM)
    flows.after_mockups(book_id, ready)
    return {str(k): len(v) for k, v in out.items()}


@celery.task(
    name="crayonlark.etsy.publish", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=5
)
@tracked
def publish(book_id: int) -> dict[str, Any]:
    """Put one approved (queued) book live on Etsy."""
    with session_scope() as s:
        urls = marketing.publish_book(s, _book(s, book_id))
    flows.after_etsy_published(book_id, pinterest.configured() and connected(pinterest.PROVIDER))
    return {"urls": urls}


@celery.task(name="crayonlark.etsy.publish_daily")
@tracked
def publish_daily() -> dict[str, Any]:
    """Every 30 min: if today's book is due (after the set hour, quota not used), start it."""
    if not (etsy.configured() and connected(etsy.PROVIDER)):
        return {"skipped": "Etsy not connected"}
    with session_scope() as s:
        book = marketing.due_for_etsy(s)
        book_id = book.id if book else None
    if book_id is None:
        return {"skipped": "nothing due"}
    return {"book_id": book_id, "job_id": flows.queue_etsy_publish(book_id)}


@celery.task(name="crayonlark.etsy.sync_stats")
@tracked
def sync_stats() -> dict[str, Any]:
    """Views and favourites of live listings, for the KDP candidates ranking."""
    if not (etsy.configured() and connected(etsy.PROVIDER)):
        return {"skipped": "Etsy not connected"}
    with session_scope() as s:
        return {"listings": marketing.sync_stats(s)}


@celery.task(name="crayonlark.pinterest.plan")
@tracked
def plan_pins(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        pins = marketing.plan_pins(s, _book(s, book_id))
        return {"scheduled": [p.scheduled_at.isoformat() for p in pins]}


@celery.task(name="crayonlark.pinterest.post_due")
def post_due() -> dict[str, Any]:
    """Beat: every 15 minutes, post at most one due pin (keeps 3-5/day naturally spaced)."""
    if not (pinterest.configured() and connected(pinterest.PROVIDER)):
        return {"skipped": "pinterest not connected"}
    with session_scope() as s:
        return {"posted": marketing.post_due_pins(s)}
