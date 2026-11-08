"""`make demo`: run the whole pipeline on the 5 bundled sample images in manual mode.

Zero paid API calls: images come from assets/sample_lineart, text agents use the offline
provider. Approvals are made by the CLI human actor "cli:demo" and land in the audit log.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import approvals, pipeline, storage
from crayonlark.core.actors import HumanActor
from crayonlark.core.config import ASSETS_DIR
from crayonlark.core.db import session_scope
from crayonlark.core.models import ApiCost, Book
from crayonlark.print.validate import validate_pdf

DEMO_PLAN: dict[str, Any] = {
    "mazes": 2,
    "wordsearch_words": ["SUN", "FISH", "HOUSE", "APPLE", "ROCKET", "STAR"],
    "wordsearch_size": 9,
    "dot2dot": ["star", "heart"],
    "tracing": "AB",
    "numbers_upto": 0,
    "sudoku": [4, 6],
}


def _book(s: Session, book_id: int) -> Book:
    book = s.get(Book, book_id)
    if book is None:
        raise RuntimeError(f"book {book_id} disappeared")
    return book


def _say(msg: str) -> None:
    print(f"  • {msg}", flush=True)


def run(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    me = HumanActor.from_cli("demo")
    samples = sorted((ASSETS_DIR / "sample_lineart").glob("*.png"))
    assert len(samples) == 5, "expected 5 bundled sample images"

    with session_scope() as s:
        costs_before = s.scalar(select(func.count(ApiCost.id))) or 0
        book = pipeline.create_book(
            s,
            "Happy Things Coloring Book (Demo)",
            me,
            subtitle="Simple Pictures and Fun Activities for Kids Ages 3-6",
            series="Happy Things",
            age_min=3,
            age_max=6,
            themes=["demo", "shapes"],
            ai_interior_images=False,
            ai_text=False,
            activity_plan=DEMO_PLAN,
        )
        approvals.approve_book_idea(s, book, me)
        book_id = book.id
        _say(f"book #{book.id} '{book.slug}' created and approved by {me.name}")

    with session_scope() as s:
        book = _book(s, book_id)
        for p in samples:
            pipeline.add_original(
                s, book, p.read_bytes(), filename=p.name, provider="manual", ai_generated=False
            )
        s.flush()
        s.refresh(book)
        for img in book.images:
            r = pipeline.run_image_qa(s, img)
            _say(
                f"QA {img.scene_title}: score {r['score']} → {r['recommendation']} "
                f"{r['failures'] or ''}"
            )
        pipeline.finish_qa_if_ready(s, book)
        _say(f"status: {book.status}")

    with session_scope() as s:
        book = _book(s, book_id)
        for img in book.images:
            approvals.decide_image(s, img, True, me)
        n = approvals.approve_image_set(s, book, me, min_images=5)
        _say(f"{n} images approved → {book.status}")

    with session_scope() as s:
        book = _book(s, book_id)
        for img in pipeline.approved_images(book):
            r = pipeline.clean_one(s, img)
            _say(
                f"cleaned {img.scene_title}: line {r['qa']['line_px_at_print']}px, "
                f"grey {r['qa']['grey_ratio']:.2%}"
            )
        pipeline.finish_cleaning_if_ready(s, book)
        _say(f"status: {book.status}")

    with session_scope() as s:
        book = _book(s, book_id)
        rep = pipeline.build_interior(s, book)
        _say(
            f"interior: {rep.pages} pages, {rep.width_in}x{rep.height_in} in, "
            f"min image DPI {rep.min_image_dpi}, fonts {', '.join(rep.fonts)}"
        )
        etsy = pipeline.build_etsy_pdfs(s, book)
        interior_key, slug = book.interior_key, book.slug

    results: dict[str, Any] = {"book_id": book_id, "files": []}
    book_dir = out / slug
    if book_dir.exists():
        shutil.rmtree(book_dir)
    assert interior_key
    dest = storage.download("outputs", interior_key, book_dir / "kdp" / "interior.pdf")
    final = validate_pdf(dest, "8.5x11")
    results["files"].append(str(dest))
    _say(f"validated {dest.name}: {'OK' if final.ok else final.errors}")
    for keys in etsy.values():
        for paper, key in keys.items():
            d = storage.download("outputs", key, book_dir / "etsy" / Path(key).name)
            trim = "letter" if paper == "letter" else "a4"
            v = validate_pdf(d, trim, min_pages=1, require_even=False, max_bytes=20 * 1024 * 1024)
            results["files"].append(str(d))
            _say(
                f"validated {d.name}: {v.pages} pages, {v.size_bytes / 1e6:.2f} MB, "
                f"{'OK' if v.ok else v.errors}"
            )

    with session_scope() as s:
        costs_after = s.scalar(select(func.count(ApiCost.id))) or 0
    if costs_after != costs_before:
        raise RuntimeError("demo made paid API calls!")
    _say("paid API calls: 0")
    return results
