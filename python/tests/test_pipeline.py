"""End-to-end pipeline against real Postgres + S3 + print tools (runs in the worker image)."""

from __future__ import annotations

from pathlib import Path

import pytest

from crayonlark.core import approvals, pipeline
from crayonlark.core.actors import SYSTEM, HumanActor
from crayonlark.core.config import ASSETS_DIR
from crayonlark.core.enums import BookStatus
from crayonlark.core.models import AuditLog, Book
from crayonlark.core.state_machine import GateError
from tests.conftest import needs_tools

SAMPLES = sorted((ASSETS_DIR / "sample_lineart").glob("*.png"))


@needs_tools
def test_manual_pipeline(db, needs_storage, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    me = HumanActor.from_cli("test")
    with db() as s:
        book = pipeline.create_book(s, "Pipeline Test Book", me, ai_interior_images=False)
        approvals.approve_book_idea(s, book, me)
        for p in SAMPLES:
            pipeline.add_original(s, book, p.read_bytes(), filename=p.name)
        s.flush()
        assert [i.position for i in book.images] == [1, 2, 3, 4, 5]
        assert book.status == BookStatus.IMAGES_GENERATING
        for img in book.images:
            pipeline.run_image_qa(s, img, check_text=False)
        assert pipeline.finish_qa_if_ready(s, book)
        assert book.status == BookStatus.AWAITING_IMAGE_APPROVAL
        book_id = book.id

    with db() as s:
        book = s.get(Book, book_id)
        for img in book.images:
            approvals.decide_image(s, img, True, me)
        with pytest.raises(GateError):
            approvals.approve_image_set(s, book, SYSTEM, min_images=5)
        with pytest.raises(ValueError):
            approvals.approve_image_set(s, book, me)  # default minimum is 25
        approvals.approve_image_set(s, book, me, min_images=5)
        for img in pipeline.approved_images(book):
            pipeline.clean_one(s, img)
        assert pipeline.finish_cleaning_if_ready(s, book)
        rep = pipeline.build_interior(s, book)
        assert rep.ok and rep.pages >= 24 and book.page_count == rep.pages
        etsy = pipeline.build_etsy_pdfs(s, book)
        assert set(next(iter(etsy.values()))) == {"letter", "a4"}

    with db() as s:
        actors = {a.actor for a in s.query(AuditLog).filter(AuditLog.action.like("%approve%"))}
        assert actors == {"cli:test"}
