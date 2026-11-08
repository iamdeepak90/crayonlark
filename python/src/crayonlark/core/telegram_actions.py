"""Telegram approval callbacks → the same approval functions the admin uses.

`handle_callback(data, chat_id)` is synchronous and testable; the bot calls it in a thread.
Callback data format: "<kind>:<id>[:<1|0>]".
"""

from __future__ import annotations

from crayonlark.core import approvals, budget, flows, kdp_slots, pipeline
from crayonlark.core.actors import HumanActor
from crayonlark.core.db import session_scope
from crayonlark.core.models import Book, Image, Niche
from crayonlark.core.state_machine import TransitionError


def handle_callback(data: str, chat_id: int | str) -> str:
    actor = HumanActor.from_telegram(chat_id)  # raises unless it is the admin chat
    parts = data.split(":")
    kind, ident = parts[0], int(parts[1])
    yes = len(parts) < 3 or parts[2] == "1"
    try:
        match kind:
            case "img":
                with session_scope() as s:
                    img = s.get(Image, ident)
                    if img is None:
                        return "Image not found"
                    approvals.decide_image(s, img, yes, actor)
                return "✅ Kept" if yes else "❌ Rejected"
            case "imgset":
                with session_scope() as s:
                    book = s.get(Book, ident)
                    if book is None:
                        return "Book not found"
                    n = approvals.approve_image_set(s, book, actor)
                    ids = [i.id for i in pipeline.approved_images(book)]
                    title = book.title
                flows.after_image_set_approved(ident, ids)
                return f"✅ {n} images approved for “{title}”. Cleaning started."
            case "niche":
                with session_scope() as s:
                    niche = s.get(Niche, ident)
                    if niche is None:
                        return "Niche not found"
                    approvals.decide_niche(s, niche, yes, actor)
                return "✅ Niche approved" if yes else "❌ Niche rejected"
            case _:
                from crayonlark.core import telegram_actions_ext

                return telegram_actions_ext.handle(kind, ident, yes, actor)
    except (ValueError, TransitionError) as exc:
        return f"⚠️ {exc}"


def status_text() -> str:
    from sqlalchemy import func, select

    with session_scope() as s:
        rows = s.execute(select(Book.status, func.count(Book.id)).group_by(Book.status)).all()
        lines = [f"• {st}: {n}" for st, n in sorted(rows)]
        k = kdp_slots.summary(s)
        b = budget.summary(s)
        extra = (
            f"\nKDP slots left this week: {k['paperback_left']} paperback, "
            f"{k['hardcover_left']} hardcover\n"
            f"API spend: ₹{b['spent_inr']:.0f} / ₹{b['cap_inr']:.0f}"
        )
    return "📚 Books by status\n" + ("\n".join(lines) or "none yet") + extra
