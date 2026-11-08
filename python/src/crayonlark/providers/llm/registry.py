"""Provider lookup by name. Paid providers are imported lazily (keys are optional)."""

from __future__ import annotations

from typing import Any


def get_provider(name: str) -> Any:
    match name:
        case "anthropic":
            from crayonlark.providers.llm.anthropic_provider import AnthropicProvider

            return AnthropicProvider()
        case "openai":
            from crayonlark.providers.llm.openai_provider import OpenAIProvider

            return OpenAIProvider()
        case "gemini":
            from crayonlark.providers.llm.gemini_provider import GeminiProvider

            return GeminiProvider()
    raise ValueError(f"unknown LLM provider {name!r} (use anthropic, openai, gemini or offline)")
