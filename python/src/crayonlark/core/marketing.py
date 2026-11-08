"""Phase 4 services: listing mockups, Etsy drafts → (human approval) → publish, Pinterest pins.

Etsy publish is gated: `publish_etsy` calls approvals.require_etsy_publish_approval() for every
listing right before activating it. Pins are only planned for listings that are already public.
"""

from __future__ import annotations

import random
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, storage
from crayonlark.core.actors import SYSTEM
from crayonlark.core.approvals import require_etsy_publish_approval
from crayonlark.core.config import get_settings
from crayonlark.core.enums import EtsyStatus, ListingStatus, PinStatus
from crayonlark.core.models import Book, EtsyListing, Listing, Pin, PinterestBoard
from crayonlark.core.state_machine import transition_etsy
from crayonlark.integrations import etsy, pinterest
from crayonlark.print import mockups

# --------------------------------------------------------------------------- mockups


def approved_etsy(book: Book) -> list[Listing]:
    return [
        lst
        for lst in book.listings
        if lst.platform == "etsy" and lst.status == ListingStatus.APPROVED
    ]


def short_name(lst: Listing) -> str:
    return lst.title.split(",")[0].split(" - ")[0].strip()[:48]


def build_mockups(session: Session, book: Book) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for lst in approved_etsy(book):
        letter = (lst.file_keys or {}).get("letter")
        if not letter:
            raise ValueError(f"listing {lst.id} has no PDF yet")
        with tempfile.TemporaryDirectory(prefix="mock-") as t:
            pdf = storage.download("outputs", letter, Path(t) / "letter.pdf")
            spec = mockups.MockupSpec(
                title=short_name(lst),
                kind=lst.product_kind,
                page_count=mockups.page_count(pdf),
                ages=f"{book.age_min}-{book.age_max}",
                theme=["sun", "sky", "coral"][lst.id % 3],
            )
            images = mockups.build_set(pdf, spec)
        keys = []
        for name, data in images.items():
            key = f"{book.slug}/mockups/{lst.id}/{name}"
            storage.put_bytes("outputs", key, data, "image/jpeg")
            keys.append(key)
        lst.mockup_keys = keys
        out[lst.id] = keys
    return out


def etsy_images(lst: Listing) -> list[str]:
    return [k for k in (lst.mockup_keys or []) if Path(k).name.startswith("etsy-")][:10]


def pin_images(lst: Listing) -> list[str]:
    return [k for k in (lst.mockup_keys or []) if Path(k).name.startswith("pin-")]


# --------------------------------------------------------------------------- Etsy


def etsy_form(lst: Listing) -> dict[str, str]:
    s = get_settings()
    return etsy.draft_form(
        title=lst.title,
        description=lst.description,
        price_cents=lst.price_cents,
        tags=list(lst.tags or []),
        taxonomy_id=s.etsy_taxonomy_id,
        when_made=s.etsy_when_made,
    )


def etsy_problems(book: Book) -> dict[int, list[str]]:
    out = {}
    for lst in approved_etsy(book):
        errs = etsy.draft_problems(etsy_form(lst))
        if not lst.file_keys:
            errs.append("PDF files not built yet")
        if not etsy_images(lst):
            errs.append("mockup images not built yet")
        if errs:
            out[lst.id] = errs
    return out


