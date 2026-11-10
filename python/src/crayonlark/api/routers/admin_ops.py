"""Admin: dashboard, niches, job monitor, audit log, settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.core import app_settings, approvals, budget, flows, jobs_admin, kdp_slots, pipeline
from crayonlark.core.enums import BookStatus, JobStatus, NicheStatus, PostStatus, SubscriberStatus
from crayonlark.core.models import AuditLog, BlogPost, Book, ContactMessage, Job, Niche, Subscriber

router = APIRouter(prefix="/api/admin", tags=["admin-ops"])


NEEDS_YOU_STATUSES = (
    BookStatus.AWAITING_IMAGE_APPROVAL,
    BookStatus.AWAITING_COVER_APPROVAL,
    BookStatus.AWAITING_LISTING_APPROVAL,
    BookStatus.KDP_PACK_READY,
)


@router.get("/dashboard")
def dashboard(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    by_status = dict(
        s.execute(select(Book.status, func.count(Book.id)).group_by(Book.status)).all()
    )
    failed_jobs = s.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)) or 0
    pending_niches = (
        s.scalar(select(func.count(Niche.id)).where(Niche.status == NicheStatus.PROPOSED)) or 0
    )
    out: dict[str, Any] = {
        "books_by_status": by_status,
        "statuses": [st.value for st in BookStatus],
        "failed_jobs": failed_jobs,
        "pending_niches": pending_niches,
        "posts_to_review": s.scalar(
            select(func.count(BlogPost.id)).where(
                BlogPost.status.in_([PostStatus.DRAFT, PostStatus.AWAITING_APPROVAL])
            )
        )
        or 0,
        "subscribers": s.scalar(
            select(func.count(Subscriber.id)).where(Subscriber.status == SubscriberStatus.CONFIRMED)
        )
        or 0,
        "messages": s.scalar(select(func.count(ContactMessage.id))) or 0,
    }
    # everything waiting for a human decision (the top-bar counter)
    out["needs_you"] = (
        sum(by_status.get(st, 0) for st in NEEDS_YOU_STATUSES)
        + pending_niches
        + out["posts_to_review"]
    )
    out["kdp_slots"] = kdp_slots.summary(s)
    out["budget"] = budget.summary(s)
    return out


# --------------------------------------------------------------------------- niches


class NicheIn(BaseModel):
    theme: str = Field(min_length=2)
    name: str = Field(min_length=2)
    age_range: str = "4-8"
    angle: str = ""
    risks: str = ""
    seasonality: str = ""
    notes: str = ""
    color_reference: bool = False


def niche_out(n: Niche) -> dict[str, Any]:
    return {
        "book_id": n.books[0].id if n.books else None,
    } | {
        k: getattr(n, k)
        for k in (
            "id",
            "theme",
            "name",
            "age_range",
            "angle",
            "risks",
            "seasonality",
            "notes",
            "source",
            "status",
            "approved_by",
            "created_at",
            "color_reference",
        )
    }


@router.get("/niches")
def list_niches(
    status: str | None = None, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> list[dict]:
    q = select(Niche).order_by(Niche.created_at.desc())
    if status:
        q = q.where(Niche.status == status)
    return [niche_out(n) for n in s.scalars(q.limit(200))]


@router.post("/niches")
def add_niche(
    body: NicheIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    from crayonlark.core.audit import record

    n = Niche(**body.model_dump(), source="manual")
    s.add(n)
    s.flush()
    record(s, admin.actor.name, "niche.create", "niche", n.id)
    return niche_out(n)


class Decision(BaseModel):
    approve: bool


class Toggle(BaseModel):
    enabled: bool


@router.post("/niches/{niche_id}/color-reference")
def set_niche_color_reference(
    niche_id: int, body: Toggle, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    """Colour example in the page corner (Etsy PDFs only) for this niche and its books.

    Books already drafted on Etsy keep their setting (their files are built); change those on
    the book page if needed."""
    from crayonlark.core.audit import record
    from crayonlark.core.enums import EtsyStatus

    n = s.get(Niche, niche_id)
    if n is None:
        raise HTTPException(404)
    n.color_reference = body.enabled
    books = [b for b in n.books if b.etsy_status == EtsyStatus.NONE]
    for b in books:
        b.color_reference = body.enabled
    record(
        s,
        admin.actor.name,
        "niche.color_reference",
        "niche",
        n.id,
        {"enabled": body.enabled, "books": [b.id for b in books]},
    )
    todo = {b.id: pipeline.needs_color_refs(b) for b in books}
    s.commit()
    for book_id, ids in todo.items():
        if ids:
            flows.queue_color_refs(book_id, ids)
    return {**niche_out(n), "books_updated": len(books)}


@router.post("/niches/{niche_id}/decision")
def decide_niche(
    niche_id: int, body: Decision, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    n = s.get(Niche, niche_id)
    if n is None:
        raise HTTPException(404)
    approvals.decide_niche(s, n, body.approve, admin.actor)
    if not body.approve:
        return niche_out(n)
    # Approving a niche makes its book straight away and starts the scene prompts (once).
    is_new = not n.books
    book = pipeline.book_from_niche(s, n, admin.actor)
    s.commit()
    if is_new and book.status == BookStatus.NICHE_APPROVED:
        flows.queue_concepts(book.id)
    return {**niche_out(n), "book_id": book.id, "book": {"id": book.id, "title": book.title}}


# --------------------------------------------------------------------------- jobs


@router.get("/jobs")
def list_jobs(
    status: str | None = None,
    limit: int = Query(100, le=500),
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> list[dict]:
    q = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if status:
        q = q.where(Job.status == status)
    return [
        {
            "id": j.id,
            "name": j.name,
            "queue": j.queue,
            "status": j.status,
            "book_id": j.book_id,
            "attempts": j.attempts,
            "error": (j.error or "")[:2000],
            "cost_usd": j.cost_usd,
            "args": j.args,
            "created_at": j.created_at,
            "finished_at": j.finished_at,
        }
        for j in s.scalars(q)
    ]


@router.get("/jobs/{job_id}")
def get_job(job_id: str, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    """One job's state, for pages that wait on a background task (e.g. niche research)."""
    j = s.get(Job, job_id)
    if j is None:
        raise HTTPException(404, "job not found")
    return {
        "id": j.id,
        "name": j.name,
        "status": j.status,
        "attempts": j.attempts,
        "error": (j.error or "")[:2000],
        "result": j.result,
        "finished_at": j.finished_at,
    }


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, admin: Admin = Depends(require_admin)) -> dict:
    try:
        return {"job_id": jobs_admin.retry(job_id)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# --------------------------------------------------------------------------- audit


@router.get("/audit")
def audit(
    limit: int = Query(100, le=500),
    offset: int = 0,
    entity_type: str | None = None,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> list[dict]:
    q = select(AuditLog).order_by(AuditLog.at.desc()).limit(limit).offset(offset)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    return [
        {
            "id": a.id,
            "at": a.at,
            "actor": a.actor,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "details": a.details,
        }
        for a in s.scalars(q)
    ]


# --------------------------------------------------------------------------- settings


@router.get("/settings")
def get_settings_all(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    return app_settings.all_settings(s)


class SettingIn(BaseModel):
    value: Any


@router.put("/settings/{key}")
def put_setting(
    key: str, body: SettingIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    if key not in app_settings.DEFAULTS:
        raise HTTPException(400, f"unknown setting {key}")
    app_settings.set_value(key, body.value, admin.actor.name, s)
    return {"key": key, "value": body.value}
