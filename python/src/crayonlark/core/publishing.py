"""Phase 3 services: cover build, listing drafts, Etsy files per listing, KDP upload pack."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, blocklist, disclosure, kdp_slots, pipeline, storage
from crayonlark.core.actors import SYSTEM
from crayonlark.core.config import get_settings
from crayonlark.core.enums import BookStatus, ListingStatus
from crayonlark.core.models import Book, Cover, Image, Listing
from crayonlark.core.state_machine import transition
from crayonlark.print import colorize, kdp_pack
from crayonlark.print.activities import build_activities
from crayonlark.print.cover.render import THEMES, CoverSpec, render

THEME_ORDER = list(THEMES)


# --------------------------------------------------------------------------- cover


def build_cover(session: Session, book: Book, options: dict[str, Any] | None = None) -> Cover:
    options = dict(options or {})
    if not book.page_count:
        raise ValueError("build the interior first (page count unknown)")
    approved = pipeline.approved_images(book)
    if not approved:
        raise ValueError("no approved images")
    version = (
        session.scalar(select(func.max(Cover.version)).where(Cover.book_id == book.id)) or 0
    ) + 1
    hero = next((i for i in approved if i.id == options.get("hero_image_id")), None)
    hero = hero or approved[(version - 1) % len(approved)]
    assert hero.cleaned_key
    hero_png = storage.get_bytes("processed", hero.cleaned_key)
    thumbs = [
        storage.get_bytes("processed", i.cleaned_key)
        for i in approved
        if i.id != hero.id and i.cleaned_key
    ][:3]
    theme = options.get("theme") or THEME_ORDER[(version - 1) % len(THEME_ORDER)]
    n_acts = len(build_activities(book.activity_plan or {}, seed=book.id))
    bullets = [f"{len(approved)} one-sided coloring pages with thick, easy lines"]
    if n_acts:
        bullets.append(f"{n_acts} bonus activity pages with answers")
    bullets.append("Large 8.5 x 11 in pages" if book.trim == "8.5x11" else "8.5 x 8.5 in pages")
    bullets.append("Single-sided pages: no bleed-through")
    spec = CoverSpec(
        title=options.get("title") or book.title,
        subtitle=options.get("subtitle", book.subtitle),
        trim=book.trim,
        page_count=book.page_count,
        paper=book.paper,
        ages=f"{book.age_min}-{book.age_max}",
        hero_png=colorize.colorize(hero_png, seed=version),
        thumbs_png=thumbs,
        blurb=options.get("blurb")
        or (
            "Big, friendly pictures with thick lines that little hands can color. Every picture "
            "sits on its own page, so markers never bleed onto the next one."
        ),
        bullets=bullets,
        series=book.series,
        theme=theme,
        spine_text_min_pages=get_settings().spine_text_min_pages,
    )
    out = render(spec)
    if not out.report.ok:
        raise ValueError("cover failed validation: " + "; ".join(out.report.errors))
    base = f"{book.slug}/cover-v{version}"
    storage.put_bytes("outputs", f"{base}.pdf", out.pdf, "application/pdf")
    storage.put_bytes("outputs", f"{base}-preview.png", out.preview_png, "image/png")
    storage.put_bytes("outputs", f"{base}-thumb.jpg", out.thumb_jpg, "image/jpeg")
    storage.put_bytes("outputs", f"{base}-phone.jpg", out.phone_jpg, "image/jpeg")
    cover = Cover(
        book_id=book.id,
        version=version,
        template="classic",
        options={**options, "theme": theme, "hero_image_id": hero.id},
        hero_image_id=hero.id,
        ai_generated=bool(book.ai_cover_image or (hero.ai_generated and book.ai_interior_images)),
        width_in=out.geometry.width,
        height_in=out.geometry.height,
        spine_in=out.geometry.spine,
        pdf_key=f"{base}.pdf",
        thumb_key=f"{base}-thumb.jpg",
        preview_key=f"{base}-phone.jpg",
    )
    session.add(cover)
    session.flush()
    if book.status == BookStatus.BUILDING:
        transition(session, book, BookStatus.AWAITING_COVER_APPROVAL, SYSTEM)
    return cover


def latest_cover(book: Book) -> Cover | None:
    return book.covers[-1] if book.covers else None


# --------------------------------------------------------------------------- listings


def draft_listings(session: Session, book: Book) -> list[Listing]:
    from crayonlark.agents import listing as listing_agent

    rows = listing_agent.run(session, book)
    if book.status == BookStatus.LISTING_DRAFT:
        transition(session, book, BookStatus.AWAITING_LISTING_APPROVAL, SYSTEM)
    return rows


def listing_problems(session: Session, book: Book) -> dict[int, dict[str, list[str]]]:
    """Blocklist hits per listing id (approval is refused while any exist)."""
    from crayonlark.agents.listing import blocklist_hits

    extra = blocklist.extra_terms(session)
    out = {}
    for lst in book.listings:
        hits = blocklist_hits(lst, extra)
        if lst.platform == "kdp" and lst.price_cents < 999:
            hits["price"] = ["KDP price must be at least $9.99"]
        if lst.platform == "etsy" and len(lst.tags or []) > 13:
            hits["tags"] = ["Etsy allows at most 13 tags"]
        if hits:
            out[lst.id] = hits
    return out


# --------------------------------------------------------------------------- Etsy files


def etsy_product(lst: Listing, book: Book) -> dict[str, Any]:
    kind = lst.product_kind
    return {
        "slug": f"{book.slug}-{kind.replace('_', '-')}-{lst.id}",
        "title": lst.title.split(",")[0][:80],
        "image_ids": [] if kind == "activity_pack" else (lst.page_selection or None),
        "activities": kind in ("bundle", "activity_pack"),
    }


def build_etsy_files(session: Session, book: Book) -> dict[int, dict[str, str]]:
    listings = [
        lst
        for lst in book.listings
        if lst.platform == "etsy" and lst.status == ListingStatus.APPROVED
    ]
    products = [etsy_product(lst, book) for lst in listings]
    keys = pipeline.build_etsy_pdfs(session, book, products) if products else {}
    out = {}
    for lst, prod in zip(listings, products, strict=True):
        lst.file_keys = keys[prod["slug"]]
        out[lst.id] = lst.file_keys
    return out


# --------------------------------------------------------------------------- KDP pack


def build_pack(session: Session, book: Book, now: datetime | None = None) -> str:
    kdp = next(
        (
            lst
            for lst in book.listings
            if lst.platform == "kdp" and lst.status == ListingStatus.APPROVED
        ),
        None,
    )
    if kdp is None:
        raise ValueError("KDP listing is not approved")
    cover = next((c for c in reversed(book.covers) if c.approval == "approved"), None)
    if cover is None or not cover.pdf_key or not book.interior_key:
        raise ValueError("approved cover and interior are required")
    week = kdp_slots.assign_slot(session, book, now or datetime.now(UTC))
    zip_bytes = kdp_pack.build_zip(
        book,
        kdp,
        interior_pdf=storage.get_bytes("outputs", book.interior_key),
        cover_pdf=storage.get_bytes("outputs", cover.pdf_key),
        ai_disclosure_md=disclosure.kdp_markdown(book, cover.ai_generated),
        week_start=week,
        thumb_jpg=storage.get_bytes("outputs", cover.thumb_key) if cover.thumb_key else None,
    )
    key = f"{book.slug}/kdp-pack-{book.slug}.zip"
    storage.put_bytes("outputs", key, zip_bytes, "application/zip")
    book.pack_key = key
    return key


def cover_files(cover: Cover) -> dict[str, str]:
    base = Path(cover.pdf_key or "").with_suffix("").as_posix()
    return {
        "pdf": cover.pdf_key or "",
        "preview": f"{base}-preview.png",
        "thumb": cover.thumb_key or "",
        "phone": cover.preview_key or "",
    }


def images_by_id(session: Session, ids: list[int]) -> dict[int, Image]:
    return {i.id: i for i in session.scalars(select(Image).where(Image.id.in_(ids)))}


def setting_images_min(session: Session) -> int:
    return int((app_settings.get("images_per_book", session) or {}).get("min", 25))
