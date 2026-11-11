"""Autopilot: everything between my two approvals, and never the approvals themselves."""

from __future__ import annotations

import pytest

from crayonlark.core import app_settings, approvals, autopilot
from crayonlark.core.actors import AUTOPILOT
from crayonlark.core.enums import ApprovalState, BookStatus, ImageStatus, NicheStatus
from crayonlark.core.models import AuditLog, Book, Image, Niche
from crayonlark.core.state_machine import AUTOPILOT_GATES, GATES, GateError, transition


@pytest.fixture
def on(db, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr("crayonlark.agents.vision_qa.enabled", lambda: True)
    monkeypatch.setattr(
        "crayonlark.providers.image.base.image_config",
        lambda: {"provider": "deepinfra", "model": "black-forest-labs/FLUX-1-schnell"},
    )
    with db() as s:
        app_settings.set_value(
            "autopilot",
            {"enabled": True, "keep_books": 3, "new_books_per_day": 2, "extra_images": 0},
            "admin:me",
            s,
        )
        app_settings.set_value("images_per_book", {"min": 3, "max": 4}, "admin:me", s)
    return db


def _img(book: Book, pos: int, qa: str = "keep", vision: str = "keep", score: float = 0.9) -> Image:
    return Image(
        book=book,
        position=pos,
        scene_title=f"scene {pos}",
        prompt=f"a cute scene {pos}",
        status=ImageStatus.QA_DONE,
        original_key=f"books/{pos}.png",
        qa_recommendation=qa,
        qa_score=score,
        vision_scores={"checked": True, "recommendation": vision},
    )


@pytest.mark.parametrize("gate", sorted(GATES - AUTOPILOT_GATES))
def test_autopilot_never_passes_my_two_approvals(gate) -> None:  # type: ignore[no-untyped-def]
    src, dst = gate
    b = Book(id=1, title="t", slug="t", status=src)
    with pytest.raises(GateError):
        transition(None, b, dst, AUTOPILOT)  # type: ignore[arg-type]


def test_autopilot_needs_to_be_switched_on(db) -> None:  # type: ignore[no-untyped-def]
    with db() as s:
        n = Niche(theme="dinosaurs", name="Dino Friends")
        s.add(n)
        s.flush()
        with pytest.raises(GateError):
            approvals.decide_niche(s, n, True, AUTOPILOT)
        assert autopilot.tick(s).notes == ["off"]


def test_tick_keeps_good_pictures_generates_and_starts_books(on) -> None:  # type: ignore[no-untyped-def]
    with on() as s:
        a = Book(title="Ready Pictures", slug="ready", status=BookStatus.AWAITING_IMAGE_APPROVAL)
        s.add(a)
        imgs = [_img(a, i, score=0.5 + i / 10) for i in range(5)]  # 5 passed, room for 4
        imgs.append(_img(a, 5, qa="reject"))
        imgs.append(_img(a, 6, vision="reject"))
        s.add_all(imgs)
        b = Book(title="New Prompts", slug="prompts", status=BookStatus.CONCEPTS_READY)
        s.add(b)
        for i in range(5):
            s.add(
                Image(
                    book=b,
                    position=i,
                    scene_title="x",
                    prompt="a happy cat",
                    status=ImageStatus.PENDING,
                )
            )
        s.add(Niche(theme="space", name="Rocket Pals"))
        s.add(Niche(theme="farm", name="Farm Friends"))
        s.flush()

        plan = autopilot.tick(s)

        # the 4 best passed pictures are kept, the rest rejected, cleaning starts
        assert a.status == BookStatus.CLEANING
        kept = sorted(i.position for i in a.images if i.approval == ApprovalState.APPROVED)
        assert kept == [1, 2, 3, 4]
        assert all(i.approved_by == "autopilot" for i in a.images)
        assert len(plan.clean[a.id]) == 4
        # pictures for the fresh prompts: the minimum (extra 0 %)
        assert len(plan.art[b.id]) == 3
        assert sum(i.status == ImageStatus.GENERATING for i in b.images) == 3
        # stock was 2 (keep 3): one new book from the oldest niche idea
        assert len(plan.concepts) == 1
        new = s.get(Book, plan.concepts[0])
        assert new is not None and new.title == "Rocket Pals Coloring Book"
        assert new.status == BookStatus.NICHE_APPROVED
        assert new.niche is not None and new.niche.approved_by == "autopilot"


def test_tick_researches_when_out_of_ideas(on) -> None:  # type: ignore[no-untyped-def]
    with on() as s:
        s.add(Niche(theme="Dinosaurs", name="Old", status=NicheStatus.APPROVED))
        s.flush()
        plan = autopilot.tick(s)
        assert plan.concepts == []
        assert plan.research == "ocean animals"  # first theme not used yet


def test_too_few_good_pictures_tells_me_once(on) -> None:  # type: ignore[no-untyped-def]
    with on() as s:
        a = Book(title="Weak", slug="weak", status=BookStatus.AWAITING_IMAGE_APPROVAL)
        s.add(a)
        s.add_all([_img(a, 0), _img(a, 1, qa="reject")])
        s.add(Niche(theme="x", name="Keep Stock Low", status=NicheStatus.REJECTED))
        app_settings.set_value("autopilot", {"enabled": True, "keep_books": 1}, "admin:me", s)
        s.flush()
        autopilot.tick(s)
        autopilot.tick(s)
        assert a.status == BookStatus.AWAITING_IMAGE_APPROVAL
        warned = s.query(AuditLog).filter(AuditLog.action == "autopilot.short").count()
        assert warned == 1


def test_switching_on_is_mine_and_shows_problems(client, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    from .test_api_admin import H, login

    monkeypatch.setattr("crayonlark.core.flows.poke_autopilot", lambda: None)
    login(client)
    r = client.get("/api/admin/autopilot", headers=H)
    assert r.status_code == 200 and r.json()["enabled"] is False
    assert any("manual" in p for p in r.json()["problems"])
    r = client.put("/api/admin/autopilot", json={"enabled": True, "keep_books": 5}, headers=H)
    assert r.status_code == 200 and r.json()["enabled"] and r.json()["keep_books"] == 5
    r = client.put(
        "/api/admin/autopilot", json={"enabled": True, "themes": ["Disney princesses"]}, headers=H
    )
    assert r.status_code == 400
