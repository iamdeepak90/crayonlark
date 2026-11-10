"""Gemini image generation ("Nano Banana" models) via generateContent, portrait 3:4 at 1K.

Imagen is shut down (checked 2026-11-08). Cost comes from usageMetadata when present.
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.core.config import get_settings
from crayonlark.providers import pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.image.base import ImageResult

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-nano-banana-2.1"


class GeminiImageProvider:
    name = "gemini"

    def __init__(self) -> None:
        self.key = get_settings().gemini_api_key
        if not self.key:
            raise RuntimeError("Gemini API key is not set (Settings → Integrations)")

    def estimate_usd(self, model: str) -> float:
        return pricing.image_price(model or DEFAULT_MODEL)

    @staticmethod
    def request(prompt: str, image_png: bytes | None = None) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [{"text": prompt}]
        if image_png is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64.b64encode(image_png).decode(),
                    }
                }
            )
        return {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": "3:4", "imageSize": "1K"},
            },
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> ImageResult:
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    u = data.get("usageMetadata") or {}
                    out = int(u.get("candidatesTokenCount") or 0)
                    cost = (
                        pricing.image_token_cost(model, int(u.get("promptTokenCount") or 0), out)
                        if out
                        else pricing.image_price(model)
                    )
                    return ImageResult(base64.b64decode(inline["data"]), cost, model)
        raise RuntimeError(f"Gemini returned no image: {str(data)[:300]}")

    def generate(self, prompt: str, model: str) -> ImageResult:
        model = model or DEFAULT_MODEL
        data = post_json(
            f"{BASE}/{model}:generateContent", {"x-goog-api-key": self.key}, self.request(prompt)
        )
        return self.parse(data, model)

    def edit(self, prompt: str, image_png: bytes, model: str) -> ImageResult:
        model = model or DEFAULT_MODEL
        body = self.request(prompt, image_png)
        data = post_json(f"{BASE}/{model}:generateContent", {"x-goog-api-key": self.key}, body)
        return self.parse(data, model)
