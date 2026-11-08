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
def test_cover_listings_pack(db, needs_storage, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "777")
    me = HumanActor.from_cli("test")
    with db() as s:
        book = _built_book(s, me)
        cover = publishing.build_cover(s, book)
        assert book.status == BookStatus.AWAITING_COVER_APPROVAL
        assert cover.ai_generated  # hero comes from AI interior art
        with pytest.raises(GateError):
            approvals.decide_cover(s, cover, True, SYSTEM)
        book_id, cover_id = book.id, cover.id

    # Approve the cover from Telegram (same gate functions as the admin).
    assert "approved" in telegram_actions.handle_callback(f"cover:{cover_id}:1", 777)

    with db() as s:
        book = s.get(Book, book_id)
        assert book.status == BookStatus.LISTING_DRAFT
        rows = publishing.draft_listings(s, book)
        assert book.status == BookStatus.AWAITING_LISTING_APPROVAL
        etsy = [r for r in rows if r.platform == "etsy"]
        assert all("AI tools" in r.description for r in etsy)
        # A blocked word stops approval until it is fixed.
        etsy[0].title = "Pokemon style coloring pages"
        s.flush()
        with pytest.raises(ValueError, match="fix 1 listing"):
            approvals.approve_all_listings(s, book, me)
        etsy[0].title = "Shapes coloring pages"
        s.flush()
        approvals.approve_all_listings(s, book, me)
        assert book.status == BookStatus.KDP_PACK_READY
        key = publishing.build_pack(s, book)
        files = publishing.build_etsy_files(s, book)
        assert book.kdp_week_start is not None
        assert len(files) == len(etsy)

    with zipfile.ZipFile(BytesIO(storage.get_bytes("outputs", key))) as z:
        assert "Yes" in z.read("ai-disclosure.md").decode()

    with db() as s:
        book = s.get(Book, book_id)
        pipeline.archive_book(s, book, me)
        assert book.kdp_week_start is None  # never uploaded → slot released
    get_settings.cache_clear()
