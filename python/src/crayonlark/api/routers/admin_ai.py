"""Admin: research agent, concepts, image generation, costs and AI provider settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.api.routers.admin_books import MAX_UPLOAD_BYTES, get_book, image_out
from crayonlark.core import app_settings, blocklist, budget, flows, generation
from crayonlark.core.audit import record
from crayonlark.core.config import get_settings
from crayonlark.core.enums import BookStatus, ImageStatus
from crayonlark.core.models import ApiCost, Book, Image
from crayonlark.integrations import websearch
from crayonlark.providers import pricing
from crayonlark.providers.image.base import image_config

router = APIRouter(prefix="/api/admin", tags=["admin-ai"])

CONCEPT_STATES = {BookStatus.NICHE_APPROVED, BookStatus.CONCEPTS_READY}
ART_STATES = {
    BookStatus.CONCEPTS_READY,
    BookStatus.IMAGES_GENERATING,
    BookStatus.IMAGES_QA,
    BookStatus.AWAITING_IMAGE_APPROVAL,
}


# --------------------------------------------------------------------------- research


class ResearchIn(BaseModel):
    theme: str = Field(min_length=2, max_length=200)
    competitor_notes: str = Field(default="", max_length=20000)
    use_web: bool = True


@router.post("/research")
def start_research(body: ResearchIn, admin: Admin = Depends(require_admin)) -> dict:
    hits = blocklist.find(body.theme, blocklist.extra_terms())
    if hits:
        raise HTTPException(400, f"theme contains blocked terms: {', '.join(hits)}")
    job_id = flows.queue_research(body.theme, body.competitor_notes, body.use_web)
    return {"job_id": job_id, "web_search": websearch.configured() and body.use_web}


# --------------------------------------------------------------------------- concepts + art


@router.get("/books/{book_id}/concepts")
def concepts(book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    b = get_book(s, book_id)
    cfg = image_config()
    rows = [i for i in b.images if i.status in (ImageStatus.PENDING, ImageStatus.GENERATING)]
    failed = [i for i in b.images if i.status == ImageStatus.FAILED]
    model = cfg.get("model") or ""
    return {
        "status": b.status,
        "can_make_concepts": b.status in CONCEPT_STATES,
        "can_generate": b.status in ART_STATES and cfg.get("provider") != "manual",
        "image_provider": cfg.get("provider", "manual"),
        "image_model": model,
        "price_per_image_usd": pricing.image_price(model) if cfg.get("provider") != "manual" else 0,
        "concepts": [image_out(i) for i in rows],
        "failed": [image_out(i) for i in failed],
    }


@router.post("/books/{book_id}/concepts")
def make_concepts(
    book_id: int, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    b = get_book(s, book_id)
    if b.status not in CONCEPT_STATES:
        raise HTTPException(400, f"book is {b.status}; concepts are made before images arrive")
    record(s, admin.actor.name, "book.concepts.request", "book", b.id)
    s.commit()
    return {"job_id": flows.queue_concepts(b.id)}


class GenerateIn(BaseModel):
    count: int = Field(default=0, ge=0, le=80)  # 0 = every remaining concept
    image_ids: list[int] | None = None  # or exactly these (e.g. retry failed ones)


@router.post("/books/{book_id}/generate-images")
def generate_images(
    book_id: int, body: GenerateIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    """Queue paid image generation. Checked against the remaining monthly budget first."""
    b = get_book(s, book_id)
    cfg = image_config()
    if cfg.get("provider", "manual") == "manual":
        raise HTTPException(400, "image provider is manual: upload pictures for the prompts")
    if b.status not in ART_STATES:
        raise HTTPException(400, f"book is {b.status}; cannot generate images now")
    if body.image_ids:
        targets = [
            i
            for i in b.images
            if i.id in set(body.image_ids)
            and not i.original_key
            and i.status in (ImageStatus.PENDING, ImageStatus.FAILED)
        ]
    else:
        targets = generation.art_targets(b, body.count or None)
    if not targets:
        raise HTTPException(400, "no concepts waiting for a picture")
    estimate = len(targets) * pricing.image_price(cfg.get("model") or "")
    left = budget.limits(s).cap_usd - budget.spent_usd(s, budget.month_key())
    if estimate > left:
        raise HTTPException(
            400,
            f"{len(targets)} images ≈ ${estimate:.2f} but only ${max(left, 0):.2f} is left "
            "in this month's budget",
        )
    for img in targets:
        img.status, img.error = ImageStatus.GENERATING, None
    record(s, admin.actor.name, "book.images.generate", "book", b.id, {"count": len(targets)})
    s.commit()
    ids = [i.id for i in targets]
    jobs = flows.queue_art(b.id, ids)  # a failed image's job is re-run under the same key
    return {"queued": len(ids), "estimate_usd": round(estimate, 4), "jobs": jobs}


@router.post("/images/{image_id}/upload")
async def upload_for_concept(
    image_id: int,
    file: UploadFile = File(...),
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    """Manual mode: attach the picture I made from this concept's prompt."""
    img = s.get(Image, image_id)
    if img is None:
        raise HTTPException(404, "image not found")
    if img.original_key:
        raise HTTPException(400, "this concept already has a picture")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "larger than 25 MB")
    try:
        generation.attach_upload(s, img, data, file.filename or "upload.png")
    except Exception as exc:
        raise HTTPException(400, f"not an image: {exc}") from exc
    img.ai_generated = img.book.ai_interior_images
    s.commit()
    flows.queue_qa(img.id, img.book_id)
    return image_out(img)


