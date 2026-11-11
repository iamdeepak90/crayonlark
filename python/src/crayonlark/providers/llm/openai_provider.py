"""OpenAI via the Responses API (`POST /v1/responses`), plain HTTP.

Structured output uses `text.format` json_schema with strict=true (schema from
base.portable_schema). Images are sent as base64 data URLs. Shapes checked against the official
docs on 2026-11-08; see docs/DECISIONS.md.
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

URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-6.1-terra"


class OpenAIProvider:
    name = "openai"

    def __init__(self) -> None:
        self.key = get_settings().openai_api_key
        if not self.key:
            raise RuntimeError("OpenAI API key is not set (Settings → Keys and connections)")

    def estimate_usd(self, task: AgentTask[Any], model: str) -> float:
        return pricing.token_cost(
            model or DEFAULT_MODEL, estimate_input_tokens(task), task.max_tokens * 2
        )

    @staticmethod
    def request(
        task: AgentTask[Any], model: str, extra_user: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": task.prompt + (f"\n\n{extra_user}" if extra_user else ""),
            }
        ]
        for img in task.images:
            b64 = base64.b64encode(img).decode()
            content.append(
                {"type": "input_image", "image_url": f"data:{image_mime(img)};base64,{b64}"}
            )
        return {
            "model": model or DEFAULT_MODEL,
            "instructions": task.system,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": task.agent,
                    "schema": portable_schema(task.schema),
                    "strict": True,
                }
            },
            # reasoning tokens count against this limit, so leave room
            "max_output_tokens": max(4000, task.max_tokens * 3),
            "reasoning": {"effort": options.get("effort") or "low"},
        }

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> tuple[str, Usage]:
        text, stop = "", ""
        for item in data.get("output") or []:
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    text += part.get("text", "")
                elif part.get("type") == "refusal":
                    stop = "refusal"
        if not stop and data.get("incomplete_details"):
            stop = str(data["incomplete_details"].get("reason", "incomplete"))
        u = data.get("usage") or {}
        cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
        used = str(data.get("model") or model)
        pin, pout = pricing.token_price(used)
        # input_tokens includes the cached ones, which bill at 10 %
        cost = ((inp - cached) * pin + cached * pin * 0.1 + out * pout) / 1_000_000
        return text, Usage(inp, out, cost, stop, used)

    def complete_json(
        self,
        task: AgentTask[Any],
        model: str,
        extra_user: str = "",
        options: dict[str, Any] | None = None,
    ) -> tuple[str, Usage]:
        body = self.request(task, model, extra_user, options or {})
        data = post_json(URL, {"Authorization": f"Bearer {self.key}"}, body)
        return self.parse(data, body["model"])
