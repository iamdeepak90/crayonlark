"""Phase 4 tasks: mockups (cpu-heavy), Etsy drafts/publish and Pinterest (publish/default)."""

from __future__ import annotations

from typing import Any

from crayonlark.core import flows, marketing
from crayonlark.core.db import session_scope
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book, OAuthToken
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
        out = marketing.build_mockups(s, _book(s, book_id))
    flows.after_mockups(book_id, etsy.configured() and connected(etsy.PROVIDER))
    return {str(k): len(v) for k, v in out.items()}


@celery.task(
    name="crayonlark.etsy.create_drafts",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=5,
)
@tracked
def create_drafts(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        ids = marketing.create_etsy_drafts(s, _book(s, book_id))
    flows.after_etsy_drafts(book_id)
    return {"etsy_listing_ids": ids}


@celery.task(
    name="crayonlark.etsy.publish", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=5
)
@tracked
def publish(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        urls = marketing.publish_etsy(s, _book(s, book_id))
    flows.after_etsy_published(book_id, pinterest.configured() and connected(pinterest.PROVIDER))
    return {"urls": urls}


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
