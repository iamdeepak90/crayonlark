"""Website tasks: publish a live book (assets, content draft, revalidate)."""

from __future__ import annotations

from typing import Any

from crayonlark.core import site
from crayonlark.core.db import session_scope
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book
from crayonlark.core.notify import notify
from crayonlark.worker.celery_app import celery


@celery.task(name="crayonlark.site.book_live", autoretry_for=(ConnectionError,), max_retries=3)
@tracked
def book_live(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        assets = site.publish_assets(s, book)
        book.is_public = True
        post = site.draft_content(s, book)
        post_id, title = post.id, book.title
    site.revalidate()
    notify(
        f"📝 Blog draft for “{title}” is waiting for approval (admin → Blog posts).",
        kind="approval",
        book_id=book_id,
    )
    return {"assets": assets, "post_id": post_id}


@celery.task(name="crayonlark.site.refresh")
@tracked
def refresh(book_id: int, publish_assets: bool = False) -> dict[str, Any]:
    if publish_assets:
        with session_scope() as s:
            book = s.get(Book, book_id)
            if book is not None:
                site.publish_assets(s, book)
    return {"revalidated": site.revalidate()}
