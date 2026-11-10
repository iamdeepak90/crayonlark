"""Approving a niche creates its book automatically (once) and queues the scene prompts."""

from fastapi.testclient import TestClient

from crayonlark.core import pipeline
from crayonlark.core.actors import SYSTEM, HumanActor
from crayonlark.core.enums import BookStatus, NicheStatus
from crayonlark.core.models import Book, Niche
from crayonlark.core.state_machine import GateError


def test_book_from_niche_is_created_once_and_idea_approved(db) -> None:  # type: ignore[no-untyped-def]
    me = HumanActor.from_cli("test")
    with db() as s:
        n = Niche(
            theme="Dinosaurs",
            name="Friendly Dinosaurs",
            age_range="3-6",
            status=NicheStatus.APPROVED,
        )
        s.add(n)
        s.flush()
        book = pipeline.book_from_niche(s, n, me)
        again = pipeline.book_from_niche(s, n, me)
        assert again.id == book.id
        assert book.title == "Friendly Dinosaurs Coloring Book"
        assert (book.age_min, book.age_max, book.themes) == (3, 6, ["dinosaurs"])
        assert book.status == BookStatus.NICHE_APPROVED
        assert s.query(Book).filter(Book.niche_id == n.id).count() == 1


def test_book_from_niche_needs_a_human(db) -> None:  # type: ignore[no-untyped-def]
    import pytest

    with db() as s:
        n = Niche(
            theme="space", name="Space Coloring Book", age_range="??", status=NicheStatus.APPROVED
        )
        s.add(n)
        s.flush()
        with pytest.raises(GateError):
            pipeline.book_from_niche(s, n, SYSTEM)


def test_approve_endpoint_creates_book_and_queues_concepts(
    db, client: TestClient, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import flows

    from .test_api_admin import H, login

    login(client)

    queued: list[int] = []
    monkeypatch.setattr(flows, "queue_concepts", lambda book_id: queued.append(book_id) or "job")
    with db() as s:
        n = Niche(theme="ocean", name="Ocean Pals", age_range="4-8")
        s.add(n)
        s.flush()
        nid = n.id
    r = client.post(f"/api/admin/niches/{nid}/decision", json={"approve": True}, headers=H)
    assert r.status_code == 200, r.text
    book = r.json()["book"]
    assert book["title"] == "Ocean Pals Coloring Book" and queued == [book["id"]]
    assert r.json()["book_id"] == book["id"]
    listed = client.get("/api/admin/niches").json()
    assert next(x for x in listed if x["id"] == nid)["book_id"] == book["id"]
    # approving again is harmless: same book, nothing queued twice
    r = client.post(f"/api/admin/niches/{nid}/decision", json={"approve": True}, headers=H)
    assert r.status_code in (200, 409) and queued == [book["id"]]


def test_reject_creates_no_book(db, client: TestClient) -> None:  # type: ignore[no-untyped-def]
    from .test_api_admin import H, login

    login(client)
    with db() as s:
        n = Niche(theme="cats", name="Cat Pals")
        s.add(n)
        s.flush()
        nid = n.id
    r = client.post(f"/api/admin/niches/{nid}/decision", json={"approve": False}, headers=H)
    assert r.status_code == 200 and r.json().get("book") is None
    with db() as s:
        assert s.query(Book).count() == 0
