"""Etsy + Pinterest: pure payload rules, PKCE, pin scheduling and a mocked end-to-end run."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from crayonlark.core import approvals, marketing, storage
from crayonlark.core.actors import HumanActor
from crayonlark.core.config import get_settings
from crayonlark.core.enums import EtsyStatus, ListingStatus, PinStatus
from crayonlark.core.models import Book, Listing, Pin
from crayonlark.core.state_machine import GateError
from crayonlark.integrations import etsy, oauth, pinterest


def test_pkce_challenge_is_s256_base64url() -> None:
    import base64
    import hashlib

    verifier = "a" * 64
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    got = oauth.challenge_for(verifier)
    assert got == expected.decode() and len(got) == 43 and "=" not in got


def test_etsy_draft_form_rules() -> None:
    form = etsy.draft_form(
        title="Ocean Coloring: Fish & Whales & Crabs: Kids $5",
        description="Designed by Crayonlark.",
        price_cents=499,
        tags=["Ocean Coloring!", "ocean coloring", *[f"tag {i}" for i in range(14)]],
        taxonomy_id=1234,
        when_made="2020_2026",
    )
    assert form["who_made"] == "i_did" and form["type"] == "download"
    assert form["is_supply"] == "false" and form["price"] == "4.99"
    assert form["title"].count("&") == 1 and form["title"].count(":") == 1
    assert "$" not in form["title"]
    tags = form["tags"].split(",")
    assert len(tags) == 13 and tags[0] == "ocean coloring"
    assert etsy.draft_problems(form) == []
    bad = dict(form, taxonomy_id="0", description="Handmade pages")
    errs = " ".join(etsy.draft_problems(bad))
    assert "taxonomy id" in errs and "handmade" in errs and "Designed by" in errs


def test_pin_payload_marks_ai_art() -> None:
    body = pinterest.pin_payload(
        board_id="1",
        title="t" * 150,
        description="d",
        link="https://x",
        alt_text="a",
        jpg=b"\xff\xd8",
        ai_art=True,
    )
    assert len(body["title"]) == 100
    assert body["media_source"]["source_type"] == "image_base64"
    assert body["ai_disclosures"] == {"values": ["AI_MODIFIED"]}
    assert "ai_disclosures" not in pinterest.pin_payload(
        board_id="1", title="t", description="", link="", alt_text="", jpg=b"x", ai_art=False
    )


def test_pin_slots_respect_daily_limit() -> None:
    now = datetime(2026, 11, 8, 10, tzinfo=UTC)
    taken = [datetime(2026, 11, 9, 14, tzinfo=UTC)] * 3
    slots = marketing.next_slots(taken, 7, 4, 13, 23, now, random.Random(1))
    per_day: dict[object, int] = {}
    for t in slots:
        assert 13 <= t.hour < 23 and t > now
        per_day[t.date()] = per_day.get(t.date(), 0) + 1
    assert per_day[datetime(2026, 11, 9).date()] == 1  # 3 already taken, limit 4
    assert all(n <= 4 for n in per_day.values()) and len(slots) == 7


@pytest.fixture
def shop(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    for k, v in {
        "ETSY_API_KEY": "key",
        "ETSY_SHARED_SECRET": "sec",
        "ETSY_SHOP_ID": "42",
        "ETSY_TAXONOMY_ID": "1234",
        "PINTEREST_APP_ID": "app",
        "PINTEREST_APP_SECRET": "psec",
    }.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _book_with_listing(s) -> Book:  # type: ignore[no-untyped-def]
    book = Book(
        title="Ocean Fun",
        slug="ocean-fun",
        ai_interior_images=True,
        age_min=3,
        age_max=6,
        themes=["ocean"],
    )
    s.add(book)
    s.flush()
    keys = {"letter": "ocean-fun/etsy/a-letter.pdf", "a4": "ocean-fun/etsy/a-a4.pdf"}
    mocks = [f"ocean-fun/mockups/1/etsy-0{i}.jpg" for i in (1, 2)] + [
        "ocean-fun/mockups/1/pin-01.jpg"
    ]
    for k in [*keys.values(), *mocks]:
        storage.put_bytes("outputs", k, b"data", "application/octet-stream")
    s.add(
        Listing(
            book_id=book.id,
            platform="etsy",
            product_kind="full_pdf",
            title="Ocean Coloring Pages, Printable",
            description="Fun.\n\nDesigned by Crayonlark.",
            tags=[f"ocean tag {i}" for i in range(13)],
            price_cents=499,
            status=ListingStatus.APPROVED,
            file_keys=keys,
            mockup_keys=mocks,
        )
    )
    oauth.save_token(
        s, "etsy", {"access_token": "77.tok", "refresh_token": "r", "expires_in": 3600}
    )
    oauth.save_token(s, "pinterest", {"access_token": "ptok", "expires_in": 3600})
    s.flush()
    s.refresh(book)
    return book


@respx.mock
def test_etsy_draft_publish_and_pins(db, needs_storage, shop) -> None:  # type: ignore[no-untyped-def]
    base = "https://api.etsy.com/v3/application/shops/42/listings"
    create = respx.post(base).mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(201, json={"listing_id": 555, "state": "draft", "url": None}),
        ]
    )
    images = respx.post(f"{base}/555/images").mock(return_value=httpx.Response(201, json={}))
    files = respx.post(f"{base}/555/files").mock(return_value=httpx.Response(201, json={}))
    activate = respx.patch(f"{base}/555").mock(
        return_value=httpx.Response(
            200, json={"state": "active", "url": "https://www.etsy.com/listing/555/ocean"}
        )
    )
    with db() as s:
        book = _book_with_listing(s)
        ids = marketing.create_etsy_drafts(s, book)
        assert ids == [555] and book.etsy_status == EtsyStatus.ETSY_DRAFTS_CREATED
        assert create.call_count == 2 and images.call_count == 2 and files.call_count == 2
        req = create.calls.last.request
        assert req.headers["x-api-key"] == "key:sec"
        assert req.headers["authorization"] == "Bearer 77.tok"
        assert b"who_made=i_did" in req.content and b"type=download" in req.content
        names = [c.request.content for c in files.calls]
        assert b"a-letter.pdf" in names[0] and b"a-a4.pdf" in names[1]
        # Running again does not re-upload anything (idempotent).
        marketing.create_etsy_drafts(s, book)
        assert images.call_count == 2 and files.call_count == 2
        with pytest.raises(GateError):
            marketing.publish_etsy(s, book)
        assert activate.call_count == 0
        approvals.approve_etsy_publish(s, book, HumanActor.from_cli("test"))
        marketing.publish_etsy(s, book)
        assert activate.call_count == 1 and book.etsy_status == EtsyStatus.ETSY_PUBLISHED
        pins = marketing.plan_pins(s, book, now=datetime.now(UTC) - timedelta(days=2), seed=1)
        assert len(pins) == 1 and pins[0].link.endswith("/555/ocean")
        assert marketing.plan_pins(s, book) == []  # idempotent

    board = respx.post("https://api.pinterest.com/v5/boards").mock(
        return_value=httpx.Response(201, json={"id": "900"})
    )
    pin = respx.post("https://api.pinterest.com/v5/pins").mock(
        return_value=httpx.Response(201, json={"id": "p1"})
    )
    with db() as s:
        posted = marketing.post_due_pins(s)
        assert len(posted) == 1 and board.call_count == 1
        body = json.loads(pin.calls.last.request.content)
        assert body["board_id"] == "900" and body["ai_disclosures"]["values"] == ["AI_MODIFIED"]
        assert s.get(Pin, posted[0]).status == PinStatus.POSTED