def create_etsy_drafts(session: Session, book: Book, client: etsy.Etsy | None = None) -> list[int]:
    """Create (or finish) one Etsy draft per approved Etsy listing. Idempotent: every step is
    recorded in EtsyListing.uploaded, so a retry continues where it stopped."""
    problems = etsy_problems(book)
    if problems:
        raise ValueError(f"cannot create Etsy drafts: {problems}")
    api = client or etsy.Etsy(session)
    ids = []
    for lst in approved_etsy(book):
        row = lst.etsy or EtsyListing(listing_id=lst.id, shop_id=api.shop_id)
        if lst.etsy is None:
            session.add(row)
            lst.etsy = row
        done: dict[str, Any] = dict(row.uploaded or {})
        try:
            if row.etsy_listing_id is None:
                created = api.create_draft(etsy_form(lst))
                row.etsy_listing_id = int(created["listing_id"])
                row.state = str(created.get("state", "draft"))
                row.url = created.get("url")
                session.flush()
            for rank, key in enumerate(etsy_images(lst), start=1):
                if f"image:{rank}" not in done:
                    alt = f"{short_name(lst)}: printable coloring page preview {rank}"
                    api.upload_image(
                        row.etsy_listing_id, storage.get_bytes("outputs", key), rank, alt
                    )
                    done[f"image:{rank}"] = key
                    row.uploaded = dict(done)
            for rank, paper in enumerate(("letter", "a4"), start=1):
                pdf_key = (lst.file_keys or {}).get(paper)
                if pdf_key and f"file:{paper}" not in done:
                    api.upload_file(
                        row.etsy_listing_id,
                        storage.get_bytes("outputs", pdf_key),
                        Path(pdf_key).name,
                        rank,
                    )
                    done[f"file:{paper}"] = pdf_key
                    row.uploaded = dict(done)
            row.error = None
        except Exception as exc:
            row.error = str(exc)[:2000]
            raise
        ids.append(row.etsy_listing_id)
    if book.etsy_status == EtsyStatus.NONE:
        transition_etsy(session, book, EtsyStatus.ETSY_DRAFTS_CREATED, SYSTEM)
    return ids


def publish_etsy(session: Session, book: Book, client: etsy.Etsy | None = None) -> list[str]:
    """Activate approved drafts. Raises GateError for any listing a human did not approve."""
    rows = [lst for lst in approved_etsy(book)]
    for lst in rows:
        require_etsy_publish_approval(lst)  # the gate, checked before any API call
    api = client or etsy.Etsy(session)
    urls = []
    for lst in rows:
        row = lst.etsy
        assert row is not None and row.etsy_listing_id is not None
        if row.state != "active":
            out = api.activate(row.etsy_listing_id)
            row.state = str(out.get("state", "active"))
            row.url = out.get("url") or row.url
            row.last_synced_at = datetime.now(UTC)
        urls.append(row.url or "")
    transition_etsy(session, book, EtsyStatus.ETSY_PUBLISHED, SYSTEM)
    return urls


# --------------------------------------------------------------------------- Pinterest


def next_slots(
    taken: list[datetime],
    n: int,
    per_day: int,
    start_h: int,
    end_h: int,
    now: datetime,
    rng: random.Random,
) -> list[datetime]:
    """n posting times from tomorrow on, at most `per_day` per UTC day (counting pins already
    scheduled), spread across the posting window with ±20 min jitter."""
    per_day = max(1, per_day)
    used: dict[Any, int] = {}
    for t in taken:
        used[t.date()] = used.get(t.date(), 0) + 1
    out: list[datetime] = []
    day = (now + timedelta(days=1)).date()
    window = max(1, end_h - start_h) * 60
    while len(out) < n:
        free = per_day - used.get(day, 0)
        for _ in range(max(0, free)):
            if len(out) >= n:
                break
            slot = used.get(day, 0)
            minute = round(window * (slot + 0.5) / per_day) + rng.randint(-20, 20)
            minute = min(max(0, minute), window - 1)
            out.append(
                datetime(day.year, day.month, day.day, start_h, tzinfo=UTC)
                + timedelta(minutes=minute)
            )
            used[day] = slot + 1
        day += timedelta(days=1)
    return sorted(out)


def board_for(session: Session, book: Book) -> PinterestBoard:
    name = (book.series or (book.themes or ["Coloring Pages"])[0]).title()
    name = f"{name} Coloring Pages" if "color" not in name.lower() else name
    board = None
    if book.niche_id is not None:
        board = session.scalar(
            select(PinterestBoard).where(PinterestBoard.niche_id == book.niche_id)
        )
    board = board or session.scalar(select(PinterestBoard).where(PinterestBoard.name == name))
    if board is None:
        board = PinterestBoard(name=name[:180], niche_id=book.niche_id)
        session.add(board)
        session.flush()
    return board


