"""Book status state machine.

Main track (every book goes to Etsy; only the best go on to KDP):
  idea → niche_approved → concepts_ready → images_generating → images_qa →
  awaiting_image_approval → cleaning → building → listing_draft → awaiting_etsy_approval →
  etsy_queued → on_etsy → kdp_pack_ready → kdp_uploaded → proof_ordered → live
Etsy detail track: none → etsy_drafts_created → etsy_published

Two approvals per book after the image set: "Approve for Etsy" (listing text + Etsy publish)
and, for the best books only, "Approve for KDP" (cover + KDP listing + slot).

Gate transitions (marked GATE) need a HumanActor. They are only called from core/approvals.py.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from crayonlark.core.actors import Actor
from crayonlark.core.audit import record
from crayonlark.core.enums import BookStatus as S
from crayonlark.core.enums import EtsyStatus as E
from crayonlark.core.models import Book

TRANSITIONS: dict[S, set[S]] = {
    S.IDEA: {S.NICHE_APPROVED},
    S.NICHE_APPROVED: {S.CONCEPTS_READY, S.IMAGES_GENERATING},  # manual mode may skip concepts
    S.CONCEPTS_READY: {S.IMAGES_GENERATING},
    S.IMAGES_GENERATING: {S.IMAGES_QA},
    S.IMAGES_QA: {S.AWAITING_IMAGE_APPROVAL, S.IMAGES_GENERATING},
    S.AWAITING_IMAGE_APPROVAL: {S.CLEANING, S.IMAGES_GENERATING},
    S.CLEANING: {S.BUILDING},
    S.BUILDING: {S.LISTING_DRAFT},
    S.LISTING_DRAFT: {S.AWAITING_ETSY_APPROVAL},
    S.AWAITING_ETSY_APPROVAL: {S.ETSY_QUEUED, S.LISTING_DRAFT},
    S.ETSY_QUEUED: {S.ON_ETSY, S.AWAITING_ETSY_APPROVAL},
    S.ON_ETSY: {S.KDP_PACK_READY},
    S.KDP_PACK_READY: {S.KDP_UPLOADED},
    S.KDP_UPLOADED: {S.PROOF_ORDERED, S.LIVE},
    S.PROOF_ORDERED: {S.LIVE},
    S.LIVE: set(),
    S.ARCHIVED: set(),
}

# Transitions only a human may make (approvals + manual KDP steps).
GATES: set[tuple[S, S]] = {
    (S.IDEA, S.NICHE_APPROVED),
    (S.AWAITING_IMAGE_APPROVAL, S.CLEANING),
    (S.AWAITING_ETSY_APPROVAL, S.ETSY_QUEUED),  # approval 1: Etsy
    (S.AWAITING_ETSY_APPROVAL, S.LISTING_DRAFT),  # send back for new listing text
    (S.ETSY_QUEUED, S.AWAITING_ETSY_APPROVAL),  # take out of the Etsy queue
    (S.ON_ETSY, S.KDP_PACK_READY),  # approval 2: KDP
    (S.KDP_PACK_READY, S.KDP_UPLOADED),
    (S.KDP_UPLOADED, S.PROOF_ORDERED),
    (S.KDP_UPLOADED, S.LIVE),
    (S.PROOF_ORDERED, S.LIVE),
}

# The only gates the owner-enabled Autopilot may pass (picking a niche, keeping the images that
# passed both QA checks). Everything else in GATES needs a person.
AUTOPILOT_GATES: set[tuple[S, S]] = {
    (S.IDEA, S.NICHE_APPROVED),
    (S.AWAITING_IMAGE_APPROVAL, S.CLEANING),
}

ETSY_TRANSITIONS: dict[E, set[E]] = {
    E.NONE: {E.ETSY_DRAFTS_CREATED},
    E.ETSY_DRAFTS_CREATED: {E.ETSY_PUBLISHED},
    E.ETSY_PUBLISHED: set(),
}
# The Etsy publish gate is the per-listing human approval checked in
# approvals.require_etsy_publish_approval() before any listing is activated.
ETSY_GATES: set[tuple[E, E]] = set()


class TransitionError(ValueError):
    pass


class GateError(PermissionError):
    pass


def can_transition(current: S, target: S) -> bool:
    if target == S.ARCHIVED:
        return True
    return target in TRANSITIONS.get(current, set())


def transition(session: Session, book: Book, target: S, actor: Actor, note: str = "") -> None:
    current = S(book.status)
    if current == target:
        return  # idempotent
    if not can_transition(current, target):
        raise TransitionError(f"book {book.id}: {current} → {target} is not allowed")
    autopilot_ok = actor.is_autopilot and (current, target) in AUTOPILOT_GATES
    if (current, target) in GATES and not (actor.is_human or autopilot_ok):
        raise GateError(f"book {book.id}: {current} → {target} needs human approval")
    book.status = target
    if target == S.LIVE and book.live_at is None:
        book.live_at = datetime.now(UTC)
    record(
        session,
        actor.name,
        "book.status",
        "book",
        book.id,
        {"from": current, "to": target, "note": note},
    )


def transition_etsy(session: Session, book: Book, target: E, actor: Actor) -> None:
    current = E(book.etsy_status)
    if current == target:
        return
    if target not in ETSY_TRANSITIONS[current]:
        raise TransitionError(f"book {book.id}: etsy {current} → {target} is not allowed")
    if (current, target) in ETSY_GATES and not actor.is_human:
        raise GateError("publishing on Etsy needs human approval")
    book.etsy_status = target
    record(
        session, actor.name, "book.etsy_status", "book", book.id, {"from": current, "to": target}
    )