# --------------------------------------------------------------------------- costs


class BudgetIn(BaseModel):
    monthly_inr: float = Field(ge=0, le=budget.MAX_CAP_INR)
    usd_inr_rate: float = Field(ge=1, le=1000)


@router.get("/budget")
def get_budget(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    sm = budget.summary(s)
    return {k: sm[k] for k in ("month", "spent_inr", "cap_inr", "usd_inr_rate", "ratio", "state")}


@router.put("/budget")
def put_budget(
    body: BudgetIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    try:
        budget.set_limits(s, body.monthly_inr, body.usd_inr_rate, admin.actor.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    return get_budget(admin, s)


@router.get("/costs")
def costs(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    summary = budget.summary(s)
    month = summary["month"]
    recent = s.scalars(select(ApiCost).order_by(ApiCost.created_at.desc()).limit(100))
    by_book = s.execute(
        select(ApiCost.book_id, Book.title, func.sum(ApiCost.cost_usd), func.count(ApiCost.id))
        .join(Book, Book.id == ApiCost.book_id)
        .where(ApiCost.status == "committed")
        .group_by(ApiCost.book_id, Book.title)
        .order_by(func.sum(ApiCost.cost_usd).desc())
        .limit(30)
    ).all()
    day = func.date_trunc("day", ApiCost.created_at)
    daily = s.execute(
        select(day, func.sum(ApiCost.cost_usd))
        .where(ApiCost.month == month, ApiCost.status == "committed")
        .group_by(day)
        .order_by(day)
    ).all()
    return {
        **summary,
        "daily": [{"day": d.date().isoformat(), "usd": round(float(u or 0), 4)} for d, u in daily],
        "by_book": [
            {"book_id": bid, "title": t, "usd": round(float(u or 0), 4), "calls": n}
            for bid, t, u, n in by_book
        ],
        "recent": [
            {
                "id": c.id,
                "at": c.created_at,
                "provider": c.provider,
                "model": c.model,
                "agent": c.agent,
                "kind": c.kind,
                "status": c.status,
                "input_tokens": c.input_tokens,
                "output_tokens": c.output_tokens,
                "images": c.images,
                "usd": round(c.cost_usd, 5),
                "inr": round(c.cost_inr, 2),
                "book_id": c.book_id,
            }
            for c in recent
        ],
    }


# --------------------------------------------------------------------------- AI settings


AGENTS = ["research", "concept", "listing", "vision_qa", "website_content"]


@router.get("/ai/providers")
def providers(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    st = get_settings()
    return {
        "keys": {
            "anthropic": bool(st.anthropic_api_key),
            "openai": bool(st.openai_api_key),
            "gemini": bool(st.gemini_api_key),
            "websearch": websearch.configured(),
        },
        "agents": AGENTS,
        "agent_models": app_settings.get("agent_models", s),
        "image_provider": app_settings.get("image_provider", s),
        "llm_prices": {m: {"input": p[0], "output": p[1]} for m, p in pricing.TOKEN_PRICES.items()},
        "image_prices": pricing.IMAGE_PRICES,
        "prices_checked": pricing.CHECKED,
    }


class AgentModel(BaseModel):
    provider: str = Field(pattern="^(offline|anthropic|openai|gemini)$")
    model: str = Field(default="", max_length=100)
    effort: str = Field(default="", pattern="^(|low|medium|high|xhigh|max)$")


class AISettingsIn(BaseModel):
    agent_models: dict[str, AgentModel]
    image_provider: str = Field(pattern="^(manual|openai|gemini)$")
    image_model: str = Field(default="", max_length=100)


@router.put("/ai/providers")
def save_providers(
    body: AISettingsIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    st = get_settings()
    have = {
        "anthropic": st.anthropic_api_key,
        "openai": st.openai_api_key,
        "gemini": st.gemini_api_key,
    }
    unknown = set(body.agent_models) - set(AGENTS)
    if unknown:
        raise HTTPException(400, f"unknown agents: {sorted(unknown)}")
    for agent, m in body.agent_models.items():
        if m.provider != "offline" and not have[m.provider]:
            raise HTTPException(400, f"{agent}: {m.provider.upper()}_API_KEY is not set")
    if body.image_provider != "manual" and not have[body.image_provider]:
        raise HTTPException(400, f"images: {body.image_provider.upper()}_API_KEY is not set")
    models = {
        a: {k: v for k, v in m.model_dump().items() if v} for a, m in body.agent_models.items()
    }
    app_settings.set_value("agent_models", models, admin.actor.name, s)
    app_settings.set_value(
        "image_provider",
        {"provider": body.image_provider, "model": body.image_model},
        admin.actor.name,
        s,
    )
    s.commit()
    return {"ok": True}
