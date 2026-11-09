from __future__ import annotations

from sqlalchemy import select

from crayonlark.core import blocklist, starter_content
from crayonlark.core.enums import BookStatus, NicheStatus, PostStatus
from crayonlark.core.models import BlogPost, Book, Niche
from crayonlark.core.starter_blog import POSTS
from tests.conftest import needs_tools


def test_starter_text_is_clean() -> None:
    """No brands/characters, never 'handmade', and slugs are unique."""
    assert len({p["slug"] for p in POSTS}) == len(POSTS) >= 8
    for p in POSTS:
        text = " ".join(p.values())
        assert not blocklist.find(text), p["slug"]
        assert "handmade" not in text.lower() and "hand-drawn" not in text.lower()
    for n in starter_content.NICHES:
        assert not blocklist.find(" ".join(n.values())), n["name"]


def test_seed_is_drafts_and_proposals_only_and_idempotent(db) -> None:  # type: ignore[no-untyped-def]
    with db() as s:
        assert starter_content.seed_blog_drafts(s) == len(POSTS)
        assert starter_content.seed_niche_proposals(s) == len(starter_content.NICHES)
    with db() as s:
        assert starter_content.seed_blog_drafts(s) == 0
        assert starter_content.seed_niche_proposals(s) == 0
        statuses = set(s.scalars(select(BlogPost.status)))
        niche_statuses = set(s.scalars(select(Niche.status)))
    assert statuses == {PostStatus.DRAFT}  # nothing is published by the seed
    assert niche_statuses == {NicheStatus.PROPOSED}  # nothing is approved by the seed


@needs_tools
def test_demo_books_add_and_remove(db, needs_storage) -> None:  # type: ignore[no-untyped-def]
    titles = starter_content.add_demo_books()
    assert len(titles) == 2 and starter_content.add_demo_books() == []
    with db() as s:
        books = s.scalars(select(Book)).all()
        assert {b.status for b in books} == {
            BookStatus.CONCEPTS_READY,
            BookStatus.AWAITING_IMAGE_APPROVAL,
        }
        assert not any(b.is_public for b in books)
    with db() as s:
        assert starter_content.remove_demo_books(s) == 2
    with db() as s:
        assert s.scalars(select(Book)).all() == []


@needs_tools
def test_free_sample_pack(db, needs_storage) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import site

    with db() as s:
        pack = starter_content.build_free_sample_pack(s)
        assert pack is not None and pack["pages"] >= 8 and pack["a4"]
        assert starter_content.build_free_sample_pack(s) is None  # already set
    with db() as s:
        assert site.free_printable(s)["key"] == pack["key"]  # type: ignore[index]
