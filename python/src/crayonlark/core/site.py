"""Public website services: what the site may show, its images, email sign-ups and contact form.

Only books that are `live` AND `is_public` and posts that a human published are ever exposed.
"""

from __future__ import annotations

import io
import logging
import re
import secrets
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, blocklist, html_safe, pipeline, storage
from crayonlark.core.audit import record
from crayonlark.core.config import get_settings
from crayonlark.core.crypto import hash_ip
from crayonlark.core.enums import BookStatus, PostStatus, SubscriberStatus
from crayonlark.core.models import BlogPost, Book, ContactMessage, Subscriber
from crayonlark.integrations import smtp

log = logging.getLogger("crayonlark.site")
MEDIA_PREFIX = "/api/public/media/"
MIN_FORM_SECONDS = 3
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}$", re.I)


# --------------------------------------------------------------------------- serializers


def media_url(key: str | None) -> str | None:
    return f"{MEDIA_PREFIX}{key}" if key else None


def amazon_link(url: str | None) -> str | None:
    """Add the Associates tag to Amazon links (only on amazon.* hosts)."""
    tag = get_settings().amazon_associates_tag
    if not url or not tag:
        return url
    parts = urlparse(url)
    if "amazon." not in parts.netloc:
        return url
    q = [(k, v) for k, v in parse_qsl(parts.query) if k != "tag"] + [("tag", tag)]
    return urlunparse(parts._replace(query=urlencode(q)))


def ai_note(book: Book) -> str:
    if book.ai_interior_images or book.ai_cover_image:
        return "Artwork made with AI tools, then edited and checked by Crayonlark."
    return ""


def theme_slug(theme: str) -> str:
    return pipeline.slugify(theme)


def public_books_query() -> Any:
    return select(Book).where(Book.status == BookStatus.LIVE, Book.is_public.is_(True))


def book_out(b: Book) -> dict[str, Any]:
    kdp = next((lst for lst in b.listings if lst.platform == "kdp"), None)
    desc = b.public_description or (kdp.description if kdp else "")
    assets = b.public_assets or {}
    etsy_url = b.etsy_url or next(
        (
            lst.etsy.url
            for lst in b.listings
            if lst.platform == "etsy"
            and lst.etsy is not None
            and lst.etsy.state == "active"
            and lst.product_kind == "full_pdf"
        ),
        None,
    )
    return {
        "slug": b.slug,
        "title": b.title,
        "subtitle": b.subtitle,
        "series": b.series,
        "volume": b.volume,
        "age_min": b.age_min,
        "age_max": b.age_max,
        "themes": [t for t in (b.themes or []) if t != "demo"],
        "page_count": b.page_count or 0,
        "trim": b.trim,
        "description_html": html_safe.markdown_to_html(desc)
        if "<" not in desc
        else html_safe.clean(desc),
        "cover_url": media_url(assets.get("cover")),
        "preview_urls": [u for u in (media_url(k) for k in assets.get("previews", [])) if u],
        "amazon_url": amazon_link(b.amazon_url),
        "etsy_url": etsy_url,
        "live_at": b.live_at,
        "updated_at": b.updated_at,
        "ai_note": ai_note(b),
    }


def reading_minutes(markdown: str) -> int:
    """About 200 words per minute, at least 1."""
    return max(1, round(len(markdown.split()) / 200))


def post_summary(p: BlogPost) -> dict[str, Any]:
    return {
        "slug": p.slug,
        "title": p.title,
        "excerpt": p.excerpt,
        "reading_minutes": reading_minutes(p.body_md),
        "published_at": p.published_at,
        "cover_url": media_url(p.cover_image_key),
    }


def post_out(session: Session, p: BlogPost) -> dict[str, Any]:
    books = []
    if p.book_id:
        b = session.scalar(public_books_query().where(Book.id == p.book_id))
        if b is not None:
            books.append(book_out(b))
    return {
        **post_summary(p),
        "html": html_safe.markdown_to_html(p.body_md),
        "seo_title": p.seo_title or p.title,
        "seo_description": p.seo_description or p.excerpt,
        "updated_at": p.updated_at,
        "books": books,
    }


