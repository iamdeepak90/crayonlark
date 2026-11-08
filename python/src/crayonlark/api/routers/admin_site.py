"""Admin: website (book visibility, blog posts with approval, subscribers, contact messages)."""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.api.routers.admin_books import get_book
from crayonlark.core import approvals, flows, site
from crayonlark.core.audit import record
from crayonlark.core.enums import PostStatus, SubscriberStatus
from crayonlark.core.models import BlogPost, ContactMessage, Subscriber

router = APIRouter(prefix="/api/admin", tags=["admin-site"])


def post_admin(p: BlogPost) -> dict[str, Any]:
    return {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "excerpt": p.excerpt,
        "body_md": p.body_md,
        "seo_title": p.seo_title,
        "seo_description": p.seo_description,
        "book_id": p.book_id,
        "ai_generated": p.ai_generated,
        "status": p.status,
        "approved_by": p.approved_by,
        "published_at": p.published_at,
        "updated_at": p.updated_at,
        "cover_url": site.media_url(p.cover_image_key),
    }


@router.get("/posts")
def posts(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> list[dict]:
    return [post_admin(p) for p in s.scalars(select(BlogPost).order_by(BlogPost.id.desc()))]


class PostIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    excerpt: str = Field(default="", max_length=300)
    body_md: str = Field(default="", max_length=20000)
    seo_title: str = Field(default="", max_length=70)
    seo_description: str = Field(default="", max_length=160)


@router.post("/posts")
def create_post(
    body: PostIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    from crayonlark.core.pipeline import slugify

    slug = slugify(body.title)
    if s.scalar(select(BlogPost.id).where(BlogPost.slug == slug)) is not None:
        raise HTTPException(400, "a post with this title already exists")
    p = BlogPost(slug=slug, ai_generated=False, status=PostStatus.DRAFT, **body.model_dump())
    s.add(p)
    s.flush()
    record(s, admin.actor.name, "post.create", "post", p.id)
    s.commit()
    return post_admin(p)


@router.patch("/posts/{post_id}")
def update_post(
    post_id: int, body: PostIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    p = s.get(BlogPost, post_id)
    if p is None:
        raise HTTPException(404)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    record(s, admin.actor.name, "post.edit", "post", p.id)
    s.commit()
    if p.status == PostStatus.PUBLISHED:
        site.revalidate()
    return post_admin(p)


@router.post("/posts/{post_id}/decision")
def decide_post(
    post_id: int,
    body: dict[str, bool],
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    p = s.get(BlogPost, post_id)
    if p is None:
        raise HTTPException(404)
    from crayonlark.agents.website_content import PostOut, WebsiteContentOut, problems

    if body.get("approve"):
        check = WebsiteContentOut(
            public_description_md="",
            post=PostOut(
                title=p.title[:120],
                excerpt=p.excerpt[:300],
                body_md=p.body_md[:8000],
                seo_title=p.seo_title[:70],
                seo_description=p.seo_description[:160],
            ),
        )
        hits = problems(check, site.blocklist.extra_terms(s))
        if hits:
            raise HTTPException(400, f"fix first: {hits}")
    approvals.decide_post(s, p, bool(body.get("approve")), admin.actor)
    s.commit()
    site.revalidate()
    return post_admin(p)


class Visibility(BaseModel):
    is_public: bool


@router.post("/books/{book_id}/website")
def set_visibility(
    book_id: int, body: Visibility, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    b.is_public = body.is_public
    record(s, admin.actor.name, "book.website", "book", b.id, {"is_public": body.is_public})
    s.commit()
    flows.after_site_change(b.id, publish_assets=body.is_public)
    return {"is_public": b.is_public}


@router.post("/books/{book_id}/free-printable")
def free_printable(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    try:
        value = site.make_free_printable(s, b, admin.actor.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    site.revalidate()
    return value


@router.get("/subscribers")
def subscribers(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    rows = list(s.scalars(select(Subscriber).order_by(Subscriber.created_at.desc()).limit(500)))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {
        "counts": counts,
        "free_printable": site.free_printable(s),
        "subscribers": [
            {
                "id": r.id,
                "email": r.email,
                "status": r.status,
                "source": r.source,
                "created_at": r.created_at,
                "confirmed_at": r.confirmed_at,
            }
            for r in rows
        ],
    }


@router.get("/subscribers.csv")
def subscribers_csv(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> Response:
    """Confirmed subscribers only (they gave double opt-in consent)."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["email", "confirmed_at", "source"])
    for r in s.scalars(
        select(Subscriber)
        .where(Subscriber.status == SubscriberStatus.CONFIRMED)
        .order_by(Subscriber.confirmed_at)
    ):
        w.writerow([r.email, r.confirmed_at.isoformat() if r.confirmed_at else "", r.source])
    record(s, admin.actor.name, "subscribers.export", "subscriber", "csv")
    s.commit()
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="subscribers.csv"'},
    )


@router.get("/messages")
def messages(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> list[dict]:
    rows = s.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(200))
    return [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "message": m.message,
            "spam": m.spam,
            "created_at": m.created_at,
        }
        for m in rows
    ]
