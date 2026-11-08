"""Human approval gates. The ONLY place gate transitions happen.

Every function here requires a HumanActor and writes the audit log. Workers and agents never
call these; they react to the resulting status (e.g. a cleaning job is enqueued after the image
set is approved).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings
from crayonlark.core.actors import Actor, HumanActor
from crayonlark.core.audit import record
from crayonlark.core.enums import ApprovalState, BookStatus, EtsyStatus, ListingStatus, NicheStatus
from crayonlark.core.models import Book, Cover, Image, Listing, Niche
from crayonlark.core.state_machine import GateError, transition, transition_etsy


def _human(actor: Actor) -> HumanActor:
    if not isinstance(actor, HumanActor):
        raise GateError(f"{actor.name} is not a human; approvals need a human")
    return actor


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- niche


def decide_niche(session: Session, niche: Niche, approve: bool, actor: Actor) -> None:
    h = _human(actor)
    niche.status = NicheStatus.APPROVED if approve else NicheStatus.REJECTED
    niche.approved_by, niche.approved_at = h.name, _now()
    record(session, h.name, "niche.approve" if approve else "niche.reject", "niche", niche.id)


def approve_book_idea(session: Session, book: Book, actor: Actor) -> None:
    """idea → niche_approved (a book created from an approved niche or by me directly)."""
    transition(session, book, BookStatus.NICHE_APPROVED, _human(actor))


# --------------------------------------------------------------------------- images


def decide_image(session: Session, image: Image, approve: bool, actor: Actor) -> None:
    h = _human(actor)
    image.approval = ApprovalState.APPROVED if approve else ApprovalState.REJECTED
    image.approved_by, image.approved_at = h.name, _now()
    record(
        session,
        h.name,
        "image.approve" if approve else "image.reject",
        "image",
        image.id,
        {"book_id": image.book_id},
    )


def approved_count(session: Session, book: Book) -> int:
    return int(
        session.scalar(
            select(func.count(Image.id)).where(
                Image.book_id == book.id, Image.approval == ApprovalState.APPROVED
            )
        )
        or 0
    )


def approve_image_set(
    session: Session, book: Book, actor: Actor, min_images: int | None = None
) -> int:
    """Lock the approved image set and move the book to cleaning. Returns approved count."""
    h = _human(actor)
    limits = app_settings.get("images_per_book", session) or {"min": 25, "max": 50}
    lo = limits["min"] if min_images is None else min_images
    n = approved_count(session, book)
    if n < lo:
        raise ValueError(f"only {n} images approved; need at least {lo}")
    if n > limits["max"]:
        raise ValueError(f"{n} images approved; maximum is {limits['max']}")
    transition(session, book, BookStatus.CLEANING, h, note=f"{n} images approved")
    record(session, h.name, "book.image_set.approve", "book", book.id, {"count": n})
    return n


# --------------------------------------------------------------------------- cover


def decide_cover(session: Session, cover: Cover, approve: bool, actor: Actor) -> None:
    h = _human(actor)
    book = cover.book
    cover.approval = ApprovalState.APPROVED if approve else ApprovalState.REJECTED
    cover.approved_by, cover.approved_at = h.name, _now()
    record(
        session,
        h.name,
        "cover.approve" if approve else "cover.reject",
        "cover",
        cover.id,
        {"book_id": book.id},
    )
    if approve:
        book.cover_key = cover.pdf_key
        transition(session, book, BookStatus.LISTING_DRAFT, h)
    else:
        transition(session, book, BookStatus.BUILDING, h, note="cover rejected, rebuild")


# --------------------------------------------------------------------------- listings


def decide_listing(session: Session, listing: Listing, approve: bool, actor: Actor) -> None:
    h = _human(actor)
    listing.status = ListingStatus.APPROVED if approve else ListingStatus.REJECTED
    listing.approved_by, listing.approved_at = h.name, _now()
    record(
        session,
        h.name,
        "listing.approve" if approve else "listing.reject",
        "listing",
        listing.id,
        {"platform": listing.platform, "book_id": listing.book_id},
    )


def approve_all_listings(session: Session, book: Book, actor: Actor) -> None:
    """Approve the KDP listing + Etsy listings together → kdp_pack_ready (pack gets built)."""
    h = _human(actor)
    listings = session.scalars(select(Listing).where(Listing.book_id == book.id)).all()
    if not any(lst.platform == "kdp" for lst in listings):
        raise ValueError("no KDP listing to approve")
    for lst in listings:
        if lst.status != ListingStatus.REJECTED:
            decide_listing(session, lst, True, h)
    transition(session, book, BookStatus.KDP_PACK_READY, h)


def reject_listings(session: Session, book: Book, actor: Actor, note: str = "") -> None:
    h = _human(actor)
    transition(session, book, BookStatus.LISTING_DRAFT, h, note=note or "listings rejected")


# --------------------------------------------------------------------------- KDP manual steps


def mark_kdp_uploaded(session: Session, book: Book, actor: Actor) -> None:
    transition(session, book, BookStatus.KDP_UPLOADED, _human(actor))


def mark_proof_ordered(session: Session, book: Book, actor: Actor) -> None:
    transition(session, book, BookStatus.PROOF_ORDERED, _human(actor))


def mark_live(
    session: Session, book: Book, actor: Actor, asin: str = "", amazon_url: str = ""
) -> None:
    h = _human(actor)
    if asin:
        book.kdp_asin = asin.strip()
    if amazon_url:
        book.amazon_url = amazon_url.strip()
    transition(session, book, BookStatus.LIVE, h)


# --------------------------------------------------------------------------- Etsy publish


def approve_etsy_publish(session: Session, book: Book, actor: Actor) -> None:
    """Approve publishing all Etsy drafts of a book. The publish job then flips them active."""
    h = _human(actor)
    if book.etsy_status != EtsyStatus.ETSY_DRAFTS_CREATED:
        raise ValueError("Etsy drafts are not created yet")
    for lst in book.listings:
        if lst.platform == "etsy" and lst.etsy is not None:
            lst.etsy.publish_approved_by = h.name
            lst.etsy.publish_approved_at = _now()
    record(session, h.name, "etsy.publish.approve", "book", book.id)


def require_etsy_publish_approval(listing: Listing) -> str:
    """The Etsy publish gate. Called by the publish job right before it activates a listing."""
    if listing.etsy is None or not listing.etsy.publish_approved_by:
        raise GateError(f"listing {listing.id}: Etsy publish was not approved by a human")
    return listing.etsy.publish_approved_by


def confirm_etsy_published(session: Session, book: Book, actor: Actor) -> None:
    """After every approved Etsy listing is active, record the book as published."""
    for lst in book.listings:
        if lst.platform == "etsy" and lst.status == ListingStatus.APPROVED:
            require_etsy_publish_approval(lst)
    transition_etsy(session, book, EtsyStatus.ETSY_PUBLISHED, actor)
