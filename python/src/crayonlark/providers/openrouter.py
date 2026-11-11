"""OpenRouter (openrouter.ai): one key for many models from many companies.

Shared bits for the LLM and image providers: auth headers, and the live model lists with
prices, which the admin uses for model suggestions and the budget guard uses for estimates.
Shapes checked against the official docs on 2026-11-09; see docs/DECISIONS.md.
"""

from __future__ import annotations

import time
from typing import Any

from crayonlark.core.config import get_settings
from crayonlark.providers.http import get_json

BASE = "https://openrouter.ai/api/v1"
CACHE_SECONDS = 6 * 3600
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def key() -> str:
    k = get_settings().openrouter_api_key
    if not k:
        raise RuntimeError("OpenRouter API key is not set (Settings → Keys and connections)")
    return k


def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key()}",
        # optional attribution shown on openrouter.ai
        "HTTP-Referer": get_settings().public_site_url,
        "X-OpenRouter-Title": "Crayonlark",
    }


def _per_million(value: Any) -> float | None:
    """OpenRouter prices are USD per token as strings ("0.000003") → USD per 1M tokens."""
    try:
        return round(float(value) * 1_000_000, 6)
    except (TypeError, ValueError):
        return None


def parse_text_models(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Models that can answer with a JSON schema (all our agents need that). Pure; unit-tested."""
    out = []
    for m in data.get("data") or []:
        params = set(m.get("supported_parameters") or [])
        if not params & {"structured_outputs", "response_format"}:
            continue
        price = m.get("pricing") or {}
        arch = m.get("architecture") or {}
        out.append(
            {
                "id": m.get("id"),
                "name": m.get("name") or m.get("id"),
                "input_per_m": _per_million(price.get("prompt")),
                "output_per_m": _per_million(price.get("completion")),
                "vision": "image" in (arch.get("input_modalities") or []),
                "reasoning": "reasoning" in params,
            }
        )
    return sorted(out, key=lambda x: str(x["id"]))


def parse_image_models(data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        ({"id": m.get("id"), "name": m.get("name") or m.get("id")} for m in data.get("data") or []),
        key=lambda x: str(x["id"]),
    )


def _cached(name: str, fetch: Any) -> list[dict[str, Any]]:
    hit = _cache.get(name)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        models: list[dict[str, Any]] = fetch()
    except Exception:
        return hit[1] if hit else []  # keep the old list (or none) if OpenRouter is down
    _cache[name] = (time.time(), models)
    return models


def text_models() -> list[dict[str, Any]]:
    return _cached("text", lambda: parse_text_models(get_json(f"{BASE}/models", headers(), {})))


def image_models() -> list[dict[str, Any]]:
    return _cached(
        "image", lambda: parse_image_models(get_json(f"{BASE}/images/models", headers(), {}))
    )


def token_price(model: str) -> tuple[float, float] | None:
    """USD per 1M input/output tokens from the live list, or None if unknown."""
    for m in text_models():
        if m["id"] == model and m["input_per_m"] is not None and m["output_per_m"] is not None:
            return float(m["input_per_m"]), float(m["output_per_m"])
    return None


def raise_on_error(data: dict[str, Any]) -> None:
    """OpenRouter can return an error object even with HTTP 200."""
    err = data.get("error")
    if err:
        from crayonlark.providers import ProviderBusy

        if not isinstance(err, dict):
            err = {"message": str(err)}
        code = int(err.get("code") or 0)
        msg = f"openrouter {code}: {str(err.get('message'))[:500]}"
        if code == 429 or code >= 500:
            raise ProviderBusy(msg)
        raise RuntimeError(msg)
