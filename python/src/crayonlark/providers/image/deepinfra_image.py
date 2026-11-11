"""DeepInfra FLUX.1 [schnell] (Apache 2.0): the cheapest picture model we use.

`POST https://api.deepinfra.com/v1/inference/black-forest-labs/FLUX-1-schnell`, portrait
1024x1536, 4 steps. Price checked 2026-11-12 on api.deepinfra.com/models: 0.05 cents per "image
unit" (one 1024x1024 image at 1 step), so one picture here is 1.5 MP x 4 steps = 6 units =
$0.003. The response reports the real cost (`inference_status.cost`), which we record.

No picture editing: colour examples fall back to the free auto-fill (core/color_refs.py).
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.core.config import get_settings
from crayonlark.providers import pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.image.base import ImageResult

DEFAULT_MODEL = "black-forest-labs/FLUX-1-schnell"
URL = "https://api.deepinfra.com/v1/inference/{model}"
WIDTH, HEIGHT, STEPS = 1024, 1536, 4  # schnell is distilled for 1-4 steps; 4 = cleanest lines
CENTS_PER_UNIT = 0.05  # 1024x1024 at 1 step


def unit_price_usd(width: int = WIDTH, height: int = HEIGHT, steps: int = STEPS) -> float:
    return CENTS_PER_UNIT / 100 * (width * height) / (1024 * 1024) * steps


class DeepInfraImageProvider:
    name = "deepinfra"

    def __init__(self) -> None:
        self.key = get_settings().deepinfra_api_key
        if not self.key:
            raise RuntimeError("DeepInfra API key is not set (Settings → Keys and connections)")

    def estimate_usd(self, model: str) -> float:
        return pricing.image_price(model or DEFAULT_MODEL)

    @staticmethod
    def request(prompt: str) -> dict[str, Any]:
        return {
            "prompt": prompt,
            "width": WIDTH,
            "height": HEIGHT,
            "num_inference_steps": STEPS,
            "num_images": 1,
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> ImageResult:
        images = data.get("images") or []
        if not images or not isinstance(images[0], str):
            raise RuntimeError(f"DeepInfra returned no image: {str(data)[:300]}")
        if any(data.get("nsfw_content_detected") or []):
            raise RuntimeError("DeepInfra flagged the picture as unsafe; it was not used")
        b64 = images[0].split(",", 1)[1] if images[0].startswith("data:") else images[0]
        cost = float((data.get("inference_status") or {}).get("cost") or 0)
        return ImageResult(base64.b64decode(b64), cost or unit_price_usd(), model)

    def generate(self, prompt: str, model: str) -> ImageResult:
        model = model or DEFAULT_MODEL
        data = post_json(
            URL.format(model=model),
            {"Authorization": f"Bearer {self.key}"},
            self.request(prompt),
            timeout=180,
        )
        return self.parse(data, model)

    def edit(self, prompt: str, image_png: bytes, model: str) -> ImageResult:
        raise NotImplementedError("DeepInfra FLUX schnell does not edit pictures")
