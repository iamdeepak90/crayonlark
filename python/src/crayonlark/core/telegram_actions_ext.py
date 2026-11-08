"""Callback kinds added in later phases (cover, listings, Etsy publish)."""

from __future__ import annotations

from crayonlark.core.actors import HumanActor


def handle(kind: str, ident: int, yes: bool, actor: HumanActor) -> str:
    return f"Unknown action {kind}"
