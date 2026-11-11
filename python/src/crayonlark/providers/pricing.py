"""USD prices for the paid models we can call, used by the budget guard.

Prices change: check the providers' pricing pages now and then and update this table (or override
a price without a deploy in admin → Settings → `model_prices`, same shape). An unknown model is
priced at UNKNOWN_* (deliberately expensive) so the budget guard errs on the safe side.
"""

from __future__ import annotations

from typing import Any

CHECKED = "2026-11-08"  # when these prices were last compared with the pricing pages

# (input, output) USD per 1M tokens. Thinking/reasoning tokens are billed as output.
TOKEN_PRICES: dict[str, tuple[float, float]] = {
    # Anthropic (checked 2026-11-08)
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    # OpenAI (checked 2026-11-08)
    "gpt-6-astra": (10.0, 50.0),
    "gpt-6.1-terra": (1.0, 5.0),
    "gpt-6-luna": (0.10, 0.50),
    # Google Gemini (checked 2026-11-08; intro prices end Nov 30 / Dec 31, later prices used)
    "gemini-4-argon": (4.0, 20.0),
    "gemini-3.1-pro-preview": (2.0, 12.0),
    "gemini-3.8-flash": (1.50, 7.50),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
}

# Image models priced by tokens: (text input, image output) USD per 1M tokens.
IMAGE_TOKEN_PRICES: dict[str, tuple[float, float]] = {
    "gpt-image-2.5-flare": (5.0, 30.0),
    "gpt-image-2.5-sunburst": (5.0, 30.0),
    "gpt-image-2.6-flare": (5.0, 30.0),
    "gpt-image-2.6-sunburst": (5.0, 30.0),
    "gemini-nano-banana-2.1": (0.5, 30.0),
    "gemini-3.1-flash-image": (0.5, 30.0),
    "gemini-3.1-flash-lite-image": (0.5, 30.0),
}

# Budget reservation per image (portrait, the quality we request): a cautious estimate; the
# real cost is computed from the usage the provider returns.
IMAGE_PRICES: dict[str, float] = {
    "gpt-image-2.5-flare": 0.06,
    "gpt-image-2.5-sunburst": 0.06,
    "gpt-image-2.6-flare": 0.06,
    "gpt-image-2.6-sunburst": 0.06,
    "gemini-nano-banana-2.1": 0.04,
    "gemini-3.1-flash-image": 0.07,
    "gemini-3.1-flash-lite-image": 0.04,
    "gemini-3-pro-image": 0.15,
    # DeepInfra, 1024x1536 at 4 steps (providers/image/deepinfra_image.py), checked 2026-11-12
    "black-forest-labs/FLUX-1-schnell": 0.003,
}

UNKNOWN_TOKEN_PRICE = (10.0, 50.0)
UNKNOWN_IMAGE_PRICE = 0.25


def _overrides() -> dict[str, Any]:
    try:
        from crayonlark.core import app_settings

        return dict(app_settings.get("model_prices") or {})
    except Exception:  # no database (unit tests, CLI without DB)
        return {}


def token_price(model: str) -> tuple[float, float]:
    over = _overrides().get("tokens", {}).get(model)
    if over:
        return float(over[0]), float(over[1])
    return TOKEN_PRICES.get(model, UNKNOWN_TOKEN_PRICE)


def image_price(model: str) -> float:
    over = _overrides().get("images", {}).get(model)
    if over is not None:
        return float(over)
    return IMAGE_PRICES.get(model, UNKNOWN_IMAGE_PRICE)


def image_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in IMAGE_TOKEN_PRICES:
        return image_price(model)
    pin, pout = IMAGE_TOKEN_PRICES[model]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


def token_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Cost in USD. Cache reads bill at 10 % and cache writes at 125 % of the input price."""
    pin, pout = token_price(model)
    return (
        input_tokens * pin
        + output_tokens * pout
        + cache_read_tokens * pin * 0.1
        + cache_write_tokens * pin * 1.25
    ) / 1_000_000


def estimate_tokens(text: str) -> int:
    """Rough token count (about 3.5 characters per token) for budget reservations."""
    return max(1, round(len(text) / 3.5))
