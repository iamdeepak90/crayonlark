"""What happens next after each step: small functions that enqueue follow-up jobs.

Kept in one place so the whole pipeline flow can be read top to bottom.
"""

from __future__ import annotations

from typing import Any

from crayonlark.core.jobs import enqueue
from crayonlark.core.notify import notify


def queue_qa(image_id: int, book_id: int | None = None) -> str:
    return enqueue(
        "crayonlark.image.qa",
        {"image_id": image_id},
        "cpu-heavy",
        idempotency_key=f"qa:{image_id}",
        book_id=book_id,
    )


def notify_images_ready(book_id: int) -> None:
    notify(
        f"🖼 Book #{book_id}: images passed QA and are waiting for your approval.",
        kind="approval",
        book_id=book_id,
    )


def after_image_set_approved(book_id: int, image_ids: list[int]) -> None:
    for image_id in image_ids:
        enqueue(
            "crayonlark.image.clean",
            {"image_id": image_id},
            "cpu-heavy",
            idempotency_key=f"clean:{image_id}",
            book_id=book_id,
        )


def after_cleaning(book_id: int) -> None:
    enqueue("crayonlark.book.build_interior", {"book_id": book_id}, "cpu-heavy", book_id=book_id)


def after_interior(book_id: int) -> None:
    queue_cover(book_id)


def queue_cover(book_id: int, options: dict[str, Any] | None = None) -> str:
    return enqueue(
        "crayonlark.book.build_cover",
        {"book_id": book_id, "options": options or {}},
        "cpu-heavy",
        book_id=book_id,
    )


def after_cover_built(book_id: int, cover_id: int) -> None:
    enqueue(
        "crayonlark.telegram.cover_review",
        {"cover_id": cover_id},
        "publish",
        idempotency_key=f"cover-review:{cover_id}",
        book_id=book_id,
    )


def after_cover_decision(book_id: int, approved: bool) -> None:
    """Approved → the listing agent drafts listings. Rejected → build a new cover version."""
    if approved:
        enqueue("crayonlark.book.draft_listings", {"book_id": book_id}, "llm", book_id=book_id)
    else:
        queue_cover(book_id)


def after_listings_drafted(book_id: int) -> None:
    enqueue(
        "crayonlark.telegram.listing_review",
        {"book_id": book_id},
        "publish",
        book_id=book_id,
    )


def after_listings_approved(book_id: int) -> None:
    enqueue("crayonlark.book.build_pack", {"book_id": book_id}, "cpu-heavy", book_id=book_id)
    enqueue("crayonlark.book.build_etsy_files", {"book_id": book_id}, "cpu-heavy", book_id=book_id)


def after_listings_rejected(book_id: int) -> None:
    enqueue("crayonlark.book.draft_listings", {"book_id": book_id}, "llm", book_id=book_id)


def notify_text(text: str) -> None:
    notify(text)


def after_live(book_id: int) -> None:
    """Book is live on Amazon: catalog page (assets + revalidate) and a blog post draft."""
    notify(f"🎉 Book #{book_id} is live. Website page + blog draft are being prepared.")
    enqueue("crayonlark.site.book_live", {"book_id": book_id}, "llm", book_id=book_id)


def after_site_change(book_id: int, publish_assets: bool = False) -> None:
    enqueue(
        "crayonlark.site.refresh",
        {"book_id": book_id, "publish_assets": publish_assets},
        "default",
        book_id=book_id,
    )


# --------------------------------------------------------------------------- Etsy + Pinterest


def after_etsy_files(book_id: int) -> None:
    enqueue("crayonlark.book.build_mockups", {"book_id": book_id}, "cpu-heavy", book_id=book_id)


def after_mockups(book_id: int, etsy_ready: bool) -> None:
    if etsy_ready:
        queue_etsy_drafts(book_id)
    else:
        notify(
            f"🖼 Mockups ready for book #{book_id}. Connect Etsy in admin → Etsy to create drafts.",
            book_id=book_id,
        )


def queue_etsy_drafts(book_id: int) -> str:
    return enqueue(
        "crayonlark.etsy.create_drafts",
        {"book_id": book_id},
        "publish",
        idempotency_key=f"etsy-drafts:{book_id}",
        book_id=book_id,
    )


def after_etsy_drafts(book_id: int) -> None:
    enqueue("crayonlark.telegram.etsy_review", {"book_id": book_id}, "publish", book_id=book_id)


def after_etsy_publish_approved(book_id: int) -> None:
    enqueue(
        "crayonlark.etsy.publish",
        {"book_id": book_id},
        "publish",
        idempotency_key=f"etsy-publish:{book_id}",
        book_id=book_id,
    )


def after_etsy_published(book_id: int, pinterest_ready: bool) -> None:
    notify(f"🛍 Etsy listings for book #{book_id} are live.", book_id=book_id)
    if pinterest_ready:
        enqueue("crayonlark.pinterest.plan", {"book_id": book_id}, "default", book_id=book_id)


# --------------------------------------------------------------------------- Phase 6: AI generation


def queue_research(theme: str, notes: str, use_web: bool) -> str:
    return enqueue(
        "crayonlark.ai.research", {"theme": theme, "notes": notes, "use_web": use_web}, "llm"
    )


def after_research(theme: str, count: int, dropped: list[str]) -> None:
    extra = f" ({len(dropped)} dropped by the blocklist)" if dropped else ""
    notify(f"💡 {count} niche ideas for “{theme}” are waiting for you{extra}.", kind="approval")


def queue_concepts(book_id: int) -> str:
    return enqueue("crayonlark.ai.concepts", {"book_id": book_id}, "llm", book_id=book_id)


def after_concepts(book_id: int, saved: int, manual: bool) -> None:
    tail = (
        "Make the pictures from the prompts in admin and upload them."
        if manual
        else "Press “Generate images” in admin when you are ready (paid)."
    )
    notify(f"📝 Book #{book_id}: {saved} scene prompts ready. {tail}", book_id=book_id)


def queue_art(book_id: int, image_ids: list[int]) -> list[str]:
    return [
        enqueue(
            "crayonlark.ai.generate_image",
            {"image_id": image_id},
            "images",
            idempotency_key=f"art:{image_id}",
            book_id=book_id,
        )
        for image_id in image_ids
    ]


def queue_vision_qa(image_id: int, book_id: int | None = None) -> str:
    return enqueue("crayonlark.ai.vision_qa", {"image_id": image_id}, "llm", book_id=book_id)
