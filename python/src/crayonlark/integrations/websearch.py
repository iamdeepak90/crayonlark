"""Optional web search for the research agent: LangSearch and/or TinyFish (one key or both).

Both are official search-results APIs (title, link, snippet); neither browses pages for us.
Amazon and Etsy are excluded twice: in the request (exclude-domains parameter) and again on the
results by host. We never read their pages (CLAUDE.md hard rule). Each request still goes through
the budget guard (kind="search") so it shows up in Costs, at $0 because both are free.

Docs (checked 2026-11-10):
- LangSearch: POST https://api.langsearch.com/v1/web-search, Bearer key,
  results in data.webPages.value[] {name, url, snippet}. Free plan with a daily token allowance.
- TinyFish: GET https://api.search.tinyfish.ai, X-API-Key header,
  results in results[] {title, url, snippet}. Free (30/min, 500/hour, 12,000/day).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from crayonlark.core.config import get_settings
from crayonlark.providers.http import get_json, post_json

log = logging.getLogger(__name__)

PROVIDERS = ("langsearch", "tinyfish")
EXCLUDED = ("amazon.", "etsy.com", "amzn.")
EXCLUDE_DOMAINS = ["amazon.com", "amazon.co.uk", "amazon.in", "amazon.de", "amzn.to", "etsy.com"]
COST_USD = {"langsearch": 0.0, "tinyfish": 0.0}  # both free (see docstring)


def keys() -> dict[str, str]:
    """Configured providers → API key, in the order they are asked."""
    s = get_settings()
    found = {"langsearch": s.langsearch_api_key, "tinyfish": s.tinyfish_api_key}
    return {p: k for p, k in found.items() if k}


def configured() -> bool:
    return bool(keys())


def allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return not any(x in host for x in EXCLUDED)


def _langsearch(key: str, query: str, count: int) -> list[dict[str, Any]]:
    data = post_json(
        "https://api.langsearch.com/v1/web-search",
        {"Authorization": f"Bearer {key}"},
        {"query": query, "count": min(50, count + 4), "excludeDomains": EXCLUDE_DOMAINS},
        timeout=60,
    )
    rows = ((data.get("data") or {}).get("webPages") or {}).get("value") or []
    return [
        {"title": r.get("name", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")}
        for r in rows
    ]


def _tinyfish(key: str, query: str, count: int) -> list[dict[str, Any]]:
    data = get_json(
        "https://api.search.tinyfish.ai",
        {"X-API-Key": key},
        {
            "query": query,
            "location": "US",
            "language": "en",
            "exclude_domains": ",".join(EXCLUDE_DOMAINS),
        },
        timeout=60,
    )
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")}
        for r in data.get("results") or []
    ]


def _one(provider: str, key: str, query: str, count: int, agent: str) -> list[dict[str, Any]]:
    from crayonlark.core import budget

    with budget.paid_call(provider, "search", agent, "search", COST_USD[provider]) as call:
        rows = (_langsearch if provider == "langsearch" else _tinyfish)(key, query, count)
        call.actual_usd = COST_USD[provider]
    return rows


def search(query: str, count: int = 8, agent: str = "research") -> list[dict[str, str]]:
    """[{title, url, snippet}] from every configured provider, merged (alternating, no duplicate
    links), Amazon/Etsy removed. Empty when none is configured. One provider failing is fine;
    only when all fail is the last error raised."""
    from crayonlark.core.budget import BudgetExceeded

    per_provider: list[list[dict[str, Any]]] = []
    errors: list[Exception] = []
    for provider, key in keys().items():
        try:
            per_provider.append(_one(provider, key, query, count, agent))
        except BudgetExceeded:
            raise
        except Exception as exc:
            log.warning("web search via %s failed: %s", provider, exc)
            errors.append(exc)
    if errors and not per_provider:
        raise errors[-1]
    merged: dict[str, dict[str, str]] = {}
    for i in range(max((len(r) for r in per_provider), default=0)):
        for rows in per_provider:
            if i < len(rows) and rows[i]["url"] and allowed(rows[i]["url"]):
                merged.setdefault(rows[i]["url"], _trim(rows[i]))
    return list(merged.values())[:count]


def _trim(r: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(r["title"])[:200],
        "url": str(r["url"])[:300],
        "snippet": str(r["snippet"])[:400],
    }


def niche_search(theme: str) -> list[dict[str, str]]:
    """Two short searches for the research agent: demand/trends and what parents look for."""
    n = 2 if len(keys()) > 1 else 1  # with both providers, keep more of the merged results
    out = search(f"{theme} coloring pages for kids trends", 6 * n)
    out += search(f"{theme} activity book ideas for children", 4 * n)
    unique: dict[str, dict[str, str]] = {}
    for r in out:
        unique.setdefault(r["url"], r)
    return list(unique.values())
