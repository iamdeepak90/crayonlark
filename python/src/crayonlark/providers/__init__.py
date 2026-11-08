"""Paid AI providers (LLM + image) behind small interfaces; see llm/base.py and image/base.py."""

from __future__ import annotations


class ProviderBusy(RuntimeError):
    """Rate limited or a 5xx from a provider after our own retries: safe to retry later."""


def transient_errors() -> tuple[type[BaseException], ...]:
    """Errors worth retrying a job for (network trouble, rate limits, provider outages)."""
    import anthropic
    import httpx

    return (
        ConnectionError,
        TimeoutError,
        ProviderBusy,
        httpx.TransportError,
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.InternalServerError,
    )
