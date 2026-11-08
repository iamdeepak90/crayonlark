"""What happens next after each step: small functions that enqueue follow-up jobs.

Kept in one place so the whole pipeline flow can be read top to bottom.
"""

from __future__ import annotations

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
    """Phase 3 adds the cover build here."""
    enqueue("crayonlark.book.build_etsy_pdfs", {"book_id": book_id}, "cpu-heavy", book_id=book_id)
