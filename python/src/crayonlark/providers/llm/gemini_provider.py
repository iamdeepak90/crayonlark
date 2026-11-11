"""Google Gemini via `models/{model}:generateContent`, plain HTTP.

JSON output uses responseMimeType=application/json + responseJsonSchema (as in Google's
structured-output guide). Google now marks these fields as superseded by `responseFormat`; if
they stop working, switch `request()` below. Checked 2026-11-08; see docs/DECISIONS.md.
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.core.config import get_settings
from crayonlark.providers import pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.llm.base import (
    AgentTask,
    Usage,
    estimate_input_tokens,
    image_mime,
    portable_schema,
)

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.8-flash"


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        self.key = get_settings().gemini_api_key
        if not self.key:
            raise RuntimeError("Gemini API key is not set (Settings → Keys and connections)")

    def estimate_usd(self, task: AgentTask[Any], model: str) -> float:
        return pricing.token_cost(
            model or DEFAULT_MODEL, estimate_input_tokens(task), task.max_tokens * 2
        )

    @staticmethod
    def request(task: AgentTask[Any], extra_user: str) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [
            {"text": task.prompt + (f"\n\n{extra_user}" if extra_user else "")}
        ]
        for img in task.images:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": image_mime(img),
                        "data": base64.b64encode(img).decode(),
                    }
                }
            )
        return {
            "systemInstruction": {"parts": [{"text": task.system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "maxOutputTokens": max(4000, task.max_tokens * 3),  # thinking counts here too
                "responseMimeType": "application/json",
                "responseJsonSchema": portable_schema(task.schema),
            },
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> tuple[str, Usage]:
        cands = data.get("candidates") or []
        text = ""
        stop = ""
        if cands:
            parts = (cands[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            reason = str(cands[0].get("finishReason") or "")
            stop = "refusal" if reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST") else reason
        elif (data.get("promptFeedback") or {}).get("blockReason"):
            stop = "refusal"
        u = data.get("usageMetadata") or {}
        inp = int(u.get("promptTokenCount") or 0)
        cached = int(u.get("cachedContentTokenCount") or 0)
        out = int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
        pin, pout = pricing.token_price(model)
        cost = ((inp - cached) * pin + cached * pin * 0.1 + out * pout) / 1_000_000
        return text, Usage(inp, out, cost, stop, model)

    def complete_json(
        self,
        task: AgentTask[Any],
        model: str,
        extra_user: str = "",
        options: dict[str, Any] | None = None,
    ) -> tuple[str, Usage]:
        model = model or DEFAULT_MODEL
        data = post_json(
            f"{BASE}/{model}:generateContent",
            {"x-goog-api-key": self.key},
            self.request(task, extra_user),
        )
        return self.parse(data, model)
