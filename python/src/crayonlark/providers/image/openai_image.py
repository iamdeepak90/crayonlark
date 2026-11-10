"""OpenAI image generation (`POST /v1/images/generations`), portrait 1024x1536, PNG.

Cost comes from the `usage` block (text input tokens + image output tokens). Checked
2026-11-08: gpt-image-1 is shut down; the image guide recommends the gpt-image-2.5 family.
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.core.config import get_settings
from crayonlark.providers import pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.image.base import ImageResult, data_url

URL = "https://api.openai.com/v1/images/generations"
EDIT_URL = "https://api.openai.com/v1/images/edits"  # JSON body: images[].image_url (data URL)
DEFAULT_MODEL = "gpt-image-2.5-flare"


class OpenAIImageProvider:
    name = "openai"

    def __init__(self) -> None:
        self.key = get_settings().openai_api_key
        if not self.key:
            raise RuntimeError("OpenAI API key is not set (Settings → Integrations)")

    def estimate_usd(self, model: str) -> float:
        return pricing.image_price(model or DEFAULT_MODEL)

    @staticmethod
    def request(prompt: str, model: str) -> dict[str, Any]:
        return {
            "model": model or DEFAULT_MODEL,
            "prompt": prompt,
            "size": "1024x1536",
            "quality": "medium",
            "n": 1,
            "output_format": "png",
            "background": "opaque",
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> ImageResult:
        items = data.get("data") or []
        if not items or not items[0].get("b64_json"):
            raise RuntimeError(f"OpenAI returned no image: {str(data)[:300]}")
        png = base64.b64decode(items[0]["b64_json"])
        u = data.get("usage") or {}
        cost = (
            pricing.image_token_cost(
                model, int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
            )
            if u
            else pricing.image_price(model)
        )
        return ImageResult(png, cost, model)

    def generate(self, prompt: str, model: str) -> ImageResult:
        body = self.request(prompt, model)
        data = post_json(URL, {"Authorization": f"Bearer {self.key}"}, body, timeout=300)
        return self.parse(data, body["model"])

    @classmethod
    def edit_request(cls, prompt: str, image_png: bytes, model: str) -> dict[str, Any]:
        return {**cls.request(prompt, model), "images": [{"image_url": data_url(image_png)}]}

    def edit(self, prompt: str, image_png: bytes, model: str) -> ImageResult:
        body = self.edit_request(prompt, image_png, model)
        data = post_json(EDIT_URL, {"Authorization": f"Bearer {self.key}"}, body, timeout=300)
        return self.parse(data, body["model"])
