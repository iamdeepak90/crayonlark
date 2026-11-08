"""OAuth 2 helpers shared by Etsy and Pinterest: PKCE, state in Redis, encrypted token storage."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from crayonlark.core.crypto import decrypt, encrypt
from crayonlark.core.models import OAuthToken
from crayonlark.core.redis import get_redis

STATE_TTL_S = 600


def challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def new_flow(provider: str) -> tuple[str, str, str]:
    """Returns (state, verifier, challenge); the verifier is kept in Redis for the callback."""
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)[:96]
    get_redis().set(
        f"oauth:{state}", json.dumps({"provider": provider, "verifier": verifier}), ex=STATE_TTL_S
    )
    return state, verifier, challenge_for(verifier)


def pop_flow(state: str, provider: str) -> str:
    """Return the PKCE verifier for this state (one use only) or raise ValueError."""
    r = get_redis()
    raw = r.get(f"oauth:{state}")
    r.delete(f"oauth:{state}")
    if not raw:
        raise ValueError("OAuth state expired or unknown, please try again")
    data = json.loads(str(raw))
    if data["provider"] != provider:
        raise ValueError("OAuth state is for another provider")
    return str(data["verifier"])


def save_token(
    session: Session, provider: str, tok: dict[str, Any], extra: dict[str, Any] | None = None
) -> OAuthToken:
    row = session.get(OAuthToken, provider)
    if row is None:
        row = OAuthToken(provider=provider, access_token_enc="")
        session.add(row)
    row.access_token_enc = encrypt(tok["access_token"])
    if tok.get("refresh_token"):
        row.refresh_token_enc = encrypt(tok["refresh_token"])
    if tok.get("expires_in"):
        row.expires_at = datetime.now(UTC) + timedelta(seconds=int(tok["expires_in"]))
    row.scopes = str(tok.get("scope", row.scopes or ""))[:500]
    row.extra = {**(row.extra or {}), **(extra or {})}
    session.flush()
    return row


def access_token(session: Session, provider: str, refresh: Callable[[str], dict[str, Any]]) -> str:
    """A valid access token, refreshed when it expires within two minutes."""
    row = session.get(OAuthToken, provider)
    if row is None:
        raise PermissionError(f"{provider} is not connected (admin → connect)")
    soon = datetime.now(UTC) + timedelta(minutes=2)
    if row.expires_at is not None and row.expires_at < soon:
        if not row.refresh_token_enc:
            raise PermissionError(f"{provider} token expired, reconnect in admin")
        save_token(session, provider, refresh(decrypt(row.refresh_token_enc)))
    return decrypt(row.access_token_enc)


def status(session: Session, provider: str) -> dict[str, Any]:
    row = session.get(OAuthToken, provider)
    if row is None:
        return {"connected": False}
    return {
        "connected": True,
        "expires_at": row.expires_at,
        "scopes": row.scopes,
        "extra": {k: v for k, v in (row.extra or {}).items() if k != "secret"},
        "updated_at": row.updated_at,
    }
