"""All database tables. One file on purpose: easy to read top to bottom.

Enums are stored as plain strings (see core/enums.py) so adding a value never needs a
Postgres enum migration.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from crayonlark.core.enums import (
    ApprovalState,
    BookFormat,
    BookStatus,
    EtsyStatus,
    ImageStatus,
    JobStatus,
    ListingStatus,
    NicheStatus,
    Paper,
    PinStatus,
    PostStatus,
    SubscriberStatus,
    Trim,
)

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONType, list[Any]: JSONType}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def _uuid() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- admin


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------- niches/books


class Niche(TimestampMixin, Base):
    __tablename__ = "niches"
    id: Mapped[int] = mapped_column(primary_key=True)
    theme: Mapped[str] = mapped_column(String(200))  # what I typed, e.g. "dinosaurs"
    name: Mapped[str] = mapped_column(String(200))
    age_range: Mapped[str] = mapped_column(String(50), default="4-8")
    angle: Mapped[str] = mapped_column(Text, default="")
    risks: Mapped[str] = mapped_column(Text, default="")
    seasonality: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="manual")  # manual | research_agent
    status: Mapped[str] = mapped_column(String(30), default=NicheStatus.PROPOSED)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    books: Mapped[list[Book]] = relationship(back_populates="niche")


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    niche_id: Mapped[int | None] = mapped_column(ForeignKey("niches.id"))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    subtitle: Mapped[str] = mapped_column(String(300), default="")
    series: Mapped[str] = mapped_column(String(200), default="")
    volume: Mapped[int] = mapped_column(Integer, default=1)
    format: Mapped[str] = mapped_column(String(20), default=BookFormat.PAPERBACK)
    trim: Mapped[str] = mapped_column(String(20), default=Trim.LETTER)
    paper: Mapped[str] = mapped_column(String(20), default=Paper.WHITE)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    age_min: Mapped[int] = mapped_column(Integer, default=4)
    age_max: Mapped[int] = mapped_column(Integer, default=8)
    themes: Mapped[list[Any]] = mapped_column(default=list)
    include_color_test: Mapped[bool] = mapped_column(Boolean, default=True)
    activity_plan: Mapped[dict[str, Any]] = mapped_column(default=dict)

    status: Mapped[str] = mapped_column(String(40), default=BookStatus.IDEA, index=True)
    etsy_status: Mapped[str] = mapped_column(String(40), default=EtsyStatus.NONE)

    # AI disclosure (mandatory on KDP and Etsy)
    ai_interior_images: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_cover_image: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_text: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_tools: Mapped[str] = mapped_column(String(300), default="")  # e.g. "ChatGPT image, Claude"
    ai_notes: Mapped[str] = mapped_column(Text, default="")

    # build outputs (object keys in the "outputs" bucket)
    interior_key: Mapped[str | None] = mapped_column(String(500))
    cover_key: Mapped[str | None] = mapped_column(String(500))
    pack_key: Mapped[str | None] = mapped_column(String(500))

    # KDP weekly slot (week starts Sunday 00:00 UTC)
    kdp_week_start: Mapped[date | None] = mapped_column(Date, index=True)

    # links (filled by me after manual upload)
    kdp_asin: Mapped[str | None] = mapped_column(String(20))
    amazon_url: Mapped[str | None] = mapped_column(String(500))
    etsy_url: Mapped[str | None] = mapped_column(String(500))

    # public website
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_description: Mapped[str] = mapped_column(Text, default="")
    preview_keys: Mapped[list[Any]] = mapped_column(default=list)  # in public-assets bucket
    live_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    niche: Mapped[Niche | None] = relationship(back_populates="books")
    images: Mapped[list[Image]] = relationship(back_populates="book", order_by="Image.position")
    covers: Mapped[list[Cover]] = relationship(back_populates="book", order_by="Cover.version")
    listings: Mapped[list[Listing]] = relationship(back_populates="book")


class Image(TimestampMixin, Base):
    """One coloring design (AI-generated or manually dropped)."""

    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    scene_title: Mapped[str] = mapped_column(String(300), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(40), default="manual")
    model: Mapped[str] = mapped_column(String(100), default="")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default=ImageStatus.PENDING)
    original_key: Mapped[str | None] = mapped_column(String(500))
    cleaned_key: Mapped[str | None] = mapped_column(String(500))
    thumb_key: Mapped[str | None] = mapped_column(String(500))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    qa_scores: Mapped[dict[str, Any]] = mapped_column(default=dict)
    vision_scores: Mapped[dict[str, Any]] = mapped_column(default=dict)
    qa_score: Mapped[float | None] = mapped_column(Float)
    qa_recommendation: Mapped[str | None] = mapped_column(String(20))  # keep | reject
    approval: Mapped[str] = mapped_column(String(20), default=ApprovalState.PENDING, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text)

    book: Mapped[Book] = relationship(back_populates="images")


class Page(Base):
    """Planned interior layout (filled by the interior builder, for inspection/debugging)."""

    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    __table_args__ = (UniqueConstraint("book_id", "number"),)


class Cover(TimestampMixin, Base):
    __tablename__ = "covers"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    template: Mapped[str] = mapped_column(String(60), default="classic")
    options: Mapped[dict[str, Any]] = mapped_column(default=dict)
    hero_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    width_in: Mapped[float] = mapped_column(Float, default=0)
    height_in: Mapped[float] = mapped_column(Float, default=0)
    spine_in: Mapped[float] = mapped_column(Float, default=0)
    pdf_key: Mapped[str | None] = mapped_column(String(500))
    thumb_key: Mapped[str | None] = mapped_column(String(500))
    preview_key: Mapped[str | None] = mapped_column(String(500))
    approval: Mapped[str] = mapped_column(String(20), default=ApprovalState.PENDING)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    book: Mapped[Book] = relationship(back_populates="covers")


class Listing(TimestampMixin, Base):
    """KDP listing (one per book) or Etsy product listing (3-5 per book)."""

    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(10))  # kdp | etsy
    product_kind: Mapped[str] = mapped_column(String(30), default="paperback")
    title: Mapped[str] = mapped_column(String(300), default="")
    subtitle: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list[Any]] = mapped_column(default=list)  # KDP: 7 phrases
    categories: Mapped[list[Any]] = mapped_column(default=list)  # KDP: 3 suggestions
    tags: Mapped[list[Any]] = mapped_column(default=list)  # Etsy: 13 tags
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    price_cents: Mapped[int] = mapped_column(Integer, default=999)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    ai_disclosure: Mapped[str] = mapped_column(Text, default="")
    page_selection: Mapped[list[Any]] = mapped_column(default=list)  # image ids for mini packs
    file_keys: Mapped[dict[str, Any]] = mapped_column(default=dict)  # {"letter": key, "a4": key}
    mockup_keys: Mapped[list[Any]] = mapped_column(default=list)
    status: Mapped[str] = mapped_column(String(30), default=ListingStatus.DRAFT)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    book: Mapped[Book] = relationship(back_populates="listings")
    etsy: Mapped[EtsyListing | None] = relationship(back_populates="listing", uselist=False)


class EtsyListing(TimestampMixin, Base):
    __tablename__ = "etsy_listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), unique=True
    )
    etsy_listing_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    shop_id: Mapped[str | None] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30), default="not_created")  # draft | active | ...
    url: Mapped[str | None] = mapped_column(String(500))
    uploaded: Mapped[dict[str, Any]] = mapped_column(default=dict)  # which images/files done
    publish_approved_by: Mapped[str | None] = mapped_column(String(120))
    publish_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    listing: Mapped[Listing] = relationship(back_populates="etsy")


class PinterestBoard(TimestampMixin, Base):
    __tablename__ = "pinterest_boards"
    id: Mapped[int] = mapped_column(primary_key=True)
    niche_id: Mapped[int | None] = mapped_column(ForeignKey("niches.id"), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    pinterest_board_id: Mapped[str | None] = mapped_column(String(60))


class Pin(TimestampMixin, Base):
    __tablename__ = "pins"
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    board_id: Mapped[int | None] = mapped_column(ForeignKey("pinterest_boards.id"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(500), default="")
    image_key: Mapped[str] = mapped_column(String(500))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinterest_pin_id: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default=PinStatus.SCHEDULED, index=True)
    error: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- operations


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), index=True)
    queue: Mapped[str] = mapped_column(String(30), default="default")
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64))
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.QUEUED, index=True)
    args: Mapped[dict[str, Any]] = mapped_column(default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiCost(Base):
    __tablename__ = "api_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    month: Mapped[str] = mapped_column(String(7), index=True)  # "2026-11" (UTC)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100), default="")
    agent: Mapped[str] = mapped_column(String(60), default="")
    kind: Mapped[str] = mapped_column(String(20), default="llm")  # llm | image | search | other
    status: Mapped[str] = mapped_column(String(20), default="reserved")  # reserved|committed|released
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    images: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    job_id: Mapped[str | None] = mapped_column(String(32))
    book_id: Mapped[int | None] = mapped_column(Integer)


class BudgetMonth(Base):
    """One row per month, locked (SELECT ... FOR UPDATE) when reserving spend."""

    __tablename__ = "budget_months"
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    warned_80: Mapped[bool] = mapped_column(Boolean, default=False)
    stopped: Mapped[bool] = mapped_column(Boolean, default=False)


class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(10))  # etsy | kdp
    source: Mapped[str] = mapped_column(String(20))  # etsy_api | kdp_csv
    external_id: Mapped[str] = mapped_column(String(200))
    sold_on: Mapped[date] = mapped_column(Date, index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(400), default="")
    marketplace: Mapped[str] = mapped_column(String(40), default="")
    units: Mapped[int] = mapped_column(Integer, default=1)
    revenue_cents: Mapped[int] = mapped_column(Integer, default=0)  # royalty for KDP
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("platform", "external_id"),)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONType)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(120))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    actor: Mapped[str] = mapped_column(String(120))  # admin:me@x | telegram:123 | cli:demo | system
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(60))
    details: Mapped[dict[str, Any]] = mapped_column(default=dict)


class OAuthToken(TimestampMixin, Base):
    """Etsy/Pinterest tokens, encrypted at rest with SECRET_KEY (see core/crypto.py)."""

    __tablename__ = "oauth_tokens"
    provider: Mapped[str] = mapped_column(String(30), primary_key=True)
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str] = mapped_column(String(500), default="")
    extra: Mapped[dict[str, Any]] = mapped_column(default=dict)


# --------------------------------------------------------------------------- website


class Subscriber(Base):
    __tablename__ = "subscribers"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(20), default=SubscriberStatus.PENDING)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(60), default="free-printables")
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    spam: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BlogPost(TimestampMixin, Base):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text, default="")
    body_md: Mapped[str] = mapped_column(Text, default="")
    seo_title: Mapped[str] = mapped_column(String(300), default="")
    seo_description: Mapped[str] = mapped_column(String(400), default="")
    cover_image_key: Mapped[str | None] = mapped_column(String(500))
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default=PostStatus.DRAFT, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("ix_images_book_approval", Image.book_id, Image.approval)
