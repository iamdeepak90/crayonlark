"""One interface for image generation (OpenAI, Gemini, OpenRouter) plus "manual" mode.

Manual mode costs nothing: I make the pictures in the ChatGPT/Gemini apps from the prompts shown
in admin and upload them (or drop them in the `inbox` bucket); the pipeline continues from there.
Paid providers always run inside the budget guard (`generate()` below).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ManualMode(RuntimeError):
    """The image provider is "manual": nothing to generate, wait for uploads."""


@dataclass
class ImageResult:
    data: bytes  # PNG or JPEG bytes
    cost_usd: float
    model: str


class ImageProvider(Protocol):
    name: str

    def generate(self, prompt: str, model: str) -> ImageResult: ...

    def estimate_usd(self, model: str) -> float: ...


def image_config() -> dict[str, str]:
    from crayonlark.core import app_settings

    return dict(app_settings.get("image_provider") or {"provider": "manual", "model": ""})


def get_image_provider(name: str) -> Any:
    match name:
        case "openai":
            from crayonlark.providers.image.openai_image import OpenAIImageProvider

            return OpenAIImageProvider()
        case "gemini":
            from crayonlark.providers.image.gemini_image import GeminiImageProvider

            return GeminiImageProvider()
        case "openrouter":
            from crayonlark.providers.image.openrouter_image import OpenRouterImageProvider

            return OpenRouterImageProvider()
        case "manual":
            raise ManualMode("image provider is manual: upload images in admin")
    raise ValueError(f"unknown image provider {name!r} (use openai, gemini, openrouter or manual)")


def generate(prompt: str, agent: str = "art", book_id: int | None = None) -> ImageResult:
    """Generate one image with the configured provider, inside the budget guard."""
    from crayonlark.core import budget

    cfg = image_config()
    provider = get_image_provider(cfg.get("provider", "manual"))
    model = cfg.get("model") or ""
    with budget.paid_call(
        provider.name, model, agent, "image", provider.estimate_usd(model), book_id=book_id
    ) as call:
        result: ImageResult = provider.generate(prompt, model)
        call.actual_usd, call.images, call.model = result.cost_usd, 1, result.model
    return result
