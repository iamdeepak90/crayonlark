"""Telegram callback kinds for Phase 3+: cover and listing approvals."""

from __future__ import annotations

from crayonlark.core import approvals, flows
from crayonlark.core.actors import HumanActor
from crayonlark.core.db import session_scope
from crayonlark.core.enums import ApprovalState
from crayonlark.core.models import Book, Cover


def handle(kind: str, ident: int, yes: bool, actor: HumanActor) -> str:
    match kind:
        case "cover":
            with session_scope() as s:
                cover = s.get(Cover, ident)
                if cover is None:
                    return "Cover not found"
                if cover.approval != ApprovalState.PENDING:
                    return f"Cover v{cover.version} was already {cover.approval}"
                approvals.decide_cover(s, cover, yes, actor)
                book_id = cover.book_id
            flows.after_cover_decision(book_id, yes)
            return "✅ Cover approved. Writing listings…" if yes else "🔁 Building a new cover…"
        case "listings":
            with session_scope() as s:
                book = s.get(Book, ident)
                if book is None:
                    return "Book not found"
                if yes:
                    approvals.approve_all_listings(s, book, actor)
                else:
                    approvals.reject_listings(s, book, actor)
            if yes:
                flows.after_listings_approved(ident)
                return "✅ Listings approved. Building the KDP pack and Etsy files…"
            flows.after_listings_rejected(ident)
            return "🔁 Redrafting listings…"
    return f"Unknown action {kind}"
