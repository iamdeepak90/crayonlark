"""Public website API (no auth). Only live + public books and human-published posts."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import client_ip, db
from crayonlark.core import site, storage
from crayonlark.core.enums import SubscriberStatus
from crayonlark.core.models import BlogPost, Book, Subscriber
from crayonlark.core.sessions import rate_limited

router = APIRouter(prefix="/api/public", tags=["public"])
MEDIA_KEY = re.compile(r"^[a-z0-9][a-z0-9/_.-]{0,300}\.(jpg|png|webp)$")
SUBSCRIBE_MESSAGE = "Thanks! Check your inbox for a confirmation email (and your spam folder)."


@router.get("/books")
def books(age: int | None = None, theme: str = "", s: Session = Depends(db)) -> dict:
    q = site.public_books_query().order_by(Book.live_at.desc().nulls_last(), Book.id.desc())
    if age is not None:
        q = q.where(Book.age_min <= age, Book.age_max >= age)
    rows = list(s.scalars(q))
    if theme:
        rows = [b for b in rows if theme in {site.theme_slug(t) for t in (b.themes or [])}]
    return {"books": [site.book_out(b) for b in rows]}


@router.get("/books/{slug}")
def book(slug: str, s: Session = Depends(db)) -> dict:
    b = s.scalar(site.public_books_query().where(Book.slug == slug))
    if b is None:
        raise HTTPException(404, "not found")
    related_q = site.public_books_query().where(Book.id != b.id).limit(4)
    if b.series:
        related_q = related_q.order_by((Book.series == b.series).desc(), Book.id.desc())
    return {**site.book_out(b), "related": [site.book_out(r) for r in s.scalars(related_q)]}


@router.get("/filters")
def filters(s: Session = Depends(db)) -> dict:
    themes: dict[str, dict[str, Any]] = {}
    ages: set[int] = set()
    for b in s.scalars(site.public_books_query()):
        for t in b.themes or []:
            if t == "demo":
                continue
            row = themes.setdefault(
                site.theme_slug(t), {"slug": site.theme_slug(t), "name": t.title(), "count": 0}
            )
            row["count"] += 1
        ages.update(range(b.age_min, b.age_max + 1))
    return {"themes": sorted(themes.values(), key=lambda r: r["name"]), "ages": sorted(ages)}


@router.get("/posts")
def posts(limit: int = 50, s: Session = Depends(db)) -> dict:
    rows = s.scalars(
        site.published_posts().order_by(BlogPost.published_at.desc()).limit(min(limit, 100))
    )
    return {"posts": [site.post_summary(p) for p in rows]}


@router.get("/posts/{slug}")
def post(slug: str, s: Session = Depends(db)) -> dict:
    p = s.scalar(site.published_posts().where(BlogPost.slug == slug))
    if p is None:
        raise HTTPException(404, "not found")
    return site.post_out(s, p)


@router.get("/sitemap")
def sitemap(s: Session = Depends(db)) -> dict:
    return {
        "books": [
            {"slug": b.slug, "updated_at": b.updated_at}
            for b in s.scalars(site.public_books_query())
        ],
        "posts": [
            {"slug": p.slug, "updated_at": p.updated_at} for p in s.scalars(site.published_posts())
        ],
    }


@router.get("/free-printable")
def free_printable(s: Session = Depends(db)) -> dict:
    fp = site.free_printable(s)
    if fp is None:
        return {"available": False, "title": "", "pages": 0, "preview_url": None}
    return {
        "available": True,
        "title": fp["title"],
        "pages": fp["pages"],
        "preview_url": site.media_url(fp.get("preview")),
    }


class SubscribeIn(BaseModel):
    email: str = Field(max_length=255)
    website: str = ""
    started_at: int | None = None


@router.post("/subscribe")
def subscribe(body: SubscribeIn, request: Request, s: Session = Depends(db)) -> dict:
    ip = client_ip(request)
    try:
        site.check_form(body.website, body.started_at)
    except site.FormRejected:
        return {"ok": True, "message": SUBSCRIBE_MESSAGE}  # don't tell bots
    if rate_limited(f"subscribe:{ip}", 5, 3600):
        raise HTTPException(429, "Too many tries. Please try again later.")
    try:
        site.subscribe(s, body.email, ip)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    return {"ok": True, "message": SUBSCRIBE_MESSAGE}


@router.get("/confirm")
def confirm(token: str, s: Session = Depends(db)) -> dict:
    try:
        sub = site.confirm(s, token)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    return {"ok": True, "download_url": f"/api/public/download?token={sub.token}"}


@router.get("/download")
def download(token: str, s: Session = Depends(db)) -> Response:
    sub = s.scalar(select(Subscriber).where(Subscriber.token == token))
    fp = site.free_printable(s)
    if sub is None or sub.status != SubscriberStatus.CONFIRMED or fp is None:
        raise HTTPException(404, "This download link is not valid.")
    return Response(
        storage.get_bytes("outputs", fp["key"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="crayonlark-free-coloring-pages.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/unsubscribe")
def unsubscribe(token: str, s: Session = Depends(db)) -> dict:
    site.unsubscribe(s, token)
    s.commit()
    return {"ok": True}


class ContactIn(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=255)
    message: str = Field(max_length=5000)
    website: str = ""
    started_at: int | None = None
    turnstile_token: str | None = None


@router.post("/contact")
def contact(body: ContactIn, request: Request, s: Session = Depends(db)) -> dict:
    ip = client_ip(request)
    try:
        site.check_form(body.website, body.started_at)
    except site.FormRejected:
        return {"ok": True}
    if rate_limited(f"contact:{ip}", 5, 3600):
        raise HTTPException(429, "Too many messages. Please try again later.")
    if not site.verify_turnstile(body.turnstile_token, ip):
        raise HTTPException(400, "Please complete the check and try again.")
    try:
        msg = site.contact(s, body.name, body.email, body.message, ip)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    if not msg.spam:
        from crayonlark.core.notify import notify

        notify(f"✉️ Contact form: {msg.name} <{msg.email}>\n{msg.message[:500]}", kind="contact")
    return {"ok": True}


@router.get("/media/{key:path}")
def media(key: str) -> Response:
    if not MEDIA_KEY.match(key) or ".." in key:
        raise HTTPException(404)
    try:
        data = storage.get_bytes("public", key)
    except Exception as exc:
        raise HTTPException(404) from exc
    ctype = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[key.rsplit(".", 1)[1]]
    return Response(
        data, media_type=ctype, headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )
