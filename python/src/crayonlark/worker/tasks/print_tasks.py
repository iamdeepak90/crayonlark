"""Print-engine tasks (cpu-heavy queue, concurrency 1)."""

from __future__ import annotations

from typing import Any

from crayonlark.agents import vision_qa
from crayonlark.core import flows, pipeline
from crayonlark.core.db import session_scope
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book, Image
from crayonlark.worker.celery_app import celery

RETRYABLE = (ConnectionError, TimeoutError)


@celery.task(name="crayonlark.image.qa", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3)
@tracked
def image_qa(image_id: int) -> dict[str, Any]:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None:
            return {"skipped": "missing"}
        result = pipeline.run_image_qa(s, img)
        vision = vision_qa.enabled()
        if vision:  # the vision model runs on the llm queue, not on this cpu-heavy worker
            img.vision_scores = {"pending": True}
        s.flush()
        ready = pipeline.finish_qa_if_ready(s, img.book)
        book_id = img.book_id
    if vision:
        flows.queue_vision_qa(image_id, book_id)
    if ready:
        flows.notify_images_ready(book_id)
    return result


@celery.task(
    name="crayonlark.image.clean", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3
)
@tracked
def image_clean(image_id: int) -> dict[str, Any]:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None:
            return {"skipped": "missing"}
        result = pipeline.clean_one(s, img)
        s.flush()
        moved = pipeline.finish_cleaning_if_ready(s, img.book)
        book_id = img.book_id
        wants_color = img.book.color_reference
    if wants_color:
        flows.queue_color_refs(book_id, [image_id])
    if moved:
        flows.after_cleaning(book_id)
    return result


@celery.task(
    name="crayonlark.book.build_interior",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=3,
)
@tracked
def build_interior(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = s.get(Book, book_id)
        assert book is not None
        rep = pipeline.build_interior(s, book)
    flows.after_interior(book_id)
    return {"pages": rep.pages, "min_dpi": rep.min_image_dpi, "fonts": rep.fonts}


@celery.task(
    name="crayonlark.book.build_etsy_pdfs",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=3,
)
@tracked
def build_etsy_pdfs(book_id: int, products: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    with session_scope() as s:
        book = s.get(Book, book_id)
        assert book is not None
        return pipeline.build_etsy_pdfs(s, book, products)


@celery.task(name="crayonlark.inbox.scan")
@tracked
def inbox_scan() -> dict[str, Any]:
    with session_scope() as s:
        ids = pipeline.import_inbox(s)
    for image_id in ids:
        flows.queue_qa(image_id)
    return {"imported": ids}
