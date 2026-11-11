"""Admin: the two book approvals after the image set.

1. Etsy approval: every finished book. Approving puts it in the daily Etsy queue
   (one book goes live per day).
2. KDP approval: only the books I pick from the KDP candidates (live on Etsy, ranked by their
   Etsy results). Approving takes the next free weekly KDP slot.

Plus the Autopilot (everything between the two approvals) and "Continue" for a book that
stopped between two automatic steps.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.api.routers.admin_books import get_book
from crayonlark.api.routers.admin_publish import cover_out, listing_out
from crayonlark.core import (
    app_settings,
    approvals,
    autopilot,
    flows,
    kdp_slots,
    marketing,
    pipeline,
)
from crayonlark.core import publishing as pub
from crayonlark.core.enums import BookFormat, BookStatus
from crayonlark.core.models import Book, Cover
from crayonlark.core.state_machine import TransitionError
from crayonlark.integrations import etsy, oauth

router = APIRouter(prefix="/api/admin", tags=["admin-flow"])

LOW_STOCK_DAYS = 3


def _etsy_connected(s: Session) -> bool:
    return etsy.configured() and bool(oauth.status(s, etsy.PROVIDER)["connected"])


def _book_card(s: Session, b: Book) -> dict[str, Any]:
    lst = approvals.etsy_listing(b)
    problems = pub.listing_problems(s, b)
    row = lst.etsy if lst else None
    return {
        "id": b.id,
        "title": b.title,
        "status": b.status,
        "pages": len(pipeline.approved_images(b)),
        "page_ids": [i.id for i in pipeline.approved_images(b)],
        "color_reference": b.color_reference,
        "etsy_approved_at": b.etsy_approved_at,
        "etsy_live_at": b.etsy_live_at,
        "listing": None if lst is None else listing_out(lst, problems.get(lst.id)),
        "mockups": marketing.etsy_images(lst)[:6] if lst else [],
        "etsy": None if row is None else {"url": row.url, "state": row.state, "error": row.error},
    }


# --------------------------------------------------------------------------- 1. Etsy


@router.get("/etsy/review")
def etsy_review(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    waiting = s.scalars(
        select(Book)
        .where(Book.status == BookStatus.AWAITING_ETSY_APPROVAL)
        .order_by(Book.updated_at)
    )
    queue = marketing.etsy_queue(s)
    dates = marketing.planned_dates(s)
    making = s.scalars(
        select(Book).where(
            Book.status.in_(
                [
                    BookStatus.NICHE_APPROVED,
                    BookStatus.CONCEPTS_READY,
                    BookStatus.IMAGES_GENERATING,
                    BookStatus.IMAGES_QA,
                    BookStatus.AWAITING_IMAGE_APPROVAL,
                    BookStatus.CLEANING,
                    BookStatus.BUILDING,
                    BookStatus.LISTING_DRAFT,
                ]
            )
        )
    ).all()
    cfg = marketing.daily_settings()
    days_of_stock = len(queue) / cfg["per_day"]
    recent = s.scalars(
        select(Book)
        .where(Book.etsy_live_at.is_not(None))
        .order_by(Book.etsy_live_at.desc())
        .limit(7)
    )
    return {
        "configured": etsy.configured(),
        "connected": _etsy_connected(s),
        "connection": oauth.status(s, etsy.PROVIDER),
        "remaining_today": etsy.remaining_today(),
        "daily": cfg,
        "live_today": marketing.live_today(s),
        "days_of_stock": round(days_of_stock, 1),
        "low_stock": days_of_stock < LOW_STOCK_DAYS,
        "in_production": len(making),
        "waiting": [_book_card(s, b) for b in waiting],
        "queue": [{**_book_card(s, b), "planned_for": dates.get(b.id)} for b in queue],
        "recent": [_book_card(s, b) for b in recent],
    }


def _gate(fn: Any) -> None:
    try:
        fn()
    except (ValueError, TransitionError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/books/{book_id}/etsy/approve")
def approve_etsy(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    _gate(lambda: approvals.approve_for_etsy(s, b, admin.actor))
    s.commit()
    return {"status": b.status, "planned_for": marketing.planned_dates(s).get(b.id)}


class Note(BaseModel):
    note: str = Field(default="", max_length=500)


@router.post("/books/{book_id}/etsy/send-back")
def send_back(
    book_id: int, body: Note, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    _gate(lambda: approvals.send_back_for_etsy(s, b, admin.actor, body.note))
    s.commit()
    flows.queue_listings(b.id)
    return {"status": b.status}


@router.post("/books/{book_id}/etsy/unqueue")
def unqueue(book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    b = get_book(s, book_id)
    _gate(lambda: approvals.unqueue_etsy(s, b, admin.actor))
    s.commit()
    return {"status": b.status}


@router.post("/books/{book_id}/etsy/publish-now")
def publish_now(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    """Skip the wait: put this approved book live now (it counts towards today)."""
    b = get_book(s, book_id)
    if b.status != BookStatus.ETSY_QUEUED:
        raise HTTPException(400, "only books in the Etsy queue can be published")
    if not _etsy_connected(s):
        raise HTTPException(400, "connect Etsy first (Settings → Keys and connections → Etsy)")
    return {"job_id": flows.queue_etsy_publish(b.id)}


# --------------------------------------------------------------------------- 2. KDP


def _candidate(s: Session, b: Book, now: datetime) -> dict[str, Any]:
    cover = b.covers[-1] if b.covers else None
    kdp = approvals.kdp_listing(b)
    problems = pub.listing_problems(s, b)
    return {
        "id": b.id,
        "title": b.title,
        "pages": b.page_count,
        "designs": len(pipeline.approved_images(b)),
        "kdp_skipped": b.kdp_skipped,
        "etsy_url": b.etsy_url,
        "stats": marketing.book_stats(s, b, now),
        "cover": cover_out(cover) if cover else None,
        "kdp_listing": None if kdp is None else listing_out(kdp, problems.get(kdp.id)),
        "ready": bool(cover and cover.pdf_key and b.interior_key and kdp),
    }


@router.get("/kdp/candidates")
def kdp_candidates(
    show_skipped: bool = False, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    now = datetime.now(UTC)
    q = select(Book).where(Book.status == BookStatus.ON_ETSY)
    if not show_skipped:
        q = q.where(Book.kdp_skipped.is_(False))
    rows = [_candidate(s, b, now) for b in s.scalars(q)]
    rows.sort(key=lambda r: (r["stats"]["score"], r["stats"]["days_on_etsy"]), reverse=True)
    first = kdp_slots.week_start(now)
    used = kdp_slots.used_by_week(s, BookFormat.PAPERBACK, first)
    limit = kdp_slots.limit_for(BookFormat.PAPERBACK)
    next_week = kdp_slots.pick_week(used, limit, first)
    return {
        "candidates": rows,
        "score_help": marketing.SCORE_HELP,
        "slots": kdp_slots.summary(s),
        "next_free_week": next_week,
        "next_free_week_end": next_week + timedelta(days=6),
        "per_month": limit * 52 // 12,
    }


class KdpApprove(BaseModel):
    cover_id: int | None = None


@router.post("/books/{book_id}/kdp/approve")
def approve_kdp(
    book_id: int,
    body: KdpApprove,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    b = get_book(s, book_id)
    cover = s.get(Cover, body.cover_id) if body.cover_id else None
    _gate(lambda: approvals.approve_for_kdp(s, b, admin.actor, cover))
    s.commit()
    flows.after_kdp_approved(b.id)
    return {"status": b.status}


class Skip(BaseModel):
    skip: bool = True


@router.post("/books/{book_id}/kdp/skip")
def skip_kdp(
    book_id: int, body: Skip, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    approvals.skip_kdp(s, b, admin.actor, body.skip)
    return {"kdp_skipped": b.kdp_skipped}


# --------------------------------------------------------------------------- Autopilot


@router.get("/autopilot")
def autopilot_status(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    return autopilot.status(s)


class AutopilotIn(BaseModel):
    enabled: bool


@router.put("/autopilot")
def set_autopilot(
    body: AutopilotIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    """On/off only (the rest is fixed in core/autopilot.py). Recorded in the audit log."""
    app_settings.set_value("autopilot", {"enabled": body.enabled}, admin.actor.name, s)
    s.commit()
    if body.enabled:
        flows.poke_autopilot()
    return autopilot.status(s)


# --------------------------------------------------------------------------- setup


@router.get("/setup")
def setup(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    """The few things only I can do once. Everything else is fixed in code."""
    from crayonlark.core.config import get_settings

    st = get_settings()
    items = [
        {
            "id": "openrouter",
            "label": "OpenRouter key: writes the text and checks every picture",
            "done": bool(st.openrouter_api_key),
            "required": True,
        },
        {
            "id": "deepinfra",
            "label": "DeepInfra key: makes the pictures (about ₹0.26 each)",
            "done": bool(st.deepinfra_api_key),
            "required": True,
        },
        {
            "id": "etsy",
            "label": "Etsy: app keys, then connect your shop",
            "done": _etsy_connected(s),
            "required": True,
        },
        {
            "id": "telegram",
            "label": "Telegram (optional): approve for Etsy from your phone, get alerts",
            "done": bool(st.telegram_bot_token and st.telegram_admin_chat_id),
            "required": False,
        },
    ]
    return {"items": items, "ready": all(i["done"] for i in items if i["required"])}


# --------------------------------------------------------------------------- continue


def continue_step(b: Book) -> tuple[str, Any] | None:
    """The automatic step to (re)start for a book that stopped, or None."""
    match b.status:
        case BookStatus.CLEANING:
            ids = [i.id for i in pipeline.approved_images(b) if not i.cleaned_key]
            return ("cleaning", lambda: flows.after_image_set_approved(b.id, ids))
        case BookStatus.BUILDING:
            return ("building the interior", lambda: flows.after_cleaning(b.id))
        case BookStatus.LISTING_DRAFT:
            lst = approvals.etsy_listing(b)
            if lst is None or approvals.kdp_listing(b) is None:
                label, step = "writing the listing text", flows.queue_listings
            elif not lst.file_keys:
                label, step = "building the Etsy PDF", flows.queue_etsy_files
            else:
                label, step = "making the mockups", flows.queue_mockups
            needs_cover = not b.covers  # the KDP cover is made alongside, for approval 2

            def run() -> None:
                if needs_cover:
                    flows.queue_cover(b.id)
                step(b.id)

            return (label, run)
        case BookStatus.AWAITING_ETSY_APPROVAL:
            return ("rebuilding the Etsy PDF and mockups", lambda: flows.queue_etsy_files(b.id))
    return None


@router.post("/books/{book_id}/continue")
def continue_book(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    step = continue_step(b)
    if step is None:
        raise HTTPException(400, f"nothing to restart for a book that is {b.status}")
    label, start = step
    s.commit()
    start()
    return {"started": label}
