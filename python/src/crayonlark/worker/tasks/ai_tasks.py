"""Phase 6 tasks: research and concepts (llm queue), image generation (images queue) and vision
QA (llm queue). Transient provider errors are retried with backoff; the budget guard's
BudgetExceeded is not retried (it fails the job and I get a Telegram message)."""

from __future__ import annotations

from typing import Any

from crayonlark.core import autopilot, flows, generation, pipeline
from crayonlark.core.db import session_scope
from crayonlark.core.enums import ImageStatus
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book, Image
from crayonlark.providers import transient_errors
from crayonlark.providers.image.base import image_config
from crayonlark.worker.celery_app import celery

RETRYABLE = transient_errors()


@celery.task(
    name="crayonlark.ai.research", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3
)
@tracked
def research(theme: str, notes: str = "", use_web: bool = True) -> dict[str, Any]:
    with session_scope() as s:
        out = generation.run_research(s, theme, notes, use_web)
    flows.after_research(theme, len(out["niche_ids"]), out["dropped"])
    return out


@celery.task(
    name="crayonlark.ai.concepts", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=3
)
@tracked
def concepts(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        out = generation.make_concepts(s, book)
    manual = image_config().get("provider", "manual") == "manual"
    flows.after_concepts(book_id, out["saved"], manual)
    return out


@celery.task(
    name="crayonlark.ai.generate_image",
    autoretry_for=RETRYABLE,
    retry_backoff=True,
    max_retries=4,
)
@tracked
def generate_image(image_id: int) -> dict[str, Any]:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None:
            return {"skipped": "missing"}
        book_id = img.book_id
    try:
        with session_scope() as s:
            img = s.get(Image, image_id)
            assert img is not None
            generation.generate_one(s, img)
            status = img.status
    except RETRYABLE:
        raise
    except Exception as exc:  # give up on this one image; the rest of the book continues
        _mark_failed(image_id, f"{type(exc).__name__}: {exc}")
        raise
    if status == ImageStatus.UPLOADED:
        flows.queue_qa(image_id, book_id)
    else:  # e.g. blocked prompt: may have been the last image the book was waiting for
        _maybe_ready(image_id)
    return {"status": status}


def _mark_failed(image_id: int, error: str) -> None:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is not None:
            img.status, img.error = ImageStatus.FAILED, error[:2000]
    _maybe_ready(image_id)


def _maybe_ready(image_id: int) -> None:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None:
            return
        ready = pipeline.finish_qa_if_ready(s, img.book)
        book_id = img.book_id
    if ready:
        flows.notify_images_ready(book_id)


@celery.task(name="crayonlark.ai.vision_qa", autoretry_for=RETRYABLE, retry_backoff=True)
@tracked
def vision_qa(image_id: int) -> dict[str, Any]:
    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None:
            return {"skipped": "missing"}
        scores = generation.vision_check(s, img)  # never raises for model/budget errors
        s.flush()
        ready = pipeline.finish_qa_if_ready(s, img.book)
        book_id = img.book_id
    if ready:
        flows.notify_images_ready(book_id)
    return scores


@celery.task(
    name="crayonlark.image.color_ref", autoretry_for=RETRYABLE, retry_backoff=True, max_retries=4
)
@tracked
def color_ref(image_id: int) -> dict[str, Any]:
    """Colour example for one cleaned image (AI, else free auto-fill). Etsy pages only."""
    from crayonlark.core import color_refs

    with session_scope() as s:
        img = s.get(Image, image_id)
        if img is None or not img.cleaned_key:
            return {"skipped": "missing or not cleaned"}
        return color_refs.make(s, img)


@celery.task(name="crayonlark.autopilot.tick")
def autopilot_tick() -> dict[str, Any]:
    """Everything between my two approvals (core/autopilot.py): every 10 min + when a step ends."""
    with session_scope() as s:
        plan = autopilot.tick(s)
    flows.run_autopilot_plan(plan)
    return plan.summary()