def plan_pins(
    session: Session, book: Book, now: datetime | None = None, seed: int | None = None
) -> list[Pin]:
    """Schedule pins for every public Etsy listing of the book (idempotent per image)."""
    now = now or datetime.now(UTC)
    cfg = app_settings.get("pinterest", session) or {}
    board = board_for(session, book)
    existing = {p.image_key for p in session.scalars(select(Pin).where(Pin.book_id == book.id))}
    todo = []
    for lst in approved_etsy(book):
        if lst.etsy is None or lst.etsy.state != "active" or not lst.etsy.url:
            continue
        for key in pin_images(lst):
            if key not in existing:
                todo.append((lst, key))
    taken = list(
        session.scalars(
            select(Pin.scheduled_at).where(
                Pin.status == PinStatus.SCHEDULED, Pin.scheduled_at > now
            )
        )
    )
    slots = next_slots(
        taken,
        len(todo),
        int(cfg.get("pins_per_day", 4)),
        int(cfg.get("start_hour_utc", 13)),
        int(cfg.get("end_hour_utc", 23)),
        now,
        random.Random(seed),
    )
    pins = []
    for (lst, key), when in zip(todo, slots, strict=True):
        text = lst.description.split("\n\n")[0]
        pins.append(
            Pin(
                book_id=book.id,
                listing_id=lst.id,
                board_id=board.id,
                title=short_name(lst)[:100],
                description=text[:800],
                link=lst.etsy.url if lst.etsy else "",
                image_key=key,
                scheduled_at=when,
            )
        )
    session.add_all(pins)
    session.flush()
    return pins


def post_due_pins(
    session: Session,
    now: datetime | None = None,
    limit: int = 1,
    client: pinterest.Pinterest | None = None,
) -> list[int]:
    """Post up to `limit` due pins (the beat runs every 15 minutes)."""
    now = now or datetime.now(UTC)
    due = list(
        session.scalars(
            select(Pin)
            .where(Pin.status == PinStatus.SCHEDULED, Pin.scheduled_at <= now)
            .order_by(Pin.scheduled_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    if not due:
        return []
    api = client or pinterest.Pinterest(session)
    posted = []
    for p in due:
        try:
            board = session.get(PinterestBoard, p.board_id) if p.board_id else None
            if board is None:
                raise ValueError("pin has no board")
            if not board.pinterest_board_id:
                board.pinterest_board_id = str(api.create_board(board.name)["id"])
            book = session.get(Book, p.book_id) if p.book_id else None
            body = pinterest.pin_payload(
                board_id=board.pinterest_board_id,
                title=p.title,
                description=p.description,
                link=p.link,
                alt_text=f"{p.title}: printable coloring page for kids",
                jpg=storage.get_bytes("outputs", p.image_key),
                ai_art=bool(book and book.ai_interior_images),
            )
            p.pinterest_pin_id = str(api.create_pin(body)["id"])
            p.status, p.posted_at, p.error = PinStatus.POSTED, now, None
            posted.append(p.id)
        except Exception as exc:  # one bad pin must not block the queue
            p.status, p.error = PinStatus.FAILED, str(exc)[:2000]
    return posted


def sync_boards(session: Session, client: pinterest.Pinterest | None = None) -> int:
    api = client or pinterest.Pinterest(session)
    n = 0
    for b in api.boards():
        row = session.scalar(select(PinterestBoard).where(PinterestBoard.name == b["name"]))
        if row is None:
            session.add(PinterestBoard(name=str(b["name"])[:180], pinterest_board_id=str(b["id"])))
            n += 1
        elif not row.pinterest_board_id:
            row.pinterest_board_id = str(b["id"])
    session.flush()
    return n
