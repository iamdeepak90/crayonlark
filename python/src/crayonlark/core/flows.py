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


def autopilot_on() -> bool:
    from crayonlark.core import app_settings

    return bool((app_settings.get("autopilot") or {}).get("enabled"))


def poke_autopilot() -> None:
    """Run the Autopilot now (it also runs every 10 minutes)."""
    from crayonlark.worker.celery_app import celery

    celery.send_task("crayonlark.autopilot.tick", queue="default")


def run_autopilot_plan(plan: Any) -> None:
    """Enqueue what core/autopilot.tick() decided (after its commit)."""
    for book_id in plan.concepts:
        queue_concepts(book_id)
    for book_id, ids in plan.art.items():
        queue_art(book_id, ids)
    for book_id, ids in plan.clean.items():
        after_image_set_approved(book_id, ids)
    if plan.research:
        queue_research(plan.research, "", True)


def notify_images_ready(book_id: int) -> None:
    if autopilot_on():  # the Autopilot keeps the pictures that passed both checks
        poke_autopilot()
        return
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


def queue_color_refs(book_id: int, image_ids: list[int]) -> list[str]:
    """Colour examples for the Etsy pages (books with "colour reference" on)."""
    return [
        enqueue(
            "crayonlark.image.color_ref",
            {"image_id": image_id},
            "images",
            idempotency_key=f"color:{image_id}",
            book_id=book_id,
        )
        for image_id in image_ids
    ]


def after_cleaning(book_id: int) -> None:
    enqueue("crayonlark.book.build_interior", {"book_id": book_id}, "cpu-heavy", book_id=book_id)


def after_interior(book_id: int) -> None:
    """Interior built → the KDP cover (kept for approval 2) and the listing texts, in parallel."""
    queue_cover(book_id)
    queue_listings(book_id)


def queue_listings(book_id: int) -> str:
    return enqueue("crayonlark.book.draft_listings", {"book_id": book_id}, "llm", book_id=book_id)


def queue_cover(book_id: int, options: dict[str, Any] | None = None) -> str:
    return enqueue(
        "crayonlark.book.build_cover",
        {"book_id": book_id, "options": options or {}},
        "cpu-heavy",
        book_id=book_id,
    )


def after_listings_drafted(book_id: int) -> None:
    """Listing text written → the Etsy PDF, then mockups, then approval 1 (Etsy)."""
    queue_etsy_files(book_id)


def queue_etsy_files(book_id: int) -> str:
    return enqueue(
        "crayonlark.book.build_etsy_files", {"book_id": book_id}, "cpu-heavy", book_id=book_id
    )


def queue_mockups(book_id: int) -> str:
    return enqueue(
        "crayonlark.book.build_mockups", {"book_id": book_id}, "cpu-heavy", book_id=book_id
    )


def after_kdp_approved(book_id: int) -> None:
    """Approval 2 (KDP) → the upload pack, with the next free weekly KDP slot."""
    enqueue("crayonlark.book.build_pack", {"book_id": book_id}, "cpu-heavy", book_id=book_id)


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


def after_mockups(book_id: int, ready_for_review: bool) -> None:
    """Etsy PDF + mockups done → approval 1 on admin → Etsy approval (and on Telegram)."""
    if ready_for_review:
        enqueue("crayonlark.telegram.etsy_review", {"book_id": book_id}, "publish", book_id=book_id)


def queue_etsy_publish(book_id: int) -> str:
    """Put one approved book live on Etsy now (draft + images + PDFs + activate)."""
    return enqueue(
        "crayonlark.etsy.publish",
        {"book_id": book_id},
        "publish",
        idempotency_key=f"etsy-publish:{book_id}",
        book_id=book_id,
    )


def after_etsy_published(book_id: int, pinterest_ready: bool) -> None:
    notify(f"🛍 Book #{book_id} is live on Etsy.", book_id=book_id)
    if pinterest_ready:
        enqueue("crayonlark.pinterest.plan", {"book_id": book_id}, "default", book_id=book_id)


# --------------------------------------------------------------------------- Phase 6: AI generation


def queue_research(theme: str, notes: str, use_web: bool) -> str:
    return enqueue(
        "crayonlark.ai.research", {"theme": theme, "notes": notes, "use_web": use_web}, "llm"
    )


def after_research(theme: str, count: int, dropped: list[str]) -> None:
    extra = f" ({len(dropped)} dropped by the blocklist)" if dropped else ""
    if autopilot_on():
        notify(f"💡 {count} niche ideas for “{theme}”; the Autopilot uses them in order{extra}.")
        poke_autopilot()
        return
    notify(f"💡 {count} niche ideas for “{theme}” are waiting for you{extra}.", kind="approval")


def queue_concepts(book_id: int) -> str:
    return enqueue("crayonlark.ai.concepts", {"book_id": book_id}, "llm", book_id=book_id)


def after_concepts(book_id: int, saved: int, manual: bool) -> None:
    if autopilot_on() and not manual:  # the Autopilot generates the pictures
        poke_autopilot()
        return
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
