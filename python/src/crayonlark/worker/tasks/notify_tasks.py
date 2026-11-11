"""Telegram approval requests (publish queue): image review album + per-image buttons."""

from __future__ import annotations

import io
import time
from typing import Any

from PIL import Image as PILImage

from crayonlark.core import storage
from crayonlark.core.config import get_settings
from crayonlark.core.db import session_scope
from crayonlark.core.enums import ApprovalState
from crayonlark.core.jobs import tracked
from crayonlark.core.models import Book
from crayonlark.integrations import telegram
from crayonlark.worker.celery_app import celery


def _jpeg(webp: bytes) -> bytes:
    img = PILImage.open(io.BytesIO(webp)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


@celery.task(name="crayonlark.telegram.image_review")
@tracked
def image_review(book_id: int) -> dict[str, Any]:
    if not telegram.enabled():
        return {"skipped": "telegram not configured"}
    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        items = [
            (
                i.id,
                i.thumb_key,
                i.scene_title,
                i.qa_score,
                i.qa_recommendation,
                (i.qa_scores or {}).get("original", {}).get("failures", []),
            )
            for i in book.images
            if i.approval == ApprovalState.PENDING and i.thumb_key
        ]
        title = book.title
    admin = get_settings().admin_site_url
    telegram.send_message(
        f"🖼 “{title}”: {len(items)} images ready for review.\n"
        f"Tap ✅/❌ under each image, then “Approve set”.\nGrid: {admin}/books/{book_id}/images"
    )
    for image_id, key, scene, score, rec, failures in items:
        assert key
        caption = f"#{image_id} {scene}\nQA {score} → {rec}"
        if failures:
            caption += "\n⚠️ " + "; ".join(failures)[:300]
        telegram.send_photo(
            _jpeg(storage.get_bytes("processed", key)),
            caption,
            [[("✅ Keep", f"img:{image_id}:1"), ("❌ Reject", f"img:{image_id}:0")]],
        )
        time.sleep(0.4)
    telegram.send_message(
        f"When done: approve the image set for “{title}”.",
        [[("✅ Approve image set", f"imgset:{book_id}")]],
    )
    return {"sent": len(items)}


@celery.task(name="crayonlark.telegram.etsy_review")
@tracked
def etsy_review(book_id: int) -> dict[str, Any]:
    """Approval 1 on the phone: first mockup + listing title/price, approve or send back."""
    from crayonlark.core import publishing

    if not telegram.enabled():
        return {"skipped": "telegram not configured"}
    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        lst = publishing.etsy_listing(book)
        if lst is None:
            return {"skipped": "no Etsy listing"}
        title, price = lst.title, lst.price_cents / 100
        mock = next(iter(lst.mockup_keys or []), None)
        photo = storage.get_bytes("outputs", mock) if mock else None
        problems = publishing.listing_problems(s, book).get(lst.id)
        n = len(publishing.pipeline.approved_images(book))
    admin = get_settings().admin_site_url
    text = (
        f"🛍 Ready for Etsy: “{title[:120]}”\n${price:.2f} · {n} coloring pages\n"
        f"Check the PDF and text: {admin}/etsy"
    )
    if problems:
        text += f"\n⚠️ Fix first: {problems}"
        buttons = None
    else:
        buttons = [
            [
                ("✅ Approve for Etsy", f"etsyok:{book_id}:1"),
                ("🔁 Send back", f"etsyok:{book_id}:0"),
            ]
        ]
    if photo:
        telegram.send_photo(photo, text, buttons)
    else:
        telegram.send_message(text, buttons)
    return {"sent": 1}
