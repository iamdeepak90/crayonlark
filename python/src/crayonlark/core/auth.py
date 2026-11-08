"""Single-user admin auth: argon2 password hashes, optional TOTP, Redis sessions."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from crayonlark.core.db import session_scope
from crayonlark.core.models import AdminUser

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def upsert_admin(email: str, password: str) -> None:
    email = email.strip().lower()
    with session_scope() as s:
        user = s.scalar(select(AdminUser).where(AdminUser.email == email))
        if user is None:
            if s.scalar(select(AdminUser).limit(1)) is not None:
                raise ValueError("an admin user already exists; this is a single-user system")
            s.add(AdminUser(email=email, password_hash=hash_password(password)))
        else:
            user.password_hash = hash_password(password)
