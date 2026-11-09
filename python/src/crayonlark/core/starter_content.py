"""Starter content for a fresh install (`crayonlark starter-content`) and removable admin demo
data (`crayonlark demo-data` / `crayonlark demo-data --remove`).

Nothing here skips a human gate:
- blog posts are saved as DRAFTS (I publish them in admin → Blog);
- niche ideas are saved as PROPOSED (I approve or reject them in admin → Niches);
- the free sample printable uses the 5 bundled original line-art pages (not AI art);
- demo books never get past "awaiting image approval" and are never public. Running
  `demo-data` is me acting from the terminal, so its idea approvals are logged as `cli:demo-data`.
Everything is idempotent: running a command twice changes nothing the second time.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings, storage
from crayonlark.core.audit import record
from crayonlark.core.config import ASSETS_DIR
from crayonlark.core.enums import NicheStatus, PostStatus
from crayonlark.core.models import BlogPost, Book, Niche
from crayonlark.core.starter_blog import POSTS

STARTER = "system:starter-content"
DEMO_SUFFIX = "(Demo)"

# Kids' coloring book niches to start from. Saved as proposals; I decide.
NICHES: list[dict[str, str]] = [
    {
        "theme": "farm animals",
        "name": "Farm Animal Friends",
        "age_range": "2-5",
        "angle": "Big, friendly farm animals with one animal per page and simple barn scenes.",
        "risks": "Very competitive; stand out with extra-thick lines for toddlers.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "ocean",
        "name": "Ocean Pals",
        "age_range": "4-8",
        "angle": "Smiling sea creatures, coral reefs and underwater scenes with mazes.",
        "risks": "Avoid look-alikes of famous animated fish characters.",
        "seasonality": "Peaks in summer",
    },
    {
        "theme": "dinosaurs",
        "name": "Friendly Dinosaurs",
        "age_range": "4-8",
        "angle": "Cute, not scary, dinosaurs with simple name labels kids can trace.",
        "risks": "No movie-franchise dinosaurs or logos.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "space",
        "name": "Space Adventure",
        "age_range": "5-9",
        "angle": "Rockets, planets, astronauts and friendly aliens, plus space mazes.",
        "risks": "Keep facts about planets correct in any captions.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "vehicles",
        "name": "Trucks, Trains & Diggers",
        "age_range": "3-6",
        "angle": "Construction vehicles, trains, fire trucks and tractors, one per page.",
        "risks": "No real vehicle brand logos or toy brands.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "bugs",
        "name": "Bugs & Garden Critters",
        "age_range": "4-8",
        "angle": "Ladybugs, bees, butterflies and snails in flower gardens; counting pages.",
        "risks": "Keep insects friendly and simple.",
        "seasonality": "Spring",
    },
    {
        "theme": "toddler shapes",
        "name": "My First Big Shapes",
        "age_range": "2-4",
        "angle": "Very large simple shapes and everyday objects for first coloring.",
        "risks": "Must stay extremely simple; low detail is the selling point.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "alphabet",
        "name": "ABC Animals: Color & Trace",
        "age_range": "3-5",
        "angle": "One animal per letter with a big letter to trace on every page.",
        "risks": "Check every animal name and spelling.",
        "seasonality": "Back to school",
    },
    {
        "theme": "numbers",
        "name": "Count to 20: Color by Number Fun",
        "age_range": "3-6",
        "angle": "Count-the-objects pages from 1 to 20 with dot-to-dot activities.",
        "risks": "Counts on every page must be exactly right.",
        "seasonality": "Back to school",
    },
    {
        "theme": "jungle",
        "name": "Jungle Safari",
        "age_range": "4-8",
        "angle": "Lions, elephants, monkeys and parrots in simple jungle scenes.",
        "risks": "Avoid look-alikes of famous animated jungle films.",
        "seasonality": "Evergreen",
    },
    {
        "theme": "seasons",
        "name": "Cozy Seasons",
        "age_range": "4-8",
        "angle": "Autumn leaves, snowy days, spring flowers and summer picnics.",
        "risks": "Keep holiday content generic and inclusive.",
        "seasonality": "Release before each season",
    },
    {
        "theme": "kind monsters",
        "name": "Kind Little Monsters",
        "age_range": "4-8",
        "angle": "Silly, friendly monsters doing everyday things; not scary.",
        "risks": "Keep faces friendly; no horror elements.",
        "seasonality": "Peaks in October",
    },
]

FREE_PACK_PLAN: dict[str, Any] = {
    "mazes": 1,
    "dot2dot": ["star"],
    "tracing": "A",
    "wordsearch_words": [],
    "numbers_upto": 0,
    "sudoku": [],
}


# --------------------------------------------------------------------------- blog + niches


def seed_blog_drafts(session: Session) -> int:
    added = 0
    for p in POSTS:
        if session.scalar(select(BlogPost.id).where(BlogPost.slug == p["slug"])):
            continue
        session.add(
            BlogPost(
                slug=p["slug"],
                title=p["title"],
                excerpt=p["excerpt"],
                body_md=p["body"].strip() + "\n",
                seo_title=p["title"],
                seo_description=p["excerpt"],
                ai_generated=True,
                status=PostStatus.DRAFT,
            )
        )
        added += 1
    if added:
        record(session, STARTER, "blog.starter_drafts", "blog_post", "-", {"added": added})
    return added


def seed_niche_proposals(session: Session) -> int:
    added = 0
    for n in NICHES:
        if session.scalar(select(Niche.id).where(Niche.name == n["name"])):
            continue
        session.add(Niche(**n, source="starter", status=NicheStatus.PROPOSED))
        added += 1
    if added:
        record(session, STARTER, "niche.starter_proposals", "niche", "-", {"added": added})
    return added


# --------------------------------------------------------------------------- free printable


def build_free_sample_pack(session: Session, force: bool = False) -> dict[str, Any] | None:
    """Free printable from the 5 bundled original pages (+ 3 activity pages), Letter and A4.

    Skipped when a free printable already exists, unless force=True.
    """
    from crayonlark.core.site import _page_jpg
    from crayonlark.print import cleanup, etsy_files
    from crayonlark.print.activities import build_activities

    if not force and app_settings.get("free_printable_key", session):
        return None
    samples = sorted((ASSETS_DIR / "sample_lineart").glob("*.png"))
    keys: dict[str, str] = {}
    pages = 0
    with tempfile.TemporaryDirectory(prefix="free-pack-") as t:
        tmp = Path(t)
        designs = []
        for p in samples:  # same clean-up as book pages: vectorise, re-render at 300 DPI
            out = tmp / f"{p.stem}-clean.png"
            out.write_bytes(cleanup.clean_image(p.read_bytes()).png)
            designs.append(out)
        product = etsy_files.EtsyProduct(
            slug="crayonlark-free-sample-pack",
            title="Free coloring pages from Crayonlark",
            designs=designs,
            activities=build_activities(FREE_PACK_PLAN, seed=7),
            ai_artwork=False,  # the bundled samples are drawn by code, not AI
        )
        for paper, rep in etsy_files.render_both(product, tmp / "pdf").items():
            if not rep.ok:
                raise ValueError(f"free pack {paper}: " + "; ".join(rep.errors))
            key = f"free/{Path(rep.path).name}"
            storage.put_file("outputs", key, Path(rep.path), "application/pdf")
            keys[paper] = key
            pages = rep.pages
    preview = "free/preview.jpg"
    storage.put_bytes("public", preview, _page_jpg(samples[0].read_bytes()), "image/jpeg")
    value = {
        "key": keys["letter"],
        "a4": keys.get("a4"),
        "book_id": None,
        "title": "Free coloring pages from Crayonlark",
        "pages": pages,
        "preview": preview,
    }
    app_settings.set_value("free_printable_key", value, STARTER, session)
    return value


# --------------------------------------------------------------------------- admin demo data


def _demo_books(session: Session) -> list[Book]:
    rows = session.scalars(select(Book).where(Book.title.endswith(DEMO_SUFFIX))).all()
    return [b for b in rows if "demo" in (b.themes or [])]


def add_demo_books() -> list[str]:
    """Two example books in early pipeline stages, so the admin isn't empty. Never public."""
    from crayonlark.agents import concept
    from crayonlark.core import approvals, pipeline
    from crayonlark.core.actors import HumanActor
    from crayonlark.core.db import session_scope

    me = HumanActor.from_cli("demo-data")
    with session_scope() as s:
        if _demo_books(s):
            return []
        ocean = pipeline.create_book(
            s,
            f"Ocean Pals Coloring Book {DEMO_SUFFIX}",
            me,
            subtitle="Friendly Sea Creatures for Kids Ages 4-8",
            age_min=4,
            age_max=8,
            themes=["demo", "ocean"],
        )
        sunny = pipeline.create_book(
            s,
            f"Sunny Day Coloring Book {DEMO_SUFFIX}",
            me,
            subtitle="Simple Pictures for Kids Ages 3-6",
            age_min=3,
            age_max=6,
            themes=["demo", "shapes"],
            ai_interior_images=False,
            ai_text=False,
        )
        for book in (ocean, sunny):
            approvals.approve_book_idea(s, book, me)
            concept.save_concepts(s, book, concept.offline(book, 12))
        sunny_id = sunny.id
        titles = [ocean.title, sunny.title]

    # the second one gets the 5 bundled pictures and waits for my image approval
    with session_scope() as s:
        demo = s.get(Book, sunny_id)
        assert demo is not None
        for p in sorted((ASSETS_DIR / "sample_lineart").glob("*.png")):
            pipeline.add_original(
                s, demo, p.read_bytes(), filename=p.name, provider="manual", ai_generated=False
            )
        s.flush()
        s.refresh(demo)
        for img in [i for i in demo.images if i.original_key]:
            pipeline.run_image_qa(s, img)
        pipeline.finish_qa_if_ready(s, demo)
    return titles


def remove_demo_books(session: Session) -> int:
    books = _demo_books(session)
    for book in books:
        for img in book.images:
            for bucket, key in (
                ("originals", img.original_key),
                ("processed", img.cleaned_key),
                ("processed", img.thumb_key),
            ):
                if key:
                    with contextlib.suppress(Exception):  # a missing file mustn't block clean-up
                        storage.delete(bucket, key)
        record(session, STARTER, "book.demo_removed", "book", book.id, {"title": book.title})
    ids = [b.id for b in books]
    if ids:
        session.expunge_all()
        # the database cascades to images, concepts, covers and listings (ON DELETE CASCADE)
        session.execute(delete(Book).where(Book.id.in_(ids)))
    return len(books)
