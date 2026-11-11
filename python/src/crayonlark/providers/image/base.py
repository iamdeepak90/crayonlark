"""One interface for image generation (OpenAI, Gemini, OpenRouter, DeepInfra) plus "manual" mode.

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

    def edit(self, prompt: str, image_png: bytes, model: str) -> ImageResult:
        """Change an existing picture (used to colour a line drawing)."""
        ...

    def estimate_usd(self, model: str) -> float: ...


def image_config() -> dict[str, str]:
    """Fixed in code: DeepInfra FLUX.1 schnell once its key is set, else manual uploads."""
    from crayonlark.core import app_settings
    from crayonlark.core.config import get_settings

    stored = app_settings.get("image_provider")
    if stored:  # not shown in admin any more; kept for tests and emergencies
        return dict(stored)
    if get_settings().deepinfra_api_key:
        return {"provider": "deepinfra", "model": "black-forest-labs/FLUX-1-schnell"}
    return {"provider": "manual", "model": ""}


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
        case "deepinfra":
            from crayonlark.providers.image.deepinfra_image import DeepInfraImageProvider

            return DeepInfraImageProvider()
        case "manual":
            raise ManualMode("image provider is manual: upload images in admin")
    raise ValueError(
        f"unknown image provider {name!r} (use openai, gemini, openrouter, deepinfra or manual)"
    )


def generate(prompt: str, agent: str = "art", book_id: int | None = None) -> ImageResult:
    """Generate one image with the configured provider, inside the budget guard."""
    return _paid(lambda p, m: p.generate(prompt, m), agent, book_id)


def edit(
    prompt: str, image_png: bytes, agent: str = "color_ref", book_id: int | None = None
) -> ImageResult:
    """Edit one picture with the configured provider, inside the budget guard."""
    return _paid(lambda p, m: p.edit(prompt, image_png, m), agent, book_id)


def _paid(call_provider: Any, agent: str, book_id: int | None) -> ImageResult:
    from crayonlark.core import budget

    cfg = image_config()
    provider = get_image_provider(cfg.get("provider", "manual"))
    model = cfg.get("model") or ""
    with budget.paid_call(
        provider.name, model, agent, "image", provider.estimate_usd(model), book_id=book_id
    ) as call:
        result: ImageResult = call_provider(provider, model)
        call.actual_usd, call.images, call.model = result.cost_usd, 1, result.model
    return result


def data_url(png: bytes) -> str:
    import base64

    return "data:image/png;base64," + base64.b64encode(png).decode()