def published_posts() -> Any:
    return select(BlogPost).where(BlogPost.status == PostStatus.PUBLISHED)


# --------------------------------------------------------------------------- assets


def _page_jpg(png: bytes, height: int = 1100) -> bytes:
    """A design on a white page (Letter proportions) for the website preview."""
    width = round(height * 8.5 / 11)
    page = PILImage.new("RGB", (width, height), "white")
    art = PILImage.open(io.BytesIO(png)).convert("RGB")
    art.thumbnail((width - 120, height - 120))
    page.paste(art, ((width - art.width) // 2, (height - art.height) // 2))
    out = io.BytesIO()
    page.save(out, format="JPEG", quality=82, optimize=True)
    return out.getvalue()


def publish_assets(session: Session, book: Book) -> dict[str, Any]:
    """Copy the front cover and up to 4 sample pages into the public-assets bucket."""
    assets: dict[str, Any] = {"previews": []}
    cover = next((c for c in reversed(book.covers) if c.approval == "approved"), None)
    if cover is not None and cover.thumb_key:
        key = f"books/{book.slug}/cover.jpg"
        storage.put_bytes(
            "public", key, storage.get_bytes("outputs", cover.thumb_key), "image/jpeg"
        )
        assets["cover"] = key
    for n, img in enumerate(pipeline.approved_images(book)[:4], start=1):
        if img.cleaned_key:
            key = f"books/{book.slug}/page-{n}.jpg"
            storage.put_bytes(
                "public",
                key,
                _page_jpg(storage.get_bytes("processed", img.cleaned_key)),
                "image/jpeg",
            )
            assets["previews"].append(key)
    book.public_assets = assets
    return assets


def revalidate() -> bool:
    s = get_settings()
    try:
        r = httpx.post(
            f"{s.web_internal_url.rstrip('/')}/revalidate",
            headers={"x-revalidate-secret": s.revalidate_secret},
            timeout=10,
        )
        return r.status_code == 200
    except httpx.HTTPError as exc:
        log.warning("revalidate failed: %s", exc)
        return False


# --------------------------------------------------------------------------- content agent


def draft_content(session: Session, book: Book) -> BlogPost:
    """Run the website content agent: public description (if empty) + a blog post draft."""
    from crayonlark.agents import website_content

    out = website_content.run(book, len(pipeline.approved_images(book)))
    hits = website_content.problems(out, blocklist.extra_terms(session))
    if not book.public_description and not hits:
        book.public_description = out.public_description_md
    p = out.post
    slug = pipeline.slugify(p.title)
    n = 2
    while session.scalar(select(BlogPost.id).where(BlogPost.slug == slug)) is not None:
        slug, n = f"{pipeline.slugify(p.title)}-{n}", n + 1
    post = BlogPost(
        slug=slug,
        title=p.title,
        excerpt=p.excerpt,
        body_md=p.body_md,
        seo_title=p.seo_title,
        seo_description=p.seo_description,
        book_id=book.id,
        cover_image_key=(book.public_assets or {}).get("cover"),
        ai_generated=book.ai_text,
        status=PostStatus.AWAITING_APPROVAL,
    )
    session.add(post)
    session.flush()
    if hits:
        record(session, "agent:website_content", "post.blocklist", "post", post.id, hits)
    return post


# --------------------------------------------------------------------------- forms


class FormRejected(ValueError):
    pass


def check_form(website: str, started_at: int | None, now_ms: int | None = None) -> None:
    """Honeypot + time trap. Raises FormRejected for bots."""
    now_ms = now_ms or int(time.time() * 1000)
    if website.strip():
        raise FormRejected("spam")
    if started_at is None or now_ms - started_at < MIN_FORM_SECONDS * 1000:
        raise FormRejected("too fast")


def verify_turnstile(token: str | None, ip: str) -> bool:
    secret = get_settings().turnstile_secret
    if not secret:
        return True
    if not token:
        return False
    try:
        r = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token, "remoteip": ip},
            timeout=10,
        )
        return bool(r.json().get("success"))
    except httpx.HTTPError:
        return False


