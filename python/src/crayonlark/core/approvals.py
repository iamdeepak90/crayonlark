"""Approval gates. The ONLY place gate transitions happen.

Every function here requires a HumanActor and writes the audit log. Workers and agents never
call these; they react to the resulting status (e.g. a cleaning job is enqueued after the image
set is approved).

One exception, switched on by me in Settings: the Autopilot (core/autopilot.py) may decide
niches and image sets (see _human_or_autopilot). Approval 1 (Etsy) and approval 2 (KDP) are
always mine.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings
from crayonlark.core.actors import Actor, AutopilotActor, HumanActor
from crayonlark.core.audit import record
from crayonlark.core.enums import (
    ApprovalState,
    BookStatus,
    EtsyStatus,
    ListingStatus,
    NicheStatus,
    PostStatus,
)
from crayonlark.core.models import BlogPost, Book, Cover, Image, Listing, Niche
from crayonlark.core.state_machine import GateError, transition, transition_etsy


def _human(actor: Actor) -> HumanActor:
    if not isinstance(actor, HumanActor):
        raise GateError(f"{actor.name} is not a human; approvals need a human")
    return actor


def autopilot_on(session: Session | None = None) -> bool:
    return bool((app_settings.get("autopilot", session) or {}).get("enabled"))


def _human_or_autopilot(session: Session, actor: Actor) -> Actor:
    """For the niche and image-set gates only: me, or the Autopilot while I have it switched on."""
    if isinstance(actor, AutopilotActor):
        if not autopilot_on(session):
            raise GateError("the Autopilot is switched off")
        return actor
    return _human(actor)


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- niche


def decide_niche(session: Session, niche: Niche, approve: bool, actor: Actor) -> None:
    h = _human_or_autopilot(session, actor)
    niche.status = NicheStatus.APPROVED if approve else NicheStatus.REJECTED
    niche.approved_by, niche.approved_at = h.name, _now()
    record(session, h.name, "niche.approve" if approve else "niche.reject", "niche", niche.id)


def approve_book_idea(session: Session, book: Book, actor: Actor) -> None:
    """idea → niche_approved (a book created from an approved niche or by me directly)."""
    transition(session, book, BookStatus.NICHE_APPROVED, _human_or_autopilot(session, actor))


# --------------------------------------------------------------------------- images


def decide_image(session: Session, image: Image, approve: bool, actor: Actor) -> None:
    h = _human_or_autopilot(session, actor)
    if approve and not image.original_key:
        raise ValueError(f"image {image.id} has no picture yet (concept only)")
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
    h = _human_or_autopilot(session, actor)
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
    """Approve or reject one cover version. The book only moves on with "Approve for KDP"."""
    h = _human(actor)
    cover.approval = ApprovalState.APPROVED if approve else ApprovalState.REJECTED
    cover.approved_by, cover.approved_at = h.name, _now()
    record(
        session,
        h.name,
        "cover.approve" if approve else "cover.reject",
        "cover",
        cover.id,
        {"book_id": cover.book_id},
    )
    if approve:
        cover.book.cover_key = cover.pdf_key


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


def etsy_listing(book: Book) -> Listing | None:
    from crayonlark.core.publishing import etsy_listing as find

    return find(book)


def kdp_listing(book: Book) -> Listing | None:
    from crayonlark.core.publishing import kdp_listing as find

    return find(book)


def _problems(session: Session, book: Book, listing: Listing) -> None:
    from crayonlark.core.publishing import listing_problems

    hits = listing_problems(session, book).get(listing.id)
    if hits:
        raise ValueError(f"fix the {listing.platform} listing first: {hits}")


# --------------------------------------------------------------------------- approval 1: Etsy


def approve_for_etsy(session: Session, book: Book, actor: Actor) -> None:
    """Approval 1. Approves the Etsy listing text AND its Etsy publish (both gates, both
    recorded). The book joins the Etsy queue; the scheduler puts one book live per day."""
    from crayonlark.core.config import get_settings
    from crayonlark.core.models import EtsyListing

    h = _human(actor)
    if book.status != BookStatus.AWAITING_ETSY_APPROVAL:
        raise ValueError(f"book is {book.status}, not waiting for Etsy approval")
    lst = etsy_listing(book)
    if lst is None:
        raise ValueError("no Etsy listing yet")
    _problems(session, book, lst)
    if not lst.file_keys or not lst.mockup_keys:
        raise ValueError("the Etsy PDF and mockups are still being made")
    decide_listing(session, lst, True, h)
    row = lst.etsy
    if row is None:
        row = EtsyListing(listing_id=lst.id, shop_id=get_settings().etsy_shop_id or None)
        session.add(row)
        lst.etsy = row
    row.publish_approved_by, row.publish_approved_at = h.name, _now()
    record(session, h.name, "etsy.publish.approve", "book", book.id, {"listing_id": lst.id})
    book.etsy_approved_at = _now()
    transition(session, book, BookStatus.ETSY_QUEUED, h)


def send_back_for_etsy(session: Session, book: Book, actor: Actor, note: str = "") -> None:
    """Not good enough yet: the listing agent writes new text (and the PDF is rebuilt)."""
    h = _human(actor)
    transition(session, book, BookStatus.LISTING_DRAFT, h, note=note or "sent back")


def unqueue_etsy(session: Session, book: Book, actor: Actor) -> None:
    """Take a book out of the Etsy queue before it goes live (approval withdrawn)."""
    h = _human(actor)
    lst = etsy_listing(book)
    if lst is not None:
        lst.status = ListingStatus.DRAFT
        if lst.etsy is not None:
            lst.etsy.publish_approved_by = lst.etsy.publish_approved_at = None
    book.etsy_approved_at = None
    record(session, h.name, "etsy.publish.withdraw", "book", book.id)
    transition(session, book, BookStatus.AWAITING_ETSY_APPROVAL, h)


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


# --------------------------------------------------------------------------- approval 2: KDP


def approve_for_kdp(session: Session, book: Book, actor: Actor, cover: Cover | None = None) -> None:
    """Approval 2, only for the books I pick. Approves the cover and the KDP listing text
    (both gates, both recorded) and moves the book to KDP; the pack job then takes the next
    free weekly KDP slot."""
    h = _human(actor)
    if book.status != BookStatus.ON_ETSY:
        raise ValueError(f"book is {book.status}: only books live on Etsy can go to KDP")
    cover = cover or (book.covers[-1] if book.covers else None)
    if cover is None or cover.book_id != book.id or not cover.pdf_key:
        raise ValueError("the KDP cover is not built yet")
    if cover.approval == ApprovalState.REJECTED:
        raise ValueError("this cover was rejected: pick or build another one")
    if not book.interior_key:
        raise ValueError("the KDP interior is not built yet")
    lst = kdp_listing(book)
    if lst is None:
        raise ValueError("no KDP listing yet")
    _problems(session, book, lst)
    if cover.approval != ApprovalState.APPROVED:
        decide_cover(session, cover, True, h)
    book.cover_key = cover.pdf_key
    if lst.status != ListingStatus.APPROVED:
        decide_listing(session, lst, True, h)
    book.kdp_skipped = False
    record(session, h.name, "kdp.approve", "book", book.id, {"cover_id": cover.id})
    transition(session, book, BookStatus.KDP_PACK_READY, h)


def skip_kdp(session: Session, book: Book, actor: Actor, skip: bool = True) -> None:
    """ "Not for KDP": hide the book from the KDP candidates (it stays on Etsy)."""
    h = _human(actor)
    book.kdp_skipped = skip
    record(session, h.name, "kdp.skip" if skip else "kdp.unskip", "book", book.id)


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
    book.live_at = book.live_at or _now()


# --------------------------------------------------------------------------- blog


def decide_post(session: Session, post: BlogPost, approve: bool, actor: Actor) -> None:
    """Publish (or reject) a blog post. Only a human can publish to the website."""
    h = _human(actor)
    post.status = PostStatus.PUBLISHED if approve else PostStatus.REJECTED
    post.approved_by = h.name
    if approve and post.published_at is None:
        post.published_at = _now()
    record(session, h.name, "post.publish" if approve else "post.reject", "post", post.id)
