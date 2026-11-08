"""Admin: covers, listings and KDP upload packs (Phase 3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.api.routers.admin_books import get_book
from crayonlark.core import approvals, flows, kdp_slots, publishing
from crayonlark.core.audit import record
from crayonlark.core.enums import ApprovalState, BookStatus, ListingStatus
from crayonlark.core.models import Book, Cover, Listing
from crayonlark.core.state_machine import TransitionError
from crayonlark.print.cover.render import THEMES

router = APIRouter(prefix="/api/admin", tags=["admin-publish"])


def cover_out(c: Cover) -> dict[str, Any]:
    return {
        "id": c.id,
        "version": c.version,
        "approval": c.approval,
        "approved_by": c.approved_by,
        "template": c.template,
        "options": c.options or {},
        "ai_generated": c.ai_generated,
        "width_in": c.width_in,
        "height_in": c.height_in,
        "spine_in": c.spine_in,
        "files": publishing.cover_files(c),
        "created_at": c.created_at,
    }


def listing_out(lst: Listing, problems: dict[str, list[str]] | None = None) -> dict[str, Any]:
    return {
        "id": lst.id,
        "platform": lst.platform,
        "product_kind": lst.product_kind,
        "title": lst.title,
        "subtitle": lst.subtitle,
        "description": lst.description,
        "keywords": lst.keywords or [],
        "categories": lst.categories or [],
        "tags": lst.tags or [],
        "age_min": lst.age_min,
        "age_max": lst.age_max,
        "price_cents": lst.price_cents,
        "ai_disclosure": lst.ai_disclosure,
        "page_selection": lst.page_selection or [],
        "file_keys": lst.file_keys or {},
        "status": lst.status,
        "approved_by": lst.approved_by,
        "problems": problems or {},
    }


# --------------------------------------------------------------------------- covers


@router.get("/books/{book_id}/covers")
def covers(book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    b = get_book(s, book_id)
    return {
        "book": {"id": b.id, "title": b.title, "status": b.status, "page_count": b.page_count},
        "themes": list(THEMES),
        "covers": [cover_out(c) for c in reversed(b.covers)],
        "approved_images": [
            {"id": i.id, "scene_title": i.scene_title}
            for i in publishing.pipeline.approved_images(b)
        ],
    }


class CoverOptions(BaseModel):
    theme: str | None = None
    hero_image_id: int | None = None
    title: str | None = None
    subtitle: str | None = None
    blurb: str | None = Field(default=None, max_length=600)


@router.post("/books/{book_id}/covers")
def regenerate_cover(
    book_id: int,
    body: CoverOptions,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    b = get_book(s, book_id)
    if b.status not in (BookStatus.BUILDING, BookStatus.AWAITING_COVER_APPROVAL):
        raise HTTPException(400, f"covers can only be rebuilt before approval (status {b.status})")
    if body.theme and body.theme not in THEMES:
        raise HTTPException(400, "unknown theme")
    opts = body.model_dump(exclude_none=True)
    record(s, admin.actor.name, "cover.regenerate", "book", b.id, opts)
    s.commit()
    return {"job_id": flows.queue_cover(b.id, opts)}


@router.post("/covers/{cover_id}/decision")
def decide_cover(
    cover_id: int,
    body: dict[str, bool],
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    cover = s.get(Cover, cover_id)
    if cover is None:
        raise HTTPException(404, "cover not found")
    if cover.approval != ApprovalState.PENDING:
        raise HTTPException(400, f"cover is already {cover.approval}")
    approve = bool(body.get("approve"))
    try:
        approvals.decide_cover(s, cover, approve, admin.actor)
    except TransitionError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    flows.after_cover_decision(cover.book_id, approve)
    return cover_out(cover)


# --------------------------------------------------------------------------- listings


@router.get("/books/{book_id}/listings")
def listings(book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    b = get_book(s, book_id)
    problems = publishing.listing_problems(s, b)
    return {
        "book": {"id": b.id, "title": b.title, "status": b.status, "slug": b.slug},
        "listings": [listing_out(lst, problems.get(lst.id)) for lst in b.listings],
    }


class ListingPatch(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    keywords: list[str] | None = Field(default=None, max_length=7)
    categories: list[str] | None = Field(default=None, max_length=3)
    tags: list[str] | None = Field(default=None, max_length=13)
    price_cents: int | None = Field(default=None, ge=50)
    age_min: int | None = None
    age_max: int | None = None


@router.patch("/listings/{listing_id}")
def update_listing(
    listing_id: int,
    body: ListingPatch,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    lst = s.get(Listing, listing_id)
    if lst is None:
        raise HTTPException(404, "listing not found")
    if lst.status == ListingStatus.APPROVED:
        raise HTTPException(400, "approved listings are locked")
    changes = body.model_dump(exclude_unset=True)
    if lst.platform == "kdp" and "description" in changes:
        from crayonlark.agents.listing import safe_html

        changes["description"] = safe_html(changes["description"])
    if "tags" in changes:
        changes["tags"] = [t.lower().strip()[:20] for t in changes["tags"] if t.strip()]
    for k, v in changes.items():
        setattr(lst, k, v)
    record(s, admin.actor.name, "listing.edit", "listing", lst.id, {"fields": sorted(changes)})
    s.flush()
    problems = publishing.listing_problems(s, lst.book).get(lst.id)
    s.commit()
    return listing_out(lst, problems)


@router.post("/books/{book_id}/listings/approve")
def approve_listings(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    try:
        approvals.approve_all_listings(s, b, admin.actor)
    except (ValueError, TransitionError) as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    flows.after_listings_approved(b.id)
    return {"status": b.status}


@router.post("/books/{book_id}/listings/redraft")
def redraft_listings(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    try:
        if b.status == BookStatus.AWAITING_LISTING_APPROVAL:
            approvals.reject_listings(s, b, admin.actor)
        elif b.status != BookStatus.LISTING_DRAFT:
            raise HTTPException(400, f"cannot redraft in status {b.status}")
    except TransitionError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    flows.after_listings_rejected(b.id)
    return {"status": b.status}


@router.post("/listings/{listing_id}/decision")
def decide_listing(
    listing_id: int,
    body: dict[str, bool],
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    """Reject a single Etsy product (it is then skipped when all listings are approved)."""
    lst = s.get(Listing, listing_id)
    if lst is None:
        raise HTTPException(404, "listing not found")
    if lst.platform == "kdp" and not body.get("approve"):
        raise HTTPException(400, "reject the KDP listing with 'Redraft' instead")
    approvals.decide_listing(s, lst, bool(body.get("approve")), admin.actor)
    s.commit()
    return listing_out(lst)


# --------------------------------------------------------------------------- packs


@router.get("/packs")
def packs(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    shown = [
        BookStatus.KDP_PACK_READY,
        BookStatus.KDP_UPLOADED,
        BookStatus.PROOF_ORDERED,
        BookStatus.LIVE,
    ]
    books = s.scalars(
        select(Book).where(Book.status.in_(shown)).order_by(Book.kdp_week_start, Book.id)
    )
    rows = []
    for b in books:
        etsy = [
            {
                "id": lst.id,
                "product_kind": lst.product_kind,
                "title": lst.title,
                "file_keys": lst.file_keys or {},
            }
            for lst in b.listings
            if lst.platform == "etsy" and lst.status == ListingStatus.APPROVED
        ]
        rows.append(
            {
                "id": b.id,
                "title": b.title,
                "slug": b.slug,
                "status": b.status,
                "format": b.format,
                "page_count": b.page_count,
                "kdp_week_start": b.kdp_week_start,
                "pack_key": b.pack_key,
                "interior_key": b.interior_key,
                "cover_key": b.cover_key,
                "kdp_asin": b.kdp_asin,
                "amazon_url": b.amazon_url,
                "etsy": etsy,
            }
        )
    return {"slots": kdp_slots.summary(s), "packs": rows}


@router.post("/books/{book_id}/pack/rebuild")
def rebuild_pack(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    if b.status != BookStatus.KDP_PACK_READY:
        raise HTTPException(400, "pack can only be rebuilt while it is waiting for upload")
    flows.after_listings_approved(b.id)
    return {"queued": True}
