"""Admin: optional integrations (keys and accounts) entered in Settings instead of Coolify."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.core import integrations
from crayonlark.core.config import get_settings

router = APIRouter(prefix="/api/admin/integrations", tags=["admin-integrations"])


class GroupIn(BaseModel):
    enabled: bool
    # secrets: null/missing = keep the saved one, "" = clear, text = replace
    values: dict[str, str | None] = Field(default_factory=dict)


@router.get("")
def list_integrations(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    return {"groups": integrations.describe(s)}


@router.put("/{group_id}")
def save_integration(
    group_id: str,
    body: GroupIn,
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> dict:
    if any(v is not None and len(v) > 4000 for v in body.values.values()):
        raise HTTPException(422, "value too long")
    try:
        integrations.save_group(s, group_id, body.enabled, body.values, admin.actor.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s.commit()
    get_settings.cache_clear()
    return {"groups": integrations.describe(s)}
