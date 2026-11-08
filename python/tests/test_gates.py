from __future__ import annotations

from pathlib import Path

import pytest

from crayonlark.core.actors import SYSTEM, HumanActor, agent
from crayonlark.core.enums import BookStatus as S
from crayonlark.core.models import Book
from crayonlark.core.state_machine import (
    GATES,
    TRANSITIONS,
    GateError,
    TransitionError,
    can_transition,
    transition,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "crayonlark"


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def book(status: S) -> Book:
    return Book(id=1, title="t", slug="t", status=status)


def test_human_actor_cannot_be_constructed_directly() -> None:
    with pytest.raises(PermissionError):
        HumanActor("admin:me")
    assert HumanActor.from_cli("me").is_human
    assert not SYSTEM.is_human and not agent("listing").is_human


def test_telegram_actor_requires_admin_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    from crayonlark.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "42")
    try:
        assert HumanActor.from_telegram(42).name == "telegram:42"
        with pytest.raises(PermissionError):
            HumanActor.from_telegram(43)
    finally:
        config.get_settings.cache_clear()


@pytest.mark.parametrize("gate", sorted(GATES))
def test_agents_cannot_pass_gates(gate: tuple[S, S]) -> None:
    src, dst = gate
    b = book(src)
    with pytest.raises(GateError):
        transition(FakeSession(), b, dst, agent("x"))  # type: ignore[arg-type]
    assert b.status == src
    transition(FakeSession(), b, dst, HumanActor.from_cli("t"))  # type: ignore[arg-type]
    assert b.status == dst


def test_required_gates_exist() -> None:
    assert (S.IDEA, S.NICHE_APPROVED) in GATES
    assert (S.AWAITING_IMAGE_APPROVAL, S.CLEANING) in GATES
    assert (S.AWAITING_COVER_APPROVAL, S.LISTING_DRAFT) in GATES
    assert (S.AWAITING_LISTING_APPROVAL, S.KDP_PACK_READY) in GATES


def test_illegal_transitions_rejected() -> None:
    with pytest.raises(TransitionError):
        transition(FakeSession(), book(S.IDEA), S.LIVE, HumanActor.from_cli("t"))  # type: ignore[arg-type]
    assert can_transition(S.LIVE, S.ARCHIVED)
    assert all(g[1] in TRANSITIONS[g[0]] for g in GATES)


def test_no_agent_or_worker_code_impersonates_a_human() -> None:
    """Agents/workers/providers/integrations must never create a HumanActor or call approvals."""
    for folder in ("agents", "worker", "providers", "integrations", "print"):
        for f in (SRC / folder).rglob("*.py"):
            text = f.read_text()
            assert "HumanActor" not in text, f"{f} references HumanActor"
            assert "approvals." not in text or "require_etsy_publish_approval" in text, (
                f"{f} calls approvals"
            )
