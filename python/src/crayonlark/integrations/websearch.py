"""Optional web search for the research agent (WEBSEARCH_PROVIDER = brave | tavily).

Official search APIs only. Results from Amazon and Etsy are excluded: we never scrape or read
their pages (CLAUDE.md hard rule). Each request goes through the budget guard (kind="search").
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from crayonlark.core.config import get_settings
from crayonlark.providers.http import get_json, post_json

EXCLUDED = ("amazon.", "etsy.com", "amzn.")
COST_USD = {"brave": 0.005, "tavily": 0.008}  # per request / basic search (checked 2026-11-08)


def configured() -> bool:
    s = get_settings()
    return s.websearch_provider in COST_USD and bool(s.websearch_api_key)


def allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return not any(x in host for x in EXCLUDED)


def search(query: str, count: int = 8, agent: str = "research") -> list[dict[str, str]]:
    """[{title, url, snippet}] with Amazon/Etsy results removed. Empty when not configured."""
    from crayonlark.core import budget

    if not configured():
        return []
    s = get_settings()
    provider, key = s.websearch_provider, s.websearch_api_key
    with budget.paid_call(provider, "search", agent, "search", COST_USD[provider]) as call:
        if provider == "brave":
            data = get_json(
                "https://api.search.brave.com/res/v1/web/search",
                {"X-Subscription-Token": key, "Accept": "application/json"},
                {"q": query, "count": min(20, count + 4), "safesearch": "strict"},
            )
            rows = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", ""),
                }
                for r in (data.get("web") or {}).get("results") or []
            ]
        else:
            data = post_json(
                "https://api.tavily.com/search",
                {"Authorization": f"Bearer {key}"},
                {
                    "query": query,
                    "max_results": min(20, count),
                    "search_depth": "basic",
                    "exclude_domains": ["amazon.com", "amazon.co.uk", "amazon.in", "etsy.com"],
                },
                timeout=60,
            )
            rows = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                }
                for r in data.get("results") or []
            ]
        call.actual_usd = COST_USD[provider]
    return [_trim(r) for r in rows if allowed(r["url"])][:count]


def _trim(r: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(r["title"])[:200],
        "url": str(r["url"])[:300],
        "snippet": str(r["snippet"])[:400],
    }


def niche_search(theme: str) -> list[dict[str, str]]:
    """Two short searches for the research agent: demand/trends and what parents look for."""
    out = search(f"{theme} coloring pages for kids trends", 6)
    out += search(f"{theme} activity book ideas for children", 4)
    unique: dict[str, dict[str, str]] = {}
    for r in out:
        unique.setdefault(r["url"], r)
    return list(unique.values())
