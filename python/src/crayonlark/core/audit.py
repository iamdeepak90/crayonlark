"""Audit log: every approval, publish and settings change, with who/when."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from crayonlark.core.models import AuditLog


def record(
    session: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
    )
    session.add(entry)
    return entry
