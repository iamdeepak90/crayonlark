"""Phase 3 flow against Postgres + S3: cover → listings → pack, with gates and slot release."""

from __future__ import annotations

import zipfile
from io import BytesIO

import pytest

from crayonlark.core import approvals, pipeline, publishing, storage, telegram_actions
from crayonlark.core.actors import SYSTEM, HumanActor
from crayonlark.core.config import ASSETS_DIR, get_settings
from crayonlark.core.enums import BookStatus
from crayonlark.core.models import Book
from crayonlark.core.state_machine import GateError
from tests.conftest import needs_tools

SAMPLES = sorted((ASSETS_DIR / "sample_lineart").glob("*.png"))


def _built_book(s, me) -> Book:  # type: ignore[no-untyped-def]
    book = pipeline.create_book(
        s, "Publishing Test Book", me, ai_interior_images=True, themes=["shapes"]
    )
    approvals.approve_book_idea(s, book, me)
    for p in SAMPLES:
        pipeline.add_original(s, book, p.read_bytes(), filename=p.name)
    s.flush()
    for img in book.images:
        pipeline.run_image_qa(s, img, check_text=False)
        approvals.decide_image(s, img, True, me)
    pipeline.finish_qa_if_ready(s, book)
    approvals.approve_image_set(s, book, me, min_images=5)
    for img in book.images:
        pipeline.clean_one(s, img)
    pipeline.finish_cleaning_if_ready(s, book)
    pipeline.build_interior(s, book)
    return book


@needs_tools
def test_etsy_first_then_kdp(db, needs_storage, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Build → listing text, Etsy PDF, mockups → approval 1 (Etsy) → queue → live on Etsy →
    approval 2 (KDP) → pack with a weekly slot. No cover/listing gates in between."""
    from crayonlark.core import marketing
    from crayonlark.core.state_machine import transition

    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "777")
    me = HumanActor.from_cli("test")
    with db() as s:
        book = _built_book(s, me)
        transition(s, book, BookStatus.LISTING_DRAFT, SYSTEM)  # what the interior job does
        cover = publishing.build_cover(s, book)
        assert book.status == BookStatus.LISTING_DRAFT and cover.approval == "pending"
        assert cover.ai_generated  # hero comes from AI interior art
        rows = publishing.draft_listings(s, book)
        etsy = [r for r in rows if r.platform == "etsy"]
        assert len(etsy) == 1 and etsy[0].product_kind == "full_pdf"
        assert "AI tools" in etsy[0].description
        files = publishing.build_etsy_files(s, book)
        marketing.build_mockups(s, book)
        assert len(files) == 1 and etsy[0].mockup_keys
        transition(s, book, BookStatus.AWAITING_ETSY_APPROVAL, SYSTEM)  # the mockup job
        with pytest.raises(GateError):
            approvals.approve_for_etsy(s, book, SYSTEM)
        etsy[0].title = "Pokemon style coloring pages"  # a blocked word stops approval
        s.flush()
        with pytest.raises(ValueError, match="fix the etsy listing"):
            approvals.approve_for_etsy(s, book, me)
        etsy[0].title = "Shapes coloring pages"
        book_id, cover_id = book.id, cover.id

    # Approval 1 from Telegram (same gate function as the admin).
    assert "Approved for Etsy" in telegram_actions.handle_callback(f"etsyok:{book_id}:1", 777)

    with db() as s:
        book = s.get(Book, book_id)
        assert book.status == BookStatus.ETSY_QUEUED and book.etsy_approved_at
        lst = approvals.etsy_listing(book)
        assert lst.etsy.publish_approved_by == "telegram:777"
        assert book.kdp_week_start is None  # Etsy only so far: no KDP slot used
        with pytest.raises(ValueError, match="only books live on Etsy"):
            approvals.approve_for_kdp(s, book, me)
        transition(s, book, BookStatus.ON_ETSY, SYSTEM)  # the daily publisher (mocked here)
        with pytest.raises(GateError):
            approvals.approve_for_kdp(s, book, SYSTEM)
        approvals.approve_for_kdp(s, book, me)
        assert book.status == BookStatus.KDP_PACK_READY
        assert s.get(type(cover), cover_id).approval == "approved"
        assert approvals.kdp_listing(book).status == "approved"
        key = publishing.build_pack(s, book)
        assert book.kdp_week_start is not None

    with zipfile.ZipFile(BytesIO(storage.get_bytes("outputs", key))) as z:
        assert "Yes" in z.read("ai-disclosure.md").decode()

    with db() as s:
        book = s.get(Book, book_id)
        pipeline.archive_book(s, book, me)
        assert book.kdp_week_start is None  # never uploaded → slot released
    get_settings.cache_clear()
