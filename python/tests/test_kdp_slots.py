from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from crayonlark.core import kdp_slots
from crayonlark.core.models import Book


def test_week_starts_sunday_utc() -> None:
    # Sunday 2026-11-08 00:00 UTC starts a week
    assert kdp_slots.week_start(datetime(2026, 11, 8, 0, 0, tzinfo=UTC)) == date(2026, 11, 8)
    # Saturday 23:59 UTC is still the previous week
    assert kdp_slots.week_start(datetime(2026, 11, 7, 23, 59, tzinfo=UTC)) == date(2026, 11, 1)
    # Wednesday
    assert kdp_slots.week_start(datetime(2026, 11, 11, 12, tzinfo=UTC)) == date(2026, 11, 8)
    # timezone-aware input from India (UTC+5:30), Sunday 03:00 IST = Saturday 21:30 UTC
    from datetime import timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    assert kdp_slots.week_start(datetime(2026, 11, 8, 3, 0, tzinfo=ist)) == date(2026, 11, 1)


def test_pick_week_never_exceeds_limit() -> None:
    w0 = date(2026, 11, 8)
    used = {w0: 2, date(2026, 11, 15): 1}
    assert kdp_slots.pick_week(used, 2, w0) == date(2026, 11, 15)
    assert kdp_slots.pick_week({}, 2, w0) == w0
    with pytest.raises(ValueError):
        kdp_slots.pick_week({}, 0, w0)


def test_assign_slots_two_per_week(db) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 11, 10, tzinfo=UTC)
    with db() as s:
        books = [Book(title=f"b{i}", slug=f"b{i}") for i in range(5)]
        hard = Book(title="h", slug="h", format="hardcover")
        s.add_all([*books, hard])
        s.flush()
        weeks = [kdp_slots.assign_slot(s, b, now) for b in books]
        assert weeks == [date(2026, 11, 8)] * 2 + [date(2026, 11, 15)] * 2 + [date(2026, 11, 22)]
        assert kdp_slots.assign_slot(s, books[0], now) == date(2026, 11, 8)  # idempotent
        assert kdp_slots.assign_slot(s, hard, now) == date(2026, 11, 8)  # separate limit
        summ = kdp_slots.summary(s, now)
        assert summ["paperback_left"] == 0 and summ["hardcover_left"] == 1
