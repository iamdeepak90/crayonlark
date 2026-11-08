"""OAuth connect flows for Etsy and Pinterest (admin host only, admin session required)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.core.audit import record
from crayonlark.core.config import get_settings
from crayonlark.integrations import etsy, oauth, pinterest

router = APIRouter(prefix="/api/oauth", tags=["oauth"])
PROVIDERS = {"etsy": etsy, "pinterest": pinterest}


def _provider(name: str):  # type: ignore[no-untyped-def]
    mod = PROVIDERS.get(name)
    if mod is None:
        raise HTTPException(404, "unknown provider")
    if not mod.configured():
        raise HTTPException(400, f"{name} app keys are not set (see docs/API_KEYS.md)")
    return mod


@router.get("/{name}/start")
def start(name: str, admin: Admin = Depends(require_admin)) -> RedirectResponse:
    mod = _provider(name)
    state, _verifier, challenge = oauth.new_flow(name)
    return RedirectResponse(mod.authorize_url(state, challenge), status_code=302)


@router.get("/{name}/callback")
def callback(
    name: str,
    code: str = "",
    state: str = "",
    error: str = "",
    admin: Admin = Depends(require_admin),
    s: Session = Depends(db),
) -> RedirectResponse:
    mod = _provider(name)
    back = get_settings().admin_site_url.rstrip("/") + ("/etsy" if name == "etsy" else "/pinterest")
    if error or not code:
        return RedirectResponse(f"{back}?error={error or 'no_code'}", status_code=302)
    try:
        verifier = oauth.pop_flow(state, name)
        tok = mod.exchange_code(code, verifier)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    extra = {}
    if name == "etsy" and "." in tok.get("access_token", ""):
        extra["user_id"] = tok["access_token"].split(".", 1)[0]
    oauth.save_token(s, name, tok, extra)
    record(s, admin.actor.name, f"oauth.{name}.connect", "oauth", name, {"scope": tok.get("scope")})
    s.commit()
    return RedirectResponse(f"{back}?connected=1", status_code=302)


@router.post("/{name}/disconnect")
def disconnect(name: str, admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    from crayonlark.core.models import OAuthToken

    row = s.get(OAuthToken, name)
    if row is not None:
        s.delete(row)
        record(s, admin.actor.name, f"oauth.{name}.disconnect", "oauth", name)
        s.commit()
    return {"connected": False}
