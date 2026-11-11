"""OpenRouter image generation (`POST /api/v1/images`), portrait 3:4 at 1K, PNG.

The answer has base64 in data[].b64_json and the real cost in usage.cost. Failed generations
are not billed. Shapes checked against the official docs on 2026-11-09.
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.providers import openrouter, pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.image.base import ImageResult, data_url

URL = f"{openrouter.BASE}/images"


class OpenRouterImageProvider:
    name = "openrouter"

    def __init__(self) -> None:
        openrouter.key()

    def estimate_usd(self, model: str) -> float:
        # per-image prices differ by model and provider: reserve the safe (high) default unless
        # an override is set in Settings → model_prices; the real cost is settled afterwards
        return pricing.image_price(model)

    @staticmethod
    def request(prompt: str, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "aspect_ratio": "3:4",
            "resolution": "1K",
            "output_format": "png",
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str, estimate: float) -> ImageResult:
        openrouter.raise_on_error(data)
        items = data.get("data") or []
        if not items or not items[0].get("b64_json"):
            raise RuntimeError("openrouter returned no image")
        cost = (data.get("usage") or {}).get("cost")
        return ImageResult(
            base64.b64decode(items[0]["b64_json"]),
            float(cost) if cost is not None else estimate,
            model,
        )

    def generate(self, prompt: str, model: str) -> ImageResult:
        if not model:
            raise RuntimeError("no OpenRouter image model set (defaults: providers/llm/base.py)")
        data = post_json(URL, openrouter.headers(), self.request(prompt, model))
        return self.parse(data, model, self.estimate_usd(model))

    @classmethod
    def edit_request(cls, prompt: str, image_png: bytes, model: str) -> dict[str, Any]:
        ref = {"type": "image_url", "image_url": {"url": data_url(image_png)}}
        return {**cls.request(prompt, model), "input_references": [ref]}

    def edit(self, prompt: str, image_png: bytes, model: str) -> ImageResult:
        if not model:
            raise RuntimeError("no OpenRouter image model set (defaults: providers/llm/base.py)")
        data = post_json(URL, openrouter.headers(), self.edit_request(prompt, image_png, model))
        return self.parse(data, model, self.estimate_usd(model))
