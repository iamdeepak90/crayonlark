"""Phase 6 services: research → (I approve a niche) → concepts → art → QA (Python + vision).

None of these functions approves anything. Niches, image sets and everything after still wait
for me in admin/Telegram (core/approvals.py).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from crayonlark.agents import concept, research, vision_qa
from crayonlark.core import app_settings, blocklist, budget, pipeline, storage
from crayonlark.core.enums import ImageStatus
from crayonlark.core.models import Book, Image
from crayonlark.integrations import websearch
from crayonlark.providers.image import base as image_base

log = logging.getLogger("crayonlark.generation")


# --------------------------------------------------------------------------- research


def run_research(
    session: Session, theme: str, notes: str = "", use_web: bool = True
) -> dict[str, Any]:
    hits = blocklist.find(theme, blocklist.extra_terms(session))
    if hits:
        raise blocklist.BlockedContent({"theme": hits})
    results: list[dict[str, str]] = []
    web_error = None
    if use_web and websearch.configured():
        try:
            results = websearch.niche_search(theme)
        except budget.BudgetExceeded:
            raise
        except Exception as exc:  # search is a nice-to-have: carry on with the notes only
            web_error = f"{type(exc).__name__}: {exc}"[:300]
    out = research.run(theme, notes, results)
    saved, dropped = research.save_ideas(session, theme, out)
    return {
        "niche_ids": [n.id for n in saved],
        "dropped": dropped,
        "web_results": len(results),
        "web_error": web_error,
    }


# --------------------------------------------------------------------------- concepts


def concept_count(session: Session) -> int:
    return int(app_settings.get("concepts_per_niche", session) or 40)


def make_concepts(session: Session, book: Book) -> dict[str, Any]:
    out = concept.run(book, concept_count(session))
    saved, dropped = concept.save_concepts(session, book, out)
    return {"saved": saved, "dropped": dropped}


def pending_concepts(book: Book) -> list[Image]:
    return [i for i in book.images if i.status == ImageStatus.PENDING and not i.original_key]


# --------------------------------------------------------------------------- art


def art_targets(book: Book, limit: int | None = None) -> list[Image]:
    todo = [i for i in pending_concepts(book) if i.prompt]
    return todo[:limit] if limit else todo


def generate_one(session: Session, image: Image) -> Image:
    """Generate the picture for one concept row (paid, budget-guarded)."""
    if image.original_key:
        return image  # idempotent: already has a file
    hits = blocklist.find(image.prompt, blocklist.extra_terms(session))
    if hits:
        image.status, image.error = ImageStatus.FAILED, f"blocked terms in prompt: {hits}"
        return image
    result = image_base.generate(image.prompt, agent="art", book_id=image.book_id)
    cfg = image_base.image_config()
    pipeline.add_original(
        session,
        image.book,
        result.data,
        provider=cfg.get("provider", ""),
        model=result.model,
        image=image,
    )
    image.model = result.model
    image.cost_usd = (image.cost_usd or 0) + result.cost_usd
    image.ai_generated = True
    image.error = None
    return image


def attach_upload(session: Session, image: Image, data: bytes, filename: str) -> Image:
    """Manual mode: attach a file I made from this concept's prompt."""
    return pipeline.add_original(
        session, image.book, data, filename=filename, provider="manual", image=image
    )


# --------------------------------------------------------------------------- vision QA


def vision_check(session: Session, image: Image) -> dict[str, Any]:
    """Run the vision model on one image and merge its verdict with the Python QA result.

    Failures (budget reached, refusal, provider down) never block the pipeline: the image is
    marked "not checked" and I review it as usual."""
    if not image.original_key:
        raise ValueError(f"image {image.id} has no original")
    book = image.book
    try:
        out = vision_qa.run(
            storage.get_bytes("originals", image.original_key),
            image.scene_title,
            f"{book.age_min}-{book.age_max}",
            book_id=book.id,
        )
    except Exception as exc:  # recorded on the image; I still review it
        log.warning("vision QA failed for image %s: %s", image.id, exc)
        image.vision_scores = {"checked": False, "error": str(exc)[:500]}
        return image.vision_scores
    if out is None:
        image.vision_scores = {"checked": False}
        return image.vision_scores
    scores = vision_qa.to_scores(out)
    image.vision_scores = scores
    if scores["recommendation"] == "reject":
        image.qa_recommendation = "reject"
    return scores


def needs_vision(image: Image) -> bool:
    return bool((image.vision_scores or {}).get("pending"))
