"""KDP weekly new-title limit: 2 paperbacks + 2 hardcovers per week (configurable),
week resets Sunday 00:00 UTC. A slot is consumed when a book's KDP pack is assigned a week.
The planner never assigns more than the limit; it pushes the book to the next free week.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from crayonlark.core.config import get_settings
from crayonlark.core.enums import BookFormat
from crayonlark.core.models import Book


def week_start(now: datetime | None = None) -> date:
    """Sunday (UTC) of the week containing `now`."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    days_since_sunday = (now.weekday() + 1) % 7  # Mon=0 … Sun=6  →  Sun=0, Mon=1 …
    return now.date() - timedelta(days=days_since_sunday)


def limit_for(fmt: str) -> int:
    s = get_settings()
    return s.kdp_weekly_hardcovers if fmt == BookFormat.HARDCOVER else s.kdp_weekly_paperbacks


def pick_week(used: dict[date, int], limit: int, first_week: date, horizon: int = 52) -> date:
    """First week (from first_week on) with fewer than `limit` slots used. Pure function."""
    if limit <= 0:
        raise ValueError("weekly limit is 0")
    for i in range(horizon):
        wk = first_week + timedelta(weeks=i)
        if used.get(wk, 0) < limit:
            return wk
    raise ValueError("no free KDP slot within a year")


def used_by_week(session: Session, fmt: str, from_week: date) -> dict[date, int]:
    rows = session.execute(
        select(Book.kdp_week_start, func.count(Book.id))
        .where(Book.format == fmt, Book.kdp_week_start >= from_week)
        .group_by(Book.kdp_week_start)
    ).all()
    return {wk: n for wk, n in rows if wk is not None}


def assign_slot(session: Session, book: Book, now: datetime | None = None) -> date:
    """Give the book a KDP week (idempotent). Serialised with an advisory lock."""
    if book.kdp_week_start is not None:
        return book.kdp_week_start
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(424242)"))
    first = week_start(now)
    wk = pick_week(used_by_week(session, book.format, first), limit_for(book.format), first)
    book.kdp_week_start = wk
    session.flush()
    return wk


def summary(session: Session, now: datetime | None = None) -> dict[str, Any]:
    wk = week_start(now)
    pb = used_by_week(session, BookFormat.PAPERBACK, wk)
    hc = used_by_week(session, BookFormat.HARDCOVER, wk)
    lp, lh = limit_for(BookFormat.PAPERBACK), limit_for(BookFormat.HARDCOVER)
    return {
        "week_start": wk.isoformat(),
        "resets_at": datetime.combine(wk + timedelta(days=7), datetime.min.time(), UTC).isoformat(),
        "paperback_used": pb.get(wk, 0),
        "paperback_limit": lp,
        "paperback_left": max(0, lp - pb.get(wk, 0)),
        "hardcover_used": hc.get(wk, 0),
        "hardcover_limit": lh,
        "hardcover_left": max(0, lh - hc.get(wk, 0)),
        "upcoming": [
            {
                "week_start": (wk + timedelta(weeks=i)).isoformat(),
                "paperback": pb.get(wk + timedelta(weeks=i), 0),
                "hardcover": hc.get(wk + timedelta(weeks=i), 0),
            }
            for i in range(1, 5)
        ],
    }
