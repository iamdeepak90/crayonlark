"""Admin: Etsy drafts + publish approval, mockups, Pinterest boards and pins (Phase 4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.api.routers.admin_books import get_book
from crayonlark.core import approvals, flows, marketing
from crayonlark.core.audit import record
from crayonlark.core.enums import BookStatus, EtsyStatus, ListingStatus, PinStatus
from crayonlark.core.models import Book, Listing, Pin, PinterestBoard
from crayonlark.integrations import etsy, oauth, pinterest

router = APIRouter(prefix="/api/admin", tags=["admin-marketing"])


@router.get("/etsy")
def etsy_overview(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    books = s.scalars(
        select(Book)
        .join(Listing)
        .where(
            Listing.platform == "etsy",
            Listing.status == ListingStatus.APPROVED,
            Book.status != BookStatus.ARCHIVED,
        )
        .distinct()
        .order_by(Book.updated_at.desc())
    )
    rows = []
    for b in books:
        problems = marketing.etsy_problems(b)
        rows.append(
            {
                "id": b.id,
                "title": b.title,
                "etsy_status": b.etsy_status,
                "problems": {str(k): v for k, v in problems.items()},
                "listings": [
                    {
                        "id": lst.id,
                        "product_kind": lst.product_kind,
                        "title": lst.title,
                        "price_cents": lst.price_cents,
                        "file_keys": lst.file_keys or {},
                        "mockups": marketing.etsy_images(lst),
                        "pins": marketing.pin_images(lst),
                        "etsy": None
                        if lst.etsy is None
                        else {
                            "etsy_listing_id": lst.etsy.etsy_listing_id,
                            "state": lst.etsy.state,
                            "url": lst.etsy.url,
                            "uploaded": sorted(lst.etsy.uploaded or {}),
                            "publish_approved_by": lst.etsy.publish_approved_by,
                            "error": lst.etsy.error,
                        },
                    }
                    for lst in marketing.approved_etsy(b)
                ],
            }
        )
    return {
        "configured": etsy.configured(),
        "connection": oauth.status(s, etsy.PROVIDER),
        "remaining_today": etsy.remaining_today(),
        "books": rows,
    }


@router.post("/books/{book_id}/mockups")
def rebuild_mockups(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    get_book(s, book_id)
    flows.after_etsy_files(book_id)
    return {"queued": True}


@router.post("/books/{book_id}/etsy/drafts")
def create_drafts(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    if not etsy.configured() or not oauth.status(s, etsy.PROVIDER)["connected"]:
        raise HTTPException(400, "connect Etsy first")
    problems = marketing.etsy_problems(b)
    if problems:
        raise HTTPException(400, f"fix first: {problems}")
    return {"job_id": flows.queue_etsy_drafts(b.id)}


@router.post("/books/{book_id}/etsy/approve-publish")
def approve_publish(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    if b.etsy_status != EtsyStatus.ETSY_DRAFTS_CREATED:
        raise HTTPException(400, "Etsy drafts are not ready")
    try:
        approvals.approve_etsy_publish(s, b, admin.actor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    flows.after_etsy_publish_approved(b.id)
    return {"queued": True}


# --------------------------------------------------------------------------- Pinterest


def pin_out(p: Pin) -> dict[str, Any]:
    return {
        "id": p.id,
        "book_id": p.book_id,
        "title": p.title,
        "link": p.link,
        "image_key": p.image_key,
        "scheduled_at": p.scheduled_at,
        "posted_at": p.posted_at,
        "status": p.status,
        "error": p.error,
        "pinterest_pin_id": p.pinterest_pin_id,
    }


@router.get("/pinterest")
def pinterest_overview(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    now = datetime.now(UTC)
    upcoming = s.scalars(
        select(Pin).where(Pin.status == PinStatus.SCHEDULED).order_by(Pin.scheduled_at).limit(60)
    )
    recent = s.scalars(
        select(Pin)
        .where(Pin.status != PinStatus.SCHEDULED)
        .order_by(Pin.updated_at.desc())
        .limit(30)
    )
    boards = s.scalars(select(PinterestBoard).order_by(PinterestBoard.name))
    return {
        "configured": pinterest.configured(),
        "connection": oauth.status(s, pinterest.PROVIDER),
        "now": now,
        "boards": [
            {"id": b.id, "name": b.name, "pinterest_board_id": b.pinterest_board_id} for b in boards
        ],
        "upcoming": [pin_out(p) for p in upcoming],
        "recent": [pin_out(p) for p in recent],
    }


@router.post("/pinterest/boards/sync")
def sync_boards(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    try:
        n = marketing.sync_boards(s)
    except (PermissionError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    return {"added": n}


@router.post("/books/{book_id}/pins/plan")
def plan(book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    b = get_book(s, book_id)
    pins = marketing.plan_pins(s, b)
    record(s, admin.actor.name, "pins.plan", "book", b.id, {"n": len(pins)})
    s.commit()
    return {"scheduled": len(pins)}


@router.post("/pins/{pin_id}/cancel")
def cancel(pin_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    p = s.get(Pin, pin_id)
    if p is None:
        raise HTTPException(404)
    if p.status in (PinStatus.SCHEDULED, PinStatus.FAILED):
        p.status = PinStatus.CANCELLED
    s.commit()
    return pin_out(p)


@router.post("/pins/{pin_id}/retry")
def retry(pin_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    p = s.get(Pin, pin_id)
    if p is None:
        raise HTTPException(404)
    if p.status == PinStatus.FAILED:
        p.status, p.error = PinStatus.SCHEDULED, None
        p.scheduled_at = max(p.scheduled_at, datetime.now(UTC))
    s.commit()
    return pin_out(p)
