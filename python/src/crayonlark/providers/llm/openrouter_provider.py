"""OpenRouter chat completions (`POST /api/v1/chat/completions`), plain HTTP.

Structured output: `response_format` json_schema with strict=true, and
`provider.require_parameters` so only providers that support it are used. The real cost comes
back in `usage.cost` (OpenRouter credits = USD); if it's missing we price it from the live
model list. Shapes checked against the official docs on 2026-11-09.
"""

from __future__ import annotations

import base64
from typing import Any

from crayonlark.providers import openrouter, pricing
from crayonlark.providers.http import post_json
from crayonlark.providers.llm.base import (
    AgentTask,
    Usage,
    estimate_input_tokens,
    image_mime,
    portable_schema,
)

URL = f"{openrouter.BASE}/chat/completions"


def _price(model: str) -> tuple[float, float]:
    return openrouter.token_price(model) or pricing.token_price(model)


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self) -> None:
        openrouter.key()  # fail early without a key

    def estimate_usd(self, task: AgentTask[Any], model: str) -> float:
        if not model:
            raise RuntimeError("pick an OpenRouter model in admin → Settings → AI providers")
        pin, pout = _price(model)
        return (estimate_input_tokens(task) * pin + task.max_tokens * 2 * pout) / 1_000_000

    @staticmethod
    def request(
        task: AgentTask[Any], model: str, extra_user: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": task.prompt + (f"\n\n{extra_user}" if extra_user else "")}
        ]
        for img in task.images:
            b64 = base64.b64encode(img).decode()
            url = f"data:{image_mime(img)};base64,{b64}"
            content.append({"type": "image_url", "image_url": {"url": url}})
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": task.system},
                {"role": "user", "content": content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": task.agent,
                    "strict": True,
                    "schema": portable_schema(task.schema),
                },
            },
            "provider": {"require_parameters": True},
            # reasoning tokens count against this limit, so leave room
            "max_tokens": max(4000, task.max_tokens * 3),
        }
        if options.get("effort"):  # only when chosen: not every model can reason
            body["reasoning"] = {"effort": options["effort"]}
        return body

    @staticmethod
    def parse(data: dict[str, Any], model: str) -> tuple[str, Usage]:
        openrouter.raise_on_error(data)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        finish = str(choice.get("finish_reason") or "")
        stop = "refusal" if msg.get("refusal") or finish == "content_filter" else ""
        if not stop and finish == "length":
            stop = "max_tokens"
        u = data.get("usage") or {}
        inp, out = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
        used = str(data.get("model") or model)
        if u.get("cost") is not None:
            cost = float(u["cost"])
        else:
            pin, pout = _price(used)
            cost = (inp * pin + out * pout) / 1_000_000
        return str(text), Usage(inp, out, cost, stop, used)

    def complete_json(
        self,
        task: AgentTask[Any],
        model: str,
        extra_user: str = "",
        options: dict[str, Any] | None = None,
    ) -> tuple[str, Usage]:
        if not model:
            raise RuntimeError("pick an OpenRouter model in admin → Settings → AI providers")
        body = self.request(task, model, extra_user, options or {})
        return self.parse(post_json(URL, openrouter.headers(), body), model)
