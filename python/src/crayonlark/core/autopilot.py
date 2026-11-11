"""Autopilot: everything between my two approvals runs by itself.

Switched on by me in admin (setting "autopilot"). Every few minutes `tick()`:

1. Image sets: for books waiting for image approval, keeps the pictures that passed BOTH the
   pixel QA and the AI vision check (best first, up to the maximum), rejects the ones that
   failed, and starts cleaning once enough passed. Not enough yet: generates more from the
   remaining scene prompts. Needs the vision check switched on (a cheap vision model).
2. Pictures: books with fresh scene prompts get their pictures generated (paid, budget-checked;
   a few more than the minimum, not all prompts, to save money).
3. New books: keeps `keep_books` books between "niche approved" and the Etsy queue. It approves
   the oldest proposed niche (research ideas are already blocklist-checked) and starts its book;
   with no ideas left it researches the least-used theme from `themes` (once a day).

It never passes approval 1 (Etsy) or approval 2 (KDP): those need me (state_machine.GATES).
Every decision is in the audit log as "autopilot". The cleaning, PDF, listing text, Etsy files
and mockups then run by themselves as before.

`tick()` changes the database and returns the jobs to enqueue; the worker task enqueues them after
the commit (core/flows.py)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, approvals, budget, generation, pipeline
from crayonlark.core.actors import AUTOPILOT, SYSTEM
from crayonlark.core.audit import record
from crayonlark.core.enums import ApprovalState, BookStatus, ImageStatus, NicheStatus
from crayonlark.core.models import AuditLog, Book, Image, Job, Niche
from crayonlark.core.notify import notify
from crayonlark.core.state_machine import transition

DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "keep_books": 7,  # in production + waiting for my Etsy approval + Etsy queue (≈ a week)
    "new_books_per_day": 2,
    "extra_images": 0.3,  # generate 30 % more pictures than the minimum (some fail QA)
    "themes": [
        "dinosaurs",
        "ocean animals",
        "farm animals",
        "space and planets",
        "trucks and diggers",
        "jungle animals",
        "bugs and butterflies",
        "unicorns and fairy tales",
        "cute food",
        "pets",
        "birds",
        "trains and planes",
        "under the sea mermaids",
        "forest animals",
        "robots",
        "seasons and holidays",
    ],
}

# Books the Autopilot counts as "stock" for the daily Etsy listing.
PIPELINE = [
    BookStatus.NICHE_APPROVED,
    BookStatus.CONCEPTS_READY,
    BookStatus.IMAGES_GENERATING,
    BookStatus.IMAGES_QA,
    BookStatus.AWAITING_IMAGE_APPROVAL,
    BookStatus.CLEANING,
    BookStatus.BUILDING,
    BookStatus.LISTING_DRAFT,
    BookStatus.AWAITING_ETSY_APPROVAL,
    BookStatus.ETSY_QUEUED,
]


def settings(session: Session | None = None) -> dict[str, Any]:
    return {**DEFAULTS, **(app_settings.get("autopilot", session) or {})}


@dataclass
class Plan:
    """Jobs to enqueue after the commit."""

    concepts: list[int] = field(default_factory=list)  # book ids
    art: dict[int, list[int]] = field(default_factory=dict)  # book id → image ids
    clean: dict[int, list[int]] = field(default_factory=dict)  # book id → image ids
    research: str | None = None  # theme
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "concepts": self.concepts,
            "art": {k: len(v) for k, v in self.art.items()},
            "clean": {k: len(v) for k, v in self.clean.items()},
            "research": self.research,
            "notes": self.notes,
        }


def _today(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _once_a_day(session: Session, key: str, entity: str | int, text: str, now: datetime) -> None:
    """Tell me about a problem, at most once a day per book (or per topic)."""
    seen = session.scalar(
        select(AuditLog.id).where(
            AuditLog.action == f"autopilot.{key}",
            AuditLog.entity_id == str(entity),
            AuditLog.at >= now - timedelta(days=1),
        )
    )
    if seen is None:
        record(session, AUTOPILOT.name, f"autopilot.{key}", "autopilot", entity, {"text": text})
        notify(f"🤖 Autopilot: {text}", kind="approval")


def _image_limits(session: Session) -> tuple[int, int]:
    lim = app_settings.get("images_per_book", session) or {"min": 25, "max": 50}
    return int(lim["min"]), int(lim["max"])


def _passed(img: Image) -> bool:
    """Passed the pixel QA and the AI vision check (a vision error does not count as a pass)."""
    v = img.vision_scores or {}
    return (
        img.qa_recommendation == "keep"
        and bool(v.get("checked"))
        and v.get("recommendation") == "keep"
    )


def _failed(img: Image) -> bool:
    v = img.vision_scores or {}
    return img.qa_recommendation == "reject" or (
        bool(v.get("checked")) and v.get("recommendation") == "reject"
    )


def _can_generate(session: Session, book_id: int, n: int, now: datetime) -> str | None:
    """None if `n` pictures can be generated now, else why not."""
    from crayonlark.providers import pricing
    from crayonlark.providers.image.base import image_config

    cfg = image_config()
    if cfg.get("provider", "manual") == "manual":
        return "the image provider is 'manual' (upload the pictures, or pick one in Settings → AI)"
    estimate = n * pricing.image_price(cfg.get("model") or "")
    left = budget.limits(session).cap_usd - budget.spent_usd(session, budget.month_key(now))
    if estimate > left:
        return f"{n} pictures ≈ ${estimate:.2f}, only ${max(left, 0):.2f} left this month"
    room = budget.book_room_usd(session, book_id)
    if room is not None and estimate > room:
        return f"{n} pictures ≈ ${estimate:.2f}, only ${max(room, 0):.2f} left of the per-book cap"
    return None


def _generate(session: Session, book: Book, n: int, plan: Plan, now: datetime) -> bool:
    targets = generation.art_targets(book, n)
    if not targets:
        return False
    why = _can_generate(session, book.id, len(targets), now)
    if why:
        _once_a_day(
            session, "art_blocked", book.id, f"“{book.title}” is waiting for pictures: {why}.", now
        )
        return False
    if book.status == BookStatus.AWAITING_IMAGE_APPROVAL:  # a second round
        transition(
            session, book, BookStatus.IMAGES_GENERATING, SYSTEM, note="autopilot: more pictures"
        )
    for img in targets:
        img.status, img.error = ImageStatus.GENERATING, None
    record(
        session, AUTOPILOT.name, "book.images.generate", "book", book.id, {"count": len(targets)}
    )
    plan.art[book.id] = [i.id for i in targets]
    return True


def _decide_images(
    session: Session, book: Book, cfg: dict[str, Any], plan: Plan, now: datetime
) -> None:
    from crayonlark.agents import vision_qa

    if not vision_qa.enabled():
        _once_a_day(
            session,
            "no_vision",
            "vision",
            "I only keep pictures an AI vision check has passed. Choose a vision model in "
            "Settings → AI (vision QA), or approve the images yourself.",
            now,
        )
        return
    lo, hi = _image_limits(session)
    undecided = [
        i
        for i in book.images
        if i.approval == ApprovalState.PENDING
        and i.original_key
        and i.status == ImageStatus.QA_DONE
    ]
    good = sorted((i for i in undecided if _passed(i)), key=lambda i: i.qa_score or 0, reverse=True)
    room = max(0, hi - approvals.approved_count(session, book))
    for img in good[:room]:
        approvals.decide_image(session, img, True, AUTOPILOT)
    for img in undecided:
        if _failed(img) or img in good[room:]:
            approvals.decide_image(session, img, False, AUTOPILOT)
    session.flush()
    n = approvals.approved_count(session, book)
    if n >= lo:
        approvals.approve_image_set(session, book, AUTOPILOT)
        plan.clean[book.id] = [i.id for i in pipeline.approved_images(book) if not i.cleaned_key]
        return
    more = math.ceil((lo - n) * (1 + float(cfg["extra_images"])))
    if not _generate(session, book, more, plan, now):
        _once_a_day(
            session,
            "short",
            book.id,
            f"“{book.title}” has only {n} good pictures (needs {lo}) and no more scene prompts "
            "to try. Review its images in admin.",
            now,
        )


def _start_book(session: Session, cfg: dict[str, Any], plan: Plan, now: datetime) -> bool:
    niche = session.scalar(
        select(Niche)
        .where(Niche.status == NicheStatus.PROPOSED)
        .order_by(Niche.created_at, Niche.id)
    )
    if niche is None:
        _research(session, cfg, plan, now)
        return False
    approvals.decide_niche(session, niche, True, AUTOPILOT)
    book = pipeline.book_from_niche(session, niche, AUTOPILOT)
    plan.concepts.append(book.id)
    plan.notes.append(f"started “{book.title}”")
    return True


def _research(session: Session, cfg: dict[str, Any], plan: Plan, now: datetime) -> None:
    ran_today = session.scalar(
        select(Job.id).where(Job.name == "crayonlark.ai.research", Job.created_at >= _today(now))
    )
    if ran_today is not None or not cfg["themes"]:
        return
    used: dict[str, int] = dict(
        session.execute(
            select(func.lower(Niche.theme), func.count(Niche.id)).group_by(func.lower(Niche.theme))
        ).all()
    )
    plan.research = min(
        cfg["themes"], key=lambda t: (used.get(t.lower(), 0), cfg["themes"].index(t))
    )
    record(session, AUTOPILOT.name, "autopilot.research", "theme", plan.research[:60])


def tick(session: Session, now: datetime | None = None) -> Plan:
    now = now or datetime.now(UTC)
    plan = Plan()
    cfg = settings(session)
    if not cfg["enabled"]:
        plan.notes.append("off")
        return plan
    # one tick at a time (the schedule and a "something finished" poke can overlap)
    if not session.scalar(text("SELECT pg_try_advisory_xact_lock(42420001)")):
        plan.notes.append("another tick is running")
        return plan
    if budget.summary(session, now)["state"] == "stop":
        plan.notes.append("budget used up")
        return plan

    for book in session.scalars(
        select(Book).where(Book.status == BookStatus.AWAITING_IMAGE_APPROVAL)
    ):
        _decide_images(session, book, cfg, plan, now)

    lo, _ = _image_limits(session)
    first_round = math.ceil(lo * (1 + float(cfg["extra_images"])))
    for book in session.scalars(select(Book).where(Book.status == BookStatus.CONCEPTS_READY)):
        busy = any(i.status == ImageStatus.GENERATING or i.original_key for i in book.images)
        if not busy:
            _generate(session, book, first_round, plan, now)

    stock = session.scalar(select(func.count(Book.id)).where(Book.status.in_(PIPELINE))) or 0
    started_today = (
        session.scalar(
            select(func.count(Niche.id)).where(
                Niche.approved_by == AUTOPILOT.name, Niche.approved_at >= _today(now)
            )
        )
        or 0
    )
    while stock < int(cfg["keep_books"]) and started_today < int(cfg["new_books_per_day"]):
        if not _start_book(session, cfg, plan, now):
            break
        stock += 1
        started_today += 1
    return plan


def status(session: Session) -> dict[str, Any]:
    """For the admin: the settings plus what the Autopilot can and cannot do right now."""
    from crayonlark.agents import vision_qa
    from crayonlark.providers.image.base import image_config

    cfg = settings(session)
    stock = session.scalar(select(func.count(Book.id)).where(Book.status.in_(PIPELINE))) or 0
    proposed = (
        session.scalar(select(func.count(Niche.id)).where(Niche.status == NicheStatus.PROPOSED))
        or 0
    )
    image_provider = image_config().get("provider", "manual")
    problems = []
    if image_provider == "manual":
        problems.append("Image provider is 'manual': pictures cannot be made automatically.")
    if not vision_qa.enabled():
        problems.append("No vision model: pictures cannot be checked automatically.")
    return {
        **cfg,
        "stock": stock,
        "proposed_niches": proposed,
        "image_provider": image_provider,
        "vision": vision_qa.enabled(),
        "problems": problems,
    }
