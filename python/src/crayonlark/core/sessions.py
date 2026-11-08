"""Admin sessions in Redis (opaque random token in an httpOnly cookie; only its hash is stored)."""

from __future__ import annotations

import hashlib
import secrets

from crayonlark.core.redis import get_redis

SESSION_TTL = 7 * 24 * 3600
COOKIE = "cl_session"


def _key(token: str) -> str:
    return "sess:" + hashlib.sha256(token.encode()).hexdigest()


def create(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    get_redis().set(_key(token), str(user_id), ex=SESSION_TTL)
    return token


def lookup(token: str | None) -> int | None:
    if not token:
        return None
    r = get_redis()
    val = r.get(_key(token))
    if val is None:
        return None
    r.expire(_key(token), SESSION_TTL)  # sliding expiry
    return int(val)


def destroy(token: str | None) -> None:
    if token:
        get_redis().delete(_key(token))


def rate_limited(bucket: str, limit: int, window_s: int) -> bool:
    """Fixed-window counter. Returns True when the caller is over the limit."""
    r = get_redis()
    key = f"rl:{bucket}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, window_s)
    return int(n) > limit
