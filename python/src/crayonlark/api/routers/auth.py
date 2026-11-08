"""Single-user login with optional TOTP 2FA. Rate limited. No sign-up."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import segno
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, client_ip, db, require_admin
from crayonlark.core import sessions
from crayonlark.core.audit import record
from crayonlark.core.auth import verify_password
from crayonlark.core.config import get_settings
from crayonlark.core.crypto import decrypt, encrypt
from crayonlark.core.models import AdminUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str
    totp: str | None = None


class TotpIn(BaseModel):
    code: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        sessions.COOKIE,
        token,
        max_age=sessions.SESSION_TTL,
        httponly=True,
        secure=get_settings().is_production,
        samesite="lax",
        path="/",
    )


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, s: Session = Depends(db)) -> dict:
    ip = client_ip(request)
    if sessions.rate_limited(f"login:{ip}", 10, 900) or sessions.rate_limited(
        f"login:{body.email.lower()}", 10, 900
    ):
        raise HTTPException(429, "too many attempts, try again in 15 minutes")
    user = s.scalar(select(AdminUser).where(AdminUser.email == body.email.lower()))
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(401, "wrong email or password")
    if user.totp_enabled:
        if not body.totp:
            raise HTTPException(401, "totp_required")
        secret = decrypt(user.totp_secret or "")
        if not pyotp.TOTP(secret).verify(body.totp.strip(), valid_window=1):
            raise HTTPException(401, "wrong 2FA code")
    user.last_login_at = datetime.now(UTC)
    record(s, f"admin:{user.email}", "auth.login", "admin_user", user.id, {"ip": ip})
    _set_cookie(response, sessions.create(user.id))
    return {"ok": True, "email": user.email}


@router.post("/logout")
def logout(response: Response, cl_session: str | None = Cookie(default=None)) -> dict:
    sessions.destroy(cl_session)
    response.delete_cookie(sessions.COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(admin: Admin = Depends(require_admin)) -> dict:
    return {"email": admin.user.email, "totp_enabled": admin.user.totp_enabled}


@router.post("/totp/setup")
def totp_setup(admin: Admin = Depends(require_admin)) -> dict:
    secret = pyotp.random_base32()
    admin.user.totp_secret = encrypt(secret)
    admin.user.totp_enabled = False
    uri = pyotp.TOTP(secret).provisioning_uri(admin.user.email, issuer_name="Crayonlark")
    qr = segno.make(uri).svg_data_uri(scale=6)
    return {"secret": secret, "uri": uri, "qr": qr}


@router.post("/totp/enable")
def totp_enable(
    body: TotpIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    if not admin.user.totp_secret:
        raise HTTPException(400, "run setup first")
    if not pyotp.TOTP(decrypt(admin.user.totp_secret)).verify(body.code.strip(), valid_window=1):
        raise HTTPException(400, "wrong code")
    admin.user.totp_enabled = True
    record(s, admin.actor.name, "auth.totp.enable", "admin_user", admin.user.id)
    return {"ok": True}


@router.post("/totp/disable")
def totp_disable(
    body: TotpIn, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    if admin.user.totp_enabled and not pyotp.TOTP(decrypt(admin.user.totp_secret or "")).verify(
        body.code.strip(), valid_window=1
    ):
        raise HTTPException(400, "wrong code")
    admin.user.totp_enabled = False
    admin.user.totp_secret = None
    record(s, admin.actor.name, "auth.totp.disable", "admin_user", admin.user.id)
    return {"ok": True}
