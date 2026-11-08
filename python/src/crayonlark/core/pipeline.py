"""Book pipeline services (no human gates here; see core/approvals.py for those).

Upload/import originals → QA → (human approves set) → cleanup → interior PDF → Etsy PDFs.
Each step is idempotent: re-running it overwrites the same object keys and DB fields.
"""

from __future__ import annotations

import io
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, storage
from crayonlark.core.actors import SYSTEM, Actor
from crayonlark.core.audit import record
from crayonlark.core.enums import ApprovalState, BookStatus, ImageStatus
from crayonlark.core.models import Book, Image, Page
from crayonlark.core.state_machine import transition
from crayonlark.print import cleanup, etsy_files, interior, qa_checks
from crayonlark.print.activities import build_activities
from crayonlark.print.validate import ValidationReport, validate_pdf

DEFAULT_ACTIVITY_PLAN: dict[str, Any] = {
    "mazes": 2,
    "wordsearch_words": [],
    "dot2dot": ["star", "fish"],
    "tracing": "",
    "numbers_upto": 0,
    "sudoku": [4],
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:120] or uuid.uuid4().hex[:8]


def unique_slug(session: Session, title: str) -> str:
    base = slugify(title)
    slug, n = base, 2
    while session.scalar(select(Book.id).where(Book.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def create_book(session: Session, title: str, actor: Actor, **fields: Any) -> Book:
    book = Book(title=title, slug=unique_slug(session, title), **fields)
    book.activity_plan = fields.get("activity_plan") or dict(DEFAULT_ACTIVITY_PLAN)
    session.add(book)
    session.flush()
    record(session, actor.name, "book.create", "book", book.id, {"title": title})
    return book


# --------------------------------------------------------------------------- originals


def _thumb(data: bytes, size: int = 512) -> bytes:
    img = PILImage.open(io.BytesIO(data)).convert("L")
    img.thumbnail((size, size))
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=80)
    return out.getvalue()


def add_original(
    session: Session,
    book: Book,
    data: bytes,
    filename: str = "",
    provider: str = "manual",
    model: str = "",
    prompt: str = "",
    scene_title: str = "",
    ai_generated: bool = True,
    image: Image | None = None,
) -> Image:
    """Store an original image (manual drop or provider output) and create/update its row."""
    PILImage.open(io.BytesIO(data)).verify()  # reject non-images early
    if image is None:
        pos = len(book.images) + 1
        image = Image(
            position=pos,
            prompt=prompt,
            provider=provider,
            model=model,
            scene_title=scene_title or Path(filename).stem,
            ai_generated=ai_generated,
        )
        book.images.append(image)  # keeps len(book.images) right for the next position
        session.flush()
    key = f"{book.slug}/{image.id:06d}-original.png"
    png = io.BytesIO()
    with PILImage.open(io.BytesIO(data)) as im:
        im.save(png, format="PNG")
        image.width, image.height = im.size
    storage.put_bytes("originals", key, png.getvalue(), "image/png")
    storage.put_bytes(
        "processed", f"{book.slug}/thumbs/{image.id:06d}.webp", _thumb(data), "image/webp"
    )
    image.original_key = key
    image.thumb_key = f"{book.slug}/thumbs/{image.id:06d}.webp"
    image.status = ImageStatus.UPLOADED
    image.provider = provider
    if book.status in (BookStatus.NICHE_APPROVED, BookStatus.CONCEPTS_READY):
        transition(session, book, BookStatus.IMAGES_GENERATING, SYSTEM, note="first image in")
    return image


def run_image_qa(session: Session, image: Image, check_text: bool = True) -> dict[str, Any]:
    if not image.original_key:
        raise ValueError(f"image {image.id} has no original")
    data = storage.get_bytes("originals", image.original_key)
    th = qa_checks.QAThresholds.from_dict(app_settings.get("qa_thresholds", session))
    result = qa_checks.run_checks(data, th, check_text=check_text)
    image.qa_scores = {**(image.qa_scores or {}), "original": result.to_dict()}
    image.qa_score = result.score
    image.qa_recommendation = result.recommendation
    image.status = ImageStatus.QA_DONE
    return result.to_dict()


def finish_qa_if_ready(session: Session, book: Book) -> bool:
    """When every uploaded image has QA results, move the book to awaiting_image_approval."""
    imgs = [i for i in book.images if i.status not in (ImageStatus.PENDING, ImageStatus.FAILED)]
    waiting = any(
        i.status in (ImageStatus.UPLOADED, ImageStatus.GENERATING)
        or (i.vision_scores or {}).get("pending")
        for i in imgs
    )
    if not imgs or waiting:
        return False
    if book.status == BookStatus.IMAGES_GENERATING:
        transition(session, book, BookStatus.IMAGES_QA, SYSTEM)
    if book.status == BookStatus.IMAGES_QA:
        transition(session, book, BookStatus.AWAITING_IMAGE_APPROVAL, SYSTEM)
        return True
    return False


# --------------------------------------------------------------------------- cleanup


def clean_one(session: Session, image: Image) -> dict[str, Any]:
    if image.approval != ApprovalState.APPROVED:
        raise ValueError(f"image {image.id} is not approved")
    assert image.original_key
    data = storage.get_bytes("originals", image.original_key)
    res = cleanup.clean_image(data)
    book = image.book
    key = f"{book.slug}/{image.id:06d}-clean.png"
    storage.put_bytes("processed", key, res.png, "image/png")
    storage.put_bytes(
        "processed", f"{book.slug}/{image.id:06d}-clean.svg", res.svg, "image/svg+xml"
    )
    th = qa_checks.QAThresholds.from_dict(app_settings.get("qa_thresholds", session))
    after = qa_checks.run_checks(res.png, th, check_text=False)
    image.cleaned_key = key
    image.status = ImageStatus.CLEANED
    image.qa_scores = {
        **(image.qa_scores or {}),
        "cleaned": after.to_dict(),
        "specks_removed": res.specks_removed,
    }
    return {"image_id": image.id, "cleaned_key": key, "qa": after.to_dict()}


def approved_images(book: Book) -> list[Image]:
    return [i for i in book.images if i.approval == ApprovalState.APPROVED]


def finish_cleaning_if_ready(session: Session, book: Book) -> bool:
    imgs = approved_images(book)
    if book.status == BookStatus.CLEANING and imgs and all(i.cleaned_key for i in imgs):
        transition(session, book, BookStatus.BUILDING, SYSTEM)
        return True
    return False


# --------------------------------------------------------------------------- builds


def _download_cleaned(book: Book, tmp: Path) -> list[Path]:
    paths = []
    for img in approved_images(book):
        assert img.cleaned_key, f"image {img.id} not cleaned"
        paths.append(storage.download("processed", img.cleaned_key, tmp / f"{img.id:06d}.png"))
    return paths


def other_titles(session: Session, book: Book) -> list[str]:
    rows = session.scalars(
        select(Book.title).where(Book.id != book.id, Book.status == BookStatus.LIVE).limit(8)
    )
    return list(rows)


def build_interior(session: Session, book: Book) -> ValidationReport:
    with tempfile.TemporaryDirectory(prefix="interior-") as t:
        tmp = Path(t)
        designs = _download_cleaned(book, tmp)
        spec = interior.InteriorSpec(
            title=book.title,
            subtitle=book.subtitle,
            trim=book.trim,
            year=datetime.now(UTC).year,
            designs=designs,
            activities=build_activities(book.activity_plan or {}, seed=book.id),
            include_color_test=book.include_color_test,
            ai_interior_images=book.ai_interior_images,
            more_books=other_titles(session, book),
        )
        out = tmp / "interior.pdf"
        plan = interior.render(spec, out)
        report = validate_pdf(out, book.trim, min_pages=interior.MIN_PAGES)
        if not report.ok:
            raise ValueError("interior failed validation: " + "; ".join(report.errors))
        key = f"{book.slug}/interior.pdf"
        storage.put_file("outputs", key, out, "application/pdf")
    book.interior_key = key
    book.page_count = len(plan)
    session.execute(delete(Page).where(Page.book_id == book.id))
    approved = approved_images(book)
    for p in plan:
        image_id = approved[p.refs[0]].id if p.kind == "design" else None
        session.add(
            Page(
                book_id=book.id,
                number=p.number,
                kind=p.kind,
                image_id=image_id,
                payload={"refs": p.refs},
            )
        )
    return report


def build_etsy_pdfs(
    session: Session, book: Book, products: list[dict[str, Any]] | None = None
) -> dict[str, dict[str, str]]:
    """Build Letter + A4 PDFs for each Etsy product. `products` items:
    {"slug": str, "title": str, "image_ids": [..] | None, "activities": bool}
    Default: one full pack (all designs + activities). Returns {slug: {paper: key}}."""
    approved = approved_images(book)
    products = products or [
        {
            "slug": f"{book.slug}-printable",
            "title": book.title,
            "image_ids": None,
            "activities": True,
        }
    ]
    out: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="etsy-") as t:
        tmp = Path(t)
        all_paths = dict(zip([i.id for i in approved], _download_cleaned(book, tmp), strict=True))
        acts = build_activities(book.activity_plan or {}, seed=book.id)
        for prod in products:
            ids = prod["image_ids"] if prod.get("image_ids") is not None else list(all_paths)
            product = etsy_files.EtsyProduct(
                slug=prod["slug"],
                title=prod["title"],
                designs=[all_paths[i] for i in ids if i in all_paths],
                activities=acts if prod.get("activities") else [],
                ai_artwork=book.ai_interior_images,
            )
            reports = etsy_files.render_both(product, tmp / "etsy")
            keys: dict[str, str] = {}
            for paper, rep in reports.items():
                if not rep.ok:
                    raise ValueError(f"{prod['slug']} {paper}: " + "; ".join(rep.errors))
                key = f"{book.slug}/etsy/{Path(rep.path).name}"
                storage.put_file("outputs", key, Path(rep.path), "application/pdf")
                keys[paper] = key
            out[prod["slug"]] = keys
    return out


def archive_book(session: Session, book: Book, actor: Actor) -> None:
    """Archive a book. A pack that was never uploaded to KDP gives its weekly slot back."""
    if book.status == BookStatus.KDP_PACK_READY and book.kdp_week_start is not None:
        record(
            session,
            actor.name,
            "kdp_slot.release",
            "book",
            book.id,
            {"week": book.kdp_week_start.isoformat()},
        )
        book.kdp_week_start = None
    transition(session, book, BookStatus.ARCHIVED, actor)


# --------------------------------------------------------------------------- inbox (manual drop)


def import_inbox(session: Session) -> list[int]:
    """Import files dropped into the `inbox` bucket as `<book-slug>/<file>.png`."""
    created: list[int] = []
    for key in storage.list_keys("inbox"):
        if "/" not in key or not key.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        slug, filename = key.split("/", 1)
        book = session.scalar(select(Book).where(Book.slug == slug))
        if book is None:
            continue
        data = storage.get_bytes("inbox", key)
        img = add_original(session, book, data, filename=filename, provider="manual")
        session.flush()
        created.append(img.id)
        storage.delete("inbox", key)
    return created
