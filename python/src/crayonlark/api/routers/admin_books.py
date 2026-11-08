"""Admin: books, image uploads and image approvals."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.core import approvals, flows, pipeline, storage
from crayonlark.core.enums import ApprovalState, BookStatus
from crayonlark.core.models import Book, Image, Job, Niche
from crayonlark.core.state_machine import TransitionError

router = APIRouter(prefix="/api/admin", tags=["admin-books"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class BookIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    subtitle: str = ""
    series: str = ""
    volume: int = 1
    niche_id: int | None = None
    format: str = "paperback"
    trim: str = "8.5x11"
    age_min: int = 4
    age_max: int = 8
    themes: list[str] = []
    activity_plan: dict[str, Any] | None = None
    include_color_test: bool = True
    ai_interior_images: bool = True
    ai_cover_image: bool = False
    ai_text: bool = True
    ai_tools: str = ""


class BookPatch(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    series: str | None = None
    volume: int | None = None
    trim: str | None = None
    format: str | None = None
    age_min: int | None = None
    age_max: int | None = None
    themes: list[str] | None = None
    activity_plan: dict[str, Any] | None = None
    include_color_test: bool | None = None
    ai_interior_images: bool | None = None
    ai_cover_image: bool | None = None
    ai_text: bool | None = None
    ai_tools: str | None = None
    ai_notes: str | None = None
    public_description: str | None = None
    amazon_url: str | None = None
    etsy_url: str | None = None
    kdp_asin: str | None = None
    is_public: bool | None = None


def book_summary(b: Book, counts: dict[str, int] | None = None) -> dict[str, Any]:
    return {
        "id": b.id,
        "slug": b.slug,
        "title": b.title,
        "subtitle": b.subtitle,
        "series": b.series,
        "volume": b.volume,
        "status": b.status,
        "etsy_status": b.etsy_status,
        "format": b.format,
        "trim": b.trim,
        "page_count": b.page_count,
        "kdp_week_start": b.kdp_week_start,
        "updated_at": b.updated_at,
        "counts": counts or {},
    }


def image_out(i: Image) -> dict[str, Any]:
    return {
        "id": i.id,
        "position": i.position,
        "scene_title": i.scene_title,
        "prompt": i.prompt,
        "provider": i.provider,
        "status": i.status,
        "approval": i.approval,
        "qa_score": i.qa_score,
        "qa_recommendation": i.qa_recommendation,
        "qa": (i.qa_scores or {}).get("original", {}),
        "qa_cleaned": (i.qa_scores or {}).get("cleaned"),
        "vision": i.vision_scores or {},
        "width": i.width,
        "height": i.height,
        "has_cleaned": bool(i.cleaned_key),
        "error": i.error,
    }


def get_book(s: Session, book_id: int) -> Book:
    book = s.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "book not found")
    return book


@router.get("/books")
def list_books(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> list[dict]:
    rows = s.execute(
        select(Image.book_id, Image.approval, func.count(Image.id)).group_by(
            Image.book_id, Image.approval
        )
    ).all()
    counts: dict[int, dict[str, int]] = {}
    for book_id, approval, n in rows:
        counts.setdefault(book_id, {})[approval] = n
    books = s.scalars(
        select(Book).where(Book.status != BookStatus.ARCHIVED).order_by(Book.updated_at.desc())
    )
    return [book_summary(b, counts.get(b.id)) for b in books]


@router.post("/books")
def create_book(
    body: BookIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    if body.niche_id is not None:
        niche = s.get(Niche, body.niche_id)
        if niche is None or niche.status != "approved":
            raise HTTPException(400, "niche must exist and be approved")
    book = pipeline.create_book(s, body.title, admin.actor, **body.model_dump(exclude={"title"}))
    approvals.approve_book_idea(s, book, admin.actor)  # I created it myself → approved idea
    s.commit()
    if body.niche_id is not None:  # from an approved niche: write the scene prompts next
        flows.queue_concepts(book.id)
    return book_summary(book)


@router.get("/books/{book_id}")
def book_detail(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    jobs = s.scalars(
        select(Job).where(Job.book_id == b.id).order_by(Job.created_at.desc()).limit(30)
    )
    return {
        **book_summary(b),
        "fields": {k: getattr(b, k) for k in BookPatch.model_fields if hasattr(b, k)}
        | {"ai_notes": b.ai_notes, "paper": b.paper},
        "images": [image_out(i) for i in b.images],
        "approved_count": approvals.approved_count(s, b),
        "interior_key": b.interior_key,
        "cover_key": b.cover_key,
        "pack_key": b.pack_key,
        "covers": [
            {
                "id": c.id,
                "version": c.version,
                "approval": c.approval,
                "template": c.template,
                "width_in": c.width_in,
                "height_in": c.height_in,
                "spine_in": c.spine_in,
                "has_pdf": bool(c.pdf_key),
            }
            for c in b.covers
        ],
        "listings": [
            {
                "id": lst.id,
                "platform": lst.platform,
                "product_kind": lst.product_kind,
                "title": lst.title,
                "status": lst.status,
            }
            for lst in b.listings
        ],
        "jobs": [
            {
                "id": j.id,
                "name": j.name,
                "status": j.status,
                "error": j.error,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
    }


@router.patch("/books/{book_id}")
def update_book(
    book_id: int, body: BookPatch, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    from crayonlark.core.audit import record

    record(
        s,
        admin.actor.name,
        "book.update",
        "book",
        b.id,
        {"fields": sorted(body.model_dump(exclude_unset=True))},
    )
    return book_summary(b)


@router.post("/books/{book_id}/images")
async def upload_images(
    book_id: int,
    files: list[UploadFile] = File(...),
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    b = get_book(s, book_id)
    created: list[int] = []
    errors: list[str] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_UPLOAD_BYTES:
            errors.append(f"{f.filename}: larger than 25 MB")
            continue
        try:
            img = pipeline.add_original(
                s,
                b,
                data,
                filename=f.filename or "upload.png",
                provider="manual",
                ai_generated=b.ai_interior_images,
            )
            s.flush()
            created.append(img.id)
        except Exception as exc:  # bad file: report, continue with the rest
            errors.append(f"{f.filename}: {exc}")
    s.commit()
    for image_id in created:
        flows.queue_qa(image_id, book_id)
    return {"created": created, "errors": errors}


class Decision(BaseModel):
    approve: bool


@router.post("/images/{image_id}/decision")
def decide_image(
    image_id: int, body: Decision, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    img = s.get(Image, image_id)
    if img is None:
        raise HTTPException(404, "image not found")
    try:
        approvals.decide_image(s, img, body.approve, admin.actor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return image_out(img)


@router.post("/images/{image_id}/requeue-qa")
def requeue_qa(image_id: int, admin: Admin = Depends(require_admin)) -> dict:
    return {"job_id": flows.queue_qa(image_id)}


@router.post("/books/{book_id}/approve-images")
def approve_image_set(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    try:
        n = approvals.approve_image_set(s, b, admin.actor)
    except (ValueError, TransitionError) as exc:
        raise HTTPException(400, str(exc)) from exc
    ids = [i.id for i in pipeline.approved_images(b)]
    s.commit()
    flows.after_image_set_approved(b.id, ids)
    flows.notify_text(f"✅ {admin.actor.name} approved {n} images for “{b.title}”.")
    return {"approved": n, "status": b.status}


@router.get("/images/{image_id}/file")
def image_file(
    image_id: int,
    variant: str = Query("thumb"),
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> Response:
    img = s.get(Image, image_id)
    if img is None:
        raise HTTPException(404)
    bucket, key, ctype = {
        "thumb": ("processed", img.thumb_key, "image/webp"),
        "original": ("originals", img.original_key, "image/png"),
        "cleaned": ("processed", img.cleaned_key, "image/png"),
    }.get(variant, ("processed", None, ""))
    if not key:
        raise HTTPException(404, "no such file")
    return Response(
        storage.get_bytes(bucket, key),
        media_type=ctype,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/files")
def output_file(key: str, admin: Admin = Depends(require_admin)) -> Response:
    """Download a built output (interior.pdf, cover.pdf, pack zip, Etsy PDFs)."""
    if ".." in key or key.startswith("/"):
        raise HTTPException(400)
    try:
        data = storage.get_bytes("outputs", key)
    except Exception as exc:
        raise HTTPException(404, "file not found") from exc
    name = key.rsplit("/", 1)[-1]
    ctype = (
        "application/pdf"
        if name.endswith(".pdf")
        else "application/zip"
        if name.endswith(".zip")
        else "image/jpeg"
        if name.endswith(".jpg")
        else "image/png"
        if name.endswith(".png")
        else "text/markdown; charset=utf-8"
        if name.endswith(".md")
        else "application/octet-stream"
    )
    return Response(
        data, media_type=ctype, headers={"Content-Disposition": f'inline; filename="{name}"'}
    )


@router.post("/books/{book_id}/status/{action}")
def manual_status(
    book_id: int,
    action: str,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
    asin: str = "",
    amazon_url: str = "",
) -> dict:
    """Manual KDP steps I do by hand: uploaded → proof ordered → live."""
    b = get_book(s, book_id)
    try:
        if action == "kdp-uploaded":
            approvals.mark_kdp_uploaded(s, b, admin.actor)
        elif action == "proof-ordered":
            approvals.mark_proof_ordered(s, b, admin.actor)
        elif action == "live":
            approvals.mark_live(s, b, admin.actor, asin=asin, amazon_url=amazon_url)
        elif action == "archive":
            pipeline.archive_book(s, b, admin.actor)
        else:
            raise HTTPException(400, "unknown action")
    except TransitionError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    if action == "live":
        flows.after_live(b.id)
    return book_summary(b)


@router.get("/books/{book_id}/pending-images")
def pending_count(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    n = (
        s.scalar(
            select(func.count(Image.id)).where(
                Image.book_id == book_id, Image.approval == ApprovalState.PENDING
            )
        )
        or 0
    )
    return {"pending": n}
