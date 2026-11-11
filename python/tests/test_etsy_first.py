"""Etsy first, KDP second: daily queue, ranking, the two approval screens, Continue."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from crayonlark.core import marketing
from crayonlark.core.enums import BookStatus, ListingStatus
from crayonlark.core.models import Book, EtsyListing, Listing, Sale

from .test_api_admin import H, login

NOON = datetime(2026, 11, 11, 12, tzinfo=UTC)


def test_score_is_per_week_and_rewards_sales() -> None:
    assert marketing.score(1, 0, 0, 7) == 20.0
    assert marketing.score(2, 0, 0, 14) == 20.0  # same rate, twice as long live
    assert marketing.score(1, 0, 0, 2) == 20.0  # under a week counts as one week
    assert marketing.score(0, 10, 100, 7) == 50.0
    assert marketing.score(1, 0, 0, 7) > marketing.score(0, 5, 0, 7)


def _queued(s, n: int) -> list[Book]:  # type: ignore[no-untyped-def]
    out = []
    for i in range(n):
        b = Book(title=f"Queued {i}", slug=f"queued-{i}", status=BookStatus.ETSY_QUEUED)
        b.etsy_approved_at = NOON - timedelta(hours=n - i)  # first approved first
        s.add(b)
        out.append(b)
    s.flush()
    return out


def test_one_book_a_day_after_the_set_hour(db) -> None:  # type: ignore[no-untyped-def]
    with db() as s:
        books = _queued(s, 3)
        assert marketing.due_for_etsy(s, NOON) is None  # before 14:00 UTC
        afternoon = NOON.replace(hour=15)
        assert marketing.due_for_etsy(s, afternoon) is books[0]
        dates = marketing.planned_dates(s, afternoon)
        assert [dates[b.id] for b in books] == ["2026-11-11", "2026-11-12", "2026-11-13"]
        # today's book went live: nothing more today, the rest moves on a day each
        books[0].status, books[0].etsy_live_at = BookStatus.ON_ETSY, afternoon
        s.flush()
        assert marketing.due_for_etsy(s, afternoon) is None
        dates = marketing.planned_dates(s, afternoon)
        assert [dates[b.id] for b in books[1:]] == ["2026-11-12", "2026-11-13"]


def _on_etsy(s, title: str, views: int, favs: int, sales: int, days: int) -> Book:  # type: ignore[no-untyped-def]
    b = Book(title=title, slug=title.lower().replace(" ", "-"), status=BookStatus.ON_ETSY)
    b.etsy_live_at = datetime.now(UTC) - timedelta(days=days)
    s.add(b)
    s.flush()
    lst = Listing(
        book_id=b.id,
        platform="etsy",
        product_kind="full_pdf",
        title=title,
        status=ListingStatus.APPROVED,
    )
    s.add(lst)
    s.flush()
    s.add(
        EtsyListing(
            listing_id=lst.id,
            etsy_listing_id=1000 + b.id,
            state="active",
            views=views,
            favorites=favs,
        )
    )
    for i in range(sales):
        s.add(
            Sale(
                platform="etsy",
                source="etsy_api",
                external_id=f"{b.id}-{i}",
                sold_on=datetime.now(UTC).date(),
                book_id=b.id,
                units=1,
                revenue_cents=499,
            )
        )
    return b  # fmt: skip


def test_kdp_candidates_ranked_by_etsy_results(db, client: TestClient) -> None:  # type: ignore[no-untyped-def]
    login(client)
    with db() as s:
        quiet = _on_etsy(s, "Quiet Book", views=300, favs=1, sales=0, days=14)
        star = _on_etsy(s, "Star Book", views=120, favs=9, sales=3, days=10)
        skipped = _on_etsy(s, "Skipped Book", views=999, favs=50, sales=9, days=7)
        skipped.kdp_skipped = True
        ids = (quiet.id, star.id, skipped.id)
    r = client.get("/api/admin/kdp/candidates")
    assert r.status_code == 200, r.text
    data = r.json()
    assert [c["id"] for c in data["candidates"]] == [ids[1], ids[0]]  # best first, no skipped
    top = data["candidates"][0]
    assert top["stats"]["sales"] == 3 and top["stats"]["favorites"] == 9
    assert top["ready"] is False and data["per_month"] == 8 and "views" in data["score_help"]
    shown = client.get("/api/admin/kdp/candidates?show_skipped=true").json()["candidates"]
    assert shown[0]["id"] == ids[2]
    # not ready (no cover/interior yet): approval 2 is refused with a clear reason
    r = client.post(f"/api/admin/books/{ids[1]}/kdp/approve", json={}, headers=H)
    assert r.status_code == 400 and "cover" in r.json()["detail"]
    r = client.post(f"/api/admin/books/{ids[0]}/kdp/skip", json={"skip": True}, headers=H)
    assert r.json() == {"kdp_skipped": True}


def test_etsy_review_screen_and_queue(db, client: TestClient) -> None:  # type: ignore[no-untyped-def]
    login(client)
    with db() as s:
        _queued(s, 2)
        waiting = Book(title="Waiting Book", slug="waiting-book",
                       status=BookStatus.AWAITING_ETSY_APPROVAL)  # fmt: skip
        s.add(waiting)
        s.flush()
        wid = waiting.id
    data = client.get("/api/admin/etsy/review").json()
    assert [b["id"] for b in data["waiting"]] == [wid]
    assert len(data["queue"]) == 2 and data["queue"][0]["planned_for"]
    assert data["days_of_stock"] == 2.0 and data["low_stock"] is True
    # no Etsy listing yet: approval explains why
    r = client.post(f"/api/admin/books/{wid}/etsy/approve", headers=H)
    assert r.status_code == 400 and "no Etsy listing" in r.json()["detail"]
    r = client.put("/api/admin/etsy/daily", json={"per_day": 2, "hour_utc": 9}, headers=H)
    assert r.status_code == 200
    assert client.get("/api/admin/etsy/review").json()["days_of_stock"] == 1.0


def test_continue_restarts_the_stopped_step(db, client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import flows

    calls: list[str] = []
    monkeypatch.setattr(flows, "queue_listings", lambda b: calls.append("listings") or "j")
    monkeypatch.setattr(flows, "queue_cover", lambda b, o=None: calls.append("cover") or "j")
    login(client)
    with db() as s:
        b = Book(title="Stuck Book", slug="stuck-book", status=BookStatus.LISTING_DRAFT)
        s.add(b)
        s.flush()
        bid = b.id
    r = client.post(f"/api/admin/books/{bid}/continue", headers=H)
    assert r.status_code == 200 and r.json()["started"] == "writing the listing text"
    assert calls == ["cover", "listings"]
    with db() as s:
        s.get(Book, bid).status = BookStatus.ON_ETSY
    assert client.post(f"/api/admin/books/{bid}/continue", headers=H).status_code == 400
