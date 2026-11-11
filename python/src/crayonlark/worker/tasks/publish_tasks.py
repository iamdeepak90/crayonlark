"""Phase 3 tasks: cover (cpu-heavy), listing drafts (llm), KDP pack + Etsy files (cpu-heavy)."""

from __future__ import annotations

from typing import Any

from crayonlark.core import flows, publishing
from crayonlark.core.budget import BudgetExceeded
from crayonlark.core.db import session_scope
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book
from crayonlark.core.notify import notify
from crayonlark.worker.celery_app import celery

RETRYABLE = (ConnectionError, TimeoutError)


def _book(s: Any, book_id: int) -> Book:
    book = s.get(Book, book_id)
    if book is None:
        raise ValueError(f"book {book_id} not found")
    return book


@celery.task(
    name="crayonlark.book.build_cover", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3
)
@tracked
def build_cover(book_id: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
    with session_scope() as s:
        cover = publishing.build_cover(s, _book(s, book_id), options)
        cover_id, version = cover.id, cover.version
    return {"cover_id": cover_id, "version": version}


@celery.task(
    name="crayonlark.book.draft_listings",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=3,
)
@tracked
def draft_listings(book_id: int) -> dict[str, Any]:
    try:
        with session_scope() as s:
            rows = publishing.draft_listings(s, _book(s, book_id))
            ids = [r.id for r in rows]
    except BudgetExceeded as exc:
        notify(f"⛔ Listing agent stopped for book #{book_id}: {exc}", kind="budget")
        raise
    flows.after_listings_drafted(book_id)
    return {"listings": ids}


@celery.task(
    name="crayonlark.book.build_pack", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3
)
@tracked
def build_pack(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = _book(s, book_id)
        key = publishing.build_pack(s, book)
        title, week = book.title, book.kdp_week_start
    notify(
        f"📦 KDP upload pack ready for “{title}” (slot week {week}). "
        "Download it in admin → Packs and upload it to KDP by hand.",
        kind="pack",
        book_id=book_id,
    )
    return {"pack_key": key, "week": str(week)}


@celery.task(
    name="crayonlark.book.build_etsy_files",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=3,
)
@tracked
def build_etsy_files(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        out = publishing.build_etsy_files(s, _book(s, book_id))
    if out:
        flows.queue_mockups(book_id)
    return {str(k): v for k, v in out.items()}
