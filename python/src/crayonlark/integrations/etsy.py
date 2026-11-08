"""Etsy Open API v3 (official API only; never scraping).

Verified against the Etsy OpenAPI spec and docs (Nov 2026):
- OAuth 2 with PKCE (S256), authorize https://www.etsy.com/oauth/connect, token
  https://api.etsy.com/v3/public/oauth/token (form-encoded). Access tokens last 1 h, refresh
  tokens 90 days. Tokens are "<user_id>.<token>" and sent as `Authorization: Bearer`.
- Every request sends `x-api-key: <keystring>:<shared_secret>`.
- createDraftListing POST /application/shops/{shop_id}/listings (form-encoded; required:
  quantity, title, description, price, who_made, when_made, taxonomy_id). type=download needs
  no shipping profile. Images and files are multipart uploads; a draft becomes public with
  PATCH .../listings/{id} state=active (needs at least one image).
- Rate limits per app: headers x-limit-per-second / x-remaining-today, 429 + retry-after.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from crayonlark.core.config import get_settings
from crayonlark.core.redis import get_redis
from crayonlark.integrations import oauth

AUTH_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
BASE = "https://api.etsy.com/v3/application"
SCOPES = "listings_r listings_w listings_d shops_r transactions_r"
PROVIDER = "etsy"
MAX_QPS = 5  # stay well under the app limit shown in the developer portal
TAG_RE = re.compile(r"[^a-z0-9 \-'™©®]")


class EtsyError(RuntimeError):
    pass


def configured() -> bool:
    s = get_settings()
    return bool(s.etsy_api_key and s.etsy_shared_secret and s.etsy_shop_id)


def redirect_uri() -> str:
    return get_settings().admin_site_url.rstrip("/") + "/api/oauth/etsy/callback"


def api_key() -> str:
    s = get_settings()
    return f"{s.etsy_api_key}:{s.etsy_shared_secret}"


def authorize_url(state: str, challenge: str) -> str:
    q = httpx.QueryParams(
        {
            "response_type": "code",
            "client_id": get_settings().etsy_api_key,
            "redirect_uri": redirect_uri(),
            "scope": SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTH_URL}?{q}"


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    r = httpx.post(TOKEN_URL, data=data, timeout=30)
    if r.status_code >= 400:
        raise EtsyError(f"token request failed: {r.status_code} {r.text[:300]}")
    out: dict[str, Any] = r.json()
    return out


def exchange_code(code: str, verifier: str) -> dict[str, Any]:
    return _token_request(
        {
            "grant_type": "authorization_code",
            "client_id": get_settings().etsy_api_key,
            "redirect_uri": redirect_uri(),
            "code": code,
            "code_verifier": verifier,
        }
    )


def refresh(refresh_token: str) -> dict[str, Any]:
    return _token_request(
        {
            "grant_type": "refresh_token",
            "client_id": get_settings().etsy_api_key,
            "refresh_token": refresh_token,
        }
    )


# --------------------------------------------------------------------------- payloads (pure)


def clean_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    for t in tags:
        t = TAG_RE.sub("", t.lower()).strip()[:20].strip()
        if t and t not in out:
            out.append(t)
    return out[:13]


def clean_title(title: str) -> str:
    # Etsy allows only one each of & : % and rejects ^ and $ in titles.
    t = re.sub(r"[\^$]", "", title)
    for ch in "&:%":
        first = t.find(ch)
        if first >= 0:
            t = t[: first + 1] + t[first + 1 :].replace(ch, " ")
    return re.sub(r"\s+", " ", t).strip()[:140]


def draft_form(
    *,
    title: str,
    description: str,
    price_cents: int,
    tags: list[str],
    taxonomy_id: int,
    when_made: str,
    quantity: int = 999,
) -> dict[str, str]:
    """createDraftListing body for a digital download made (designed) by the shop owner."""
    return {
        "quantity": str(quantity),
        "title": clean_title(title),
        "description": description,
        "price": f"{price_cents / 100:.2f}",
        "who_made": "i_did",  # shown by Etsy as "Designed by" the seller for digital items
        "when_made": when_made,
        "taxonomy_id": str(taxonomy_id),
        "type": "download",
        "is_supply": "false",
        "should_auto_renew": "false",
        "tags": ",".join(clean_tags(tags)),
    }


def draft_problems(form: dict[str, str]) -> list[str]:
    errs = []
    if form["taxonomy_id"] in ("", "0"):
        errs.append("set ETSY_TAXONOMY_ID (run `crayonlark etsy-taxonomy coloring`)")
    if len(form["tags"].split(",")) != 13:
        errs.append("Etsy listing needs 13 tags")
    if float(form["price"]) < 0.2:
        errs.append("price below Etsy minimum")
    low = (form["title"] + form["description"]).lower()
    if "handmade" in low or "hand-drawn" in low or "hand drawn" in low:
        errs.append('never call the item "handmade" or "hand-drawn"')
    if "Designed by" not in form["description"]:
        errs.append('description must include the "Designed by" disclosure line')
    return errs


# --------------------------------------------------------------------------- client


class Etsy:
    def __init__(self, session: Session, http: httpx.Client | None = None) -> None:
        self.session = session
        self.http = http or httpx.Client(timeout=60)
        self.shop_id = get_settings().etsy_shop_id

    def _throttle(self) -> None:
        r = get_redis()
        while True:
            key = f"etsy:qps:{int(time.time())}"
            n = r.incr(key)
            r.expire(key, 2)
            if int(n) <= MAX_QPS:
                return
            time.sleep(0.25)

    def request(self, method: str, path: str, **kw: Any) -> Any:
        token = oauth.access_token(self.session, PROVIDER, refresh)
        headers = {"x-api-key": api_key(), "Authorization": f"Bearer {token}"}
        for attempt in range(5):
            self._throttle()
            resp = self.http.request(method, f"{BASE}{path}", headers=headers, **kw)
            left = resp.headers.get("x-remaining-today")
            if left is not None:
                get_redis().set("etsy:remaining_today", left, ex=86400)
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(float(resp.headers.get("retry-after", 2**attempt)))
                continue
            if resp.status_code >= 400:
                raise EtsyError(f"{method} {path}: {resp.status_code} {resp.text[:400]}")
            return resp.json() if resp.content else {}
        raise EtsyError(f"{method} {path}: still rate limited after retries")

    def create_draft(self, form: dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = self.request("POST", f"/shops/{self.shop_id}/listings", data=form)
        return out

    def upload_image(self, listing_id: int, jpg: bytes, rank: int, alt: str) -> dict[str, Any]:
        out: dict[str, Any] = self.request(
            "POST",
            f"/shops/{self.shop_id}/listings/{listing_id}/images",
            files={"image": (f"image-{rank}.jpg", jpg, "image/jpeg")},
            data={"rank": str(rank), "alt_text": alt[:500]},
        )
        return out

    def upload_file(self, listing_id: int, pdf: bytes, name: str, rank: int) -> dict[str, Any]:
        out: dict[str, Any] = self.request(
            "POST",
            f"/shops/{self.shop_id}/listings/{listing_id}/files",
            files={"file": (name, pdf, "application/pdf")},
            data={"name": name, "rank": str(rank)},
        )
        return out

    def activate(self, listing_id: int) -> dict[str, Any]:
        out: dict[str, Any] = self.request(
            "PATCH", f"/shops/{self.shop_id}/listings/{listing_id}", data={"state": "active"}
        )
        return out

    def receipts(self, min_created: int, limit: int = 100) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self.request(
                "GET",
                f"/shops/{self.shop_id}/receipts",
                params={
                    "min_created": min_created,
                    "limit": limit,
                    "offset": offset,
                    "was_paid": "true",
                },
            )
            rows += page.get("results", [])
            offset += limit
            if offset >= int(page.get("count", 0)) or not page.get("results"):
                return rows

    def taxonomy(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = self.request("GET", "/seller-taxonomy/nodes").get("results", [])
        return out


def remaining_today() -> int | None:
    v = get_redis().get("etsy:remaining_today")
    return int(str(v)) if v is not None else None
