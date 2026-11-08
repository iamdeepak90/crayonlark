"""Tiny JSON-over-HTTP helper for the providers we call without a vendor SDK."""

from __future__ import annotations

from typing import Any

import httpx

from crayonlark.providers import ProviderBusy


def post_json(
    url: str, headers: dict[str, str], body: dict[str, Any], timeout: float = 300
) -> dict[str, Any]:
    """POST JSON and return the decoded answer. 429/5xx → ProviderBusy (the job retries with
    backoff); other errors raise RuntimeError with the provider's message."""
    r = httpx.post(url, headers=headers, json=body, timeout=timeout)
    return _decode(r)


def get_json(
    url: str, headers: dict[str, str], params: dict[str, Any], timeout: float = 30
) -> dict[str, Any]:
    r = httpx.get(url, headers=headers, params=params, timeout=timeout)
    return _decode(r)


def _decode(r: httpx.Response) -> dict[str, Any]:
    if r.status_code == 429 or r.status_code >= 500:
        raise ProviderBusy(f"{r.request.url.host} {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400:
        raise RuntimeError(f"{r.request.url.host} {r.status_code}: {r.text[:1000]}")
    data: dict[str, Any] = r.json()
    return data
