"""Pinterest API v5 (official API only).

Verified against Pinterest's OpenAPI spec (github.com/pinterest/api-description, v5.28):
- authorize https://www.pinterest.com/oauth/, token POST https://api.pinterest.com/v5/oauth/token
  with HTTP Basic (app id : secret) and a form body (grant_type, code, redirect_uri,
  refresh_token, continuous_refresh).
- POST /v5/pins: board_id, title ≤ 100, description ≤ 800, link ≤ 2048, alt_text ≤ 500,
  media_source {source_type: image_base64, content_type: image/jpeg|image/png, data},
  ai_disclosures {values: ["AI_MODIFIED"]}.
- GET /v5/boards with bookmark + page_size ≤ 250; POST /v5/boards {name, description, privacy}.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from crayonlark.core.config import get_settings
from crayonlark.integrations import oauth

AUTH_URL = "https://www.pinterest.com/oauth/"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
BASE = "https://api.pinterest.com/v5"
SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
PROVIDER = "pinterest"


class PinterestError(RuntimeError):
    pass


def configured() -> bool:
    s = get_settings()
    return bool(s.pinterest_app_id and s.pinterest_app_secret)


def redirect_uri() -> str:
    return get_settings().admin_site_url.rstrip("/") + "/api/oauth/pinterest/callback"


def authorize_url(state: str, challenge: str = "") -> str:
    q = httpx.QueryParams(
        {
            "client_id": get_settings().pinterest_app_id,
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{q}"


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    s = get_settings()
    r = httpx.post(
        TOKEN_URL, data=data, auth=(s.pinterest_app_id, s.pinterest_app_secret), timeout=30
    )
    if r.status_code >= 400:
        raise PinterestError(f"token request failed: {r.status_code} {r.text[:300]}")
    out: dict[str, Any] = r.json()
    return out


def exchange_code(code: str, verifier: str = "") -> dict[str, Any]:
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "continuous_refresh": "true",
        }
    )


def refresh(refresh_token: str) -> dict[str, Any]:
    return _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})


def pin_payload(
    *,
    board_id: str,
    title: str,
    description: str,
    link: str,
    alt_text: str,
    jpg: bytes,
    ai_art: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:800],
        "link": link[:2048],
        "alt_text": alt_text[:500],
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": base64.b64encode(jpg).decode("ascii"),
        },
    }
    if ai_art:
        body["ai_disclosures"] = {"values": ["AI_MODIFIED"]}
    return body


class Pinterest:
    def __init__(self, session: Session, http: httpx.Client | None = None) -> None:
        self.session = session
        self.http = http or httpx.Client(timeout=60)

    def request(self, method: str, path: str, **kw: Any) -> Any:
        token = oauth.access_token(self.session, PROVIDER, refresh)
        for attempt in range(4):
            resp = self.http.request(
                method, f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, **kw
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(float(resp.headers.get("retry-after", 2 ** (attempt + 1))))
                continue
            if resp.status_code >= 400:
                raise PinterestError(f"{method} {path}: {resp.status_code} {resp.text[:400]}")
            return resp.json() if resp.content else {}
        raise PinterestError(f"{method} {path}: rate limited")

    def boards(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        bookmark = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if bookmark:
                params["bookmark"] = bookmark
            page = self.request("GET", "/boards", params=params)
            out += page.get("items", [])
            bookmark = page.get("bookmark")
            if not bookmark:
                return out

    def create_board(self, name: str, description: str = "") -> dict[str, Any]:
        out: dict[str, Any] = self.request(
            "POST",
            "/boards",
            json={"name": name, "description": description[:500], "privacy": "PUBLIC"},
        )
        return out

    def create_pin(self, body: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = self.request("POST", "/pins", json=body)
        return out
