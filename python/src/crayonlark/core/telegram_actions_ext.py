"""Telegram callback kinds for approval 1 (Etsy). Approval 2 (KDP) is done in admin, where
the Etsy stats, cover and KDP listing are shown side by side."""

from __future__ import annotations

from crayonlark.core import approvals, flows
from crayonlark.core.actors import HumanActor
from crayonlark.core.db import session_scope
from crayonlark.core.models import Book


def handle(kind: str, ident: int, yes: bool, actor: HumanActor) -> str:
    if kind != "etsyok":
        return f"Unknown action {kind}"
    with session_scope() as s:
        book = s.get(Book, ident)
        if book is None:
            return "Book not found"
        if yes:
            approvals.approve_for_etsy(s, book, actor)
        else:
            approvals.send_back_for_etsy(s, book, actor, "sent back from Telegram")
    if yes:
        return "✅ Approved for Etsy. It joins the daily queue (one book goes live per day)."
    flows.queue_listings(ident)
    return "🔁 Sent back: writing new listing text…"
