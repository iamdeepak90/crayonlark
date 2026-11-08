"""String enums shared by models, API and agents. Stored as plain strings in Postgres."""

from __future__ import annotations

from enum import StrEnum


class BookStatus(StrEnum):
    IDEA = "idea"
    NICHE_APPROVED = "niche_approved"
    CONCEPTS_READY = "concepts_ready"
    IMAGES_GENERATING = "images_generating"
    IMAGES_QA = "images_qa"
    AWAITING_IMAGE_APPROVAL = "awaiting_image_approval"
    CLEANING = "cleaning"
    BUILDING = "building"
    AWAITING_COVER_APPROVAL = "awaiting_cover_approval"
    LISTING_DRAFT = "listing_draft"
    AWAITING_LISTING_APPROVAL = "awaiting_listing_approval"
    KDP_PACK_READY = "kdp_pack_ready"
    KDP_UPLOADED = "kdp_uploaded"
    PROOF_ORDERED = "proof_ordered"
    LIVE = "live"
    ARCHIVED = "archived"


class EtsyStatus(StrEnum):
    NONE = "none"
    ETSY_DRAFTS_CREATED = "etsy_drafts_created"
    ETSY_PUBLISHED = "etsy_published"


class BookFormat(StrEnum):
    PAPERBACK = "paperback"
    HARDCOVER = "hardcover"


class Trim(StrEnum):
    LETTER = "8.5x11"
    SQUARE = "8.5x8.5"


class Paper(StrEnum):
    WHITE = "white"
    CREAM = "cream"
    COLOR = "color"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NicheStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ImageStatus(StrEnum):
    PENDING = "pending"  # prompt exists, no file yet
    UPLOADED = "uploaded"  # original stored (manual drop or provider)
    QA_DONE = "qa_done"
    CLEANED = "cleaned"
    FAILED = "failed"


class Platform(StrEnum):
    KDP = "kdp"
    ETSY = "etsy"


class EtsyProductKind(StrEnum):
    FULL_PDF = "full_pdf"
    MINI_PACK = "mini_pack"
    BUNDLE = "bundle"
    ACTIVITY_PACK = "activity_pack"


class ListingStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PinStatus(StrEnum):
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PostStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    PUBLISHED = "published"
    REJECTED = "rejected"


class SubscriberStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    UNSUBSCRIBED = "unsubscribed"
