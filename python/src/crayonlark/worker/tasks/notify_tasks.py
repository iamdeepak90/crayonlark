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


@celery.task(name="crayonlark.telegram.cover_review")
@tracked
def cover_review(cover_id: int) -> dict[str, Any]:
    from crayonlark.core.models import Cover

    with session_scope() as s:
        cover = s.get(Cover, cover_id)
        if cover is None:
            return {"skipped": "missing"}
        book_id, title, version = cover.book_id, cover.book.title, cover.version
        thumb = storage.get_bytes("outputs", cover.thumb_key) if cover.thumb_key else None
        spine, size = cover.spine_in, f"{cover.width_in:.3f} x {cover.height_in:.3f} in"
    admin = get_settings().admin_site_url
    caption = (
        f"📕 Cover v{version} for “{title}”\nFull wrap {size}, spine {spine:.3f} in.\n"
        f"Full preview: {admin}/books/{book_id}/cover"
    )
    buttons = [
        [("✅ Approve cover", f"cover:{cover_id}:1"), ("🔁 New version", f"cover:{cover_id}:0")]
    ]
    if thumb:
        telegram.send_photo(thumb, caption, buttons)
    else:
        telegram.send_message(caption, buttons)
    return {"sent": 1}


@celery.task(name="crayonlark.telegram.listing_review")
@tracked
def listing_review(book_id: int) -> dict[str, Any]:
    from crayonlark.core import publishing

    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        lines = [
            f"• {lst.platform.upper()} {lst.product_kind}: {lst.title[:90]} "
            f"(${lst.price_cents / 100:.2f})"
            for lst in book.listings
        ]
        problems = publishing.listing_problems(s, book)
        title = book.title
    admin = get_settings().admin_site_url
    text = f"📝 Listings drafted for “{title}”:\n" + "\n".join(lines)
    text += f"\n\nReview and edit: {admin}/books/{book_id}/listings"
    if problems:
        text += f"\n⚠️ {len(problems)} listing(s) need fixing before approval (blocklist/rules)."
        telegram.send_message(text)
    else:
        telegram.send_message(
            text,
            [
                [
                    ("✅ Approve all", f"listings:{book_id}:1"),
                    ("🔁 Redraft", f"listings:{book_id}:0"),
                ]
            ],
        )
    return {"listings": len(lines), "problems": len(problems)}


@celery.task(name="crayonlark.telegram.etsy_review")
@tracked
def etsy_review(book_id: int) -> dict[str, Any]:
    with session_scope() as s:
        book = s.get(Book, book_id)
        if book is None:
            return {"skipped": "missing"}
        lines = [
            f"• {lst.product_kind}: {lst.title[:80]} (${lst.price_cents / 100:.2f})"
            for lst in book.listings
            if lst.platform == "etsy" and lst.etsy is not None and lst.etsy.etsy_listing_id
        ]
        title = book.title
    admin = get_settings().admin_site_url
    telegram.send_message(
        f"🛍 Etsy drafts created for “{title}”:\n"
        + "\n".join(lines)
        + f"\n\nCheck them on Etsy or in {admin}/etsy, then approve publishing.",
        [[("✅ Publish on Etsy", f"etsypub:{book_id}:1")]],
    )
    return {"drafts": len(lines)}
