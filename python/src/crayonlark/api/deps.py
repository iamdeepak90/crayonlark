"""Shared FastAPI dependencies: DB session, admin auth (+ CSRF header check)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from crayonlark.core import sessions
from crayonlark.core.actors import HumanActor
from crayonlark.core.db import session_scope
from crayonlark.core.models import AdminUser

CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "crayonlark"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def db() -> Iterator[Session]:
    with session_scope() as s:
        yield s


@dataclass
class Admin:
    user: AdminUser
    actor: HumanActor


def require_admin(
    request: Request,
    s: Session = Depends(db),
    cl_session: str | None = Cookie(default=None),
) -> Admin:
    # CSRF: browsers can't send custom headers cross-site without CORS (which we never enable).
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(403, "missing X-Requested-With header")
    user_id = sessions.lookup(cl_session)
    if user_id is None:
        raise HTTPException(401, "not logged in")
    user = s.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(401, "not logged in")
    return Admin(user=user, actor=HumanActor.from_admin(user.email))


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
