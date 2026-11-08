"""Symmetric encryption for secrets stored in the DB (OAuth tokens, TOTP secrets)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from crayonlark.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(("crayonlark-fernet:" + get_settings().secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256((get_settings().secret_key + ip).encode()).hexdigest()
