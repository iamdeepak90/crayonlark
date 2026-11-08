"""Concept agent: for a book with an approved niche, write N scene ideas (default 60). Each
becomes an image prompt through the house prompt template (admin → Settings →
house_prompt_template). Scenes that hit the blocklist are dropped.

Concepts are stored as Image rows with status "pending" (a prompt, no file yet). The art agent
or a manual upload fills them in.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, blocklist
from crayonlark.core.actors import SYSTEM as SYSTEM_ACTOR
from crayonlark.core.enums import BookStatus, ImageStatus
from crayonlark.core.models import Book, Image
from crayonlark.core.state_machine import transition
from crayonlark.providers.llm.base import AgentTask, run_task


class Scene(BaseModel):
    title: str = Field(max_length=80, description="Short page title, e.g. 'Turtle at the beach'")
    scene: str = Field(
        max_length=300,
        description="One simple scene for the image prompt: subject, action, 1-3 props",
    )


class ConceptOut(BaseModel):
    scenes: list[Scene] = Field(min_length=10, max_length=80)


SYSTEM = """You plan pages for a kids' coloring book. Write simple, varied, friendly scenes that
work as bold black-and-white line art: one clear main subject, an easy action, at most three
simple props or background shapes, nothing scary, no text or letters in the picture, no famous
characters, brands, logos or a living artist's style. Animals and objects must be real and
correctly named. Vary the subjects, actions and settings; never repeat a scene.
Return ONLY JSON matching the schema."""

ACTIONS = [
    "waving hello", "reading a book", "flying a kite", "eating an ice cream", "playing a drum",
    "sleeping under a blanket", "riding a bicycle", "building a sandcastle", "blowing bubbles",
    "planting a flower", "jumping in a puddle", "having a picnic", "wearing a party hat",
    "painting a picture", "playing football", "holding a balloon", "taking a bath",
    "sitting on a swing", "baking a cake", "looking through a telescope",
]  # fmt: skip
SETTINGS = ["", " in a sunny garden", " by the sea"]


def offline(book: Book, n: int) -> ConceptOut:
    subjects = [t for t in (book.themes or []) if t != "demo"] or [book.title]
    scenes: list[Scene] = []
    i = 0
    while len(scenes) < n and i < n * 3:
        subject = subjects[i % len(subjects)]
        action = ACTIONS[i % len(ACTIONS)]
        place = SETTINGS[(i // len(ACTIONS)) % len(SETTINGS)]
        text = f"a cute friendly {subject} {action}{place}"
        if all(s.scene != text for s in scenes):
            scenes.append(Scene(title=f"{subject.title()} {action}"[:80], scene=text))
        i += 1
    return ConceptOut(scenes=scenes)


def build_prompt(book: Book, n: int, angle: str) -> str:
    return (
        f"Book: {book.title}\nThemes: {', '.join(book.themes or [])}\n"
        f"Ages {book.age_min}-{book.age_max}.\nNiche angle: {angle or '-'}\n"
        f"Write {n} different scenes."
    )


def run(book: Book, n: int) -> ConceptOut:
    angle = book.niche.angle if book.niche else ""
    task = AgentTask(
        agent="concept",
        system=SYSTEM,
        prompt=build_prompt(book, n, angle),
        schema=ConceptOut,
        offline=lambda: offline(book, n),
        max_tokens=60 * n + 500,
        book_id=book.id,
    )
    return run_task(task)


def image_prompt(template: str, scene: str) -> str:
    return template.replace("{scene}", scene.strip().rstrip("."))


def save_concepts(session: Session, book: Book, out: ConceptOut) -> tuple[int, list[str]]:
    """Replace the book's unused concept rows with these scenes. Returns (saved, dropped)."""
    extra = blocklist.extra_terms(session)
    template = app_settings.get("house_prompt_template", session)
    for img in list(book.images):
        if img.status == ImageStatus.PENDING and not img.original_key:
            session.delete(img)
    session.flush()
    session.expire(book, ["images"])
    seen: set[str] = set()
    dropped: list[str] = []
    pos = max((i.position for i in book.images), default=0)
    provider = (app_settings.get("image_provider", session) or {}).get("provider", "manual")
    saved = 0
    for sc in out.scenes:
        key = sc.scene.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        if blocklist.find(f"{sc.title} {sc.scene}", extra):
            dropped.append(sc.title)
            continue
        pos += 1
        book.images.append(
            Image(
                position=pos,
                scene_title=sc.title,
                prompt=image_prompt(template, sc.scene),
                provider=provider,
                status=ImageStatus.PENDING,
            )
        )
        saved += 1
    session.flush()
    if book.status == BookStatus.NICHE_APPROVED:
        transition(session, book, BookStatus.CONCEPTS_READY, SYSTEM_ACTOR, note=f"{saved} scenes")
    return saved, dropped