def subscribe(session: Session, email: str, ip: str) -> Subscriber | None:
    """Create/refresh a pending subscriber and send the confirmation email (double opt-in)."""
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")
    sub = session.scalar(select(Subscriber).where(Subscriber.email == email))
    if sub is None:
        sub = Subscriber(email=email, token=secrets.token_urlsafe(32), ip_hash=hash_ip(ip))
        session.add(sub)
    elif sub.status == SubscriberStatus.CONFIRMED:
        send_download_email(sub)  # already confirmed: just resend the link
        return sub
    else:
        sub.status = SubscriberStatus.PENDING
    session.flush()
    site = get_settings().public_site_url.rstrip("/")
    link = f"{site}/free-printables/confirm?token={sub.token}"
    smtp.send(
        email,
        "Confirm your free Crayonlark coloring pages",
        f"Hi!\n\nPlease confirm your email to get your free coloring pages:\n{link}\n\n"
        "If you did not ask for this, just ignore this email.\n\nCrayonlark",
    )
    return sub


def send_download_email(sub: Subscriber) -> None:
    site = get_settings().public_site_url.rstrip("/")
    smtp.send(
        sub.email,
        "Your free Crayonlark coloring pages",
        f"Here is your download link:\n{site}/api/public/download?token={sub.token}\n\n"
        f"Unsubscribe any time: {site}/unsubscribe?token={sub.token}\n\nCrayonlark",
    )


def confirm(session: Session, token: str) -> Subscriber:
    sub = session.scalar(select(Subscriber).where(Subscriber.token == token))
    if sub is None or sub.status == SubscriberStatus.UNSUBSCRIBED:
        raise ValueError("This link is not valid any more.")
    if sub.status != SubscriberStatus.CONFIRMED:
        sub.status, sub.confirmed_at = SubscriberStatus.CONFIRMED, datetime.now(UTC)
        send_download_email(sub)
    return sub


def unsubscribe(session: Session, token: str) -> None:
    sub = session.scalar(select(Subscriber).where(Subscriber.token == token))
    if sub is not None:
        sub.status = SubscriberStatus.UNSUBSCRIBED


def contact(session: Session, name: str, email: str, message: str, ip: str) -> ContactMessage:
    if not EMAIL_RE.match(email.strip()) or not message.strip() or not name.strip():
        raise ValueError("Please fill in your name, a valid email and a message.")
    spam = bool(re.search(r"https?://", message)) and message.count("http") > 2
    msg = ContactMessage(
        name=name.strip()[:200],
        email=email.strip()[:255],
        message=message.strip()[:5000],
        spam=spam,
        ip_hash=hash_ip(ip),
    )
    session.add(msg)
    session.flush()
    if not spam:
        owner = get_settings().owner_email
        if owner:
            smtp.send(
                owner,
                f"Crayonlark contact: {msg.name}",
                f"From: {msg.name} <{msg.email}>\n\n{msg.message}",
                reply_to=msg.email,
            )
    return msg


# --------------------------------------------------------------------------- free printable


def free_printable(session: Session | None = None) -> dict[str, Any] | None:
    value = app_settings.get("free_printable_key", session)
    return value if isinstance(value, dict) and value.get("key") else None


def make_free_printable(session: Session, book: Book, actor: str, n: int = 3) -> dict[str, Any]:
    imgs = pipeline.approved_images(book)[:n]
    if not imgs:
        raise ValueError("book has no approved images")
    slug = f"free-sample-{book.slug}"
    keys = pipeline.build_etsy_pdfs(
        session,
        book,
        [
            {
                "slug": slug,
                "title": f"Free coloring pages from {book.title}"[:80],
                "image_ids": [i.id for i in imgs],
                "activities": False,
            }
        ],
    )[slug]
    preview = None
    if imgs[0].cleaned_key:
        preview = "free/preview.jpg"
        storage.put_bytes(
            "public",
            preview,
            _page_jpg(storage.get_bytes("processed", imgs[0].cleaned_key)),
            "image/jpeg",
        )
    value = {
        "key": keys["letter"],
        "a4": keys.get("a4"),
        "book_id": book.id,
        "title": f"Free coloring pages from {book.title}",
        "pages": len(imgs),
        "preview": preview,
    }
    app_settings.set_value("free_printable_key", value, actor, session)
    return value
