"""Claude via the official `anthropic` SDK.

- Structured output: `output_config.format` with a JSON schema made from the agent's Pydantic
  model by `anthropic.transform_schema` (it moves constraints such as max_length into the
  description; Pydantic still checks them in run_task).
- Thinking is adaptive by default on current models; `effort` (low|medium|high|xhigh|max) comes
  from the agent's settings entry, default "medium".
- Requests are streamed (thinking can make answers long) and we keep only the final message.
- On models that support it, a safety refusal is retried server-side on a fallback model
  (`fallbacks="default"`). The cost is priced by the model that actually answered.
"""

from __future__ import annotations

import base64
from typing import Any

import anthropic

from crayonlark.core.config import get_settings
from crayonlark.providers import pricing
from crayonlark.providers.llm.base import AgentTask, Usage, estimate_input_tokens, image_mime

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MIN_MAX_TOKENS = 16000  # room for adaptive thinking before the JSON answer
TRANSIENT = (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        if client is None:
            key = get_settings().anthropic_api_key
            if not key:
                raise RuntimeError("Anthropic API key is not set (Settings → Integrations)")
            client = anthropic.Anthropic(api_key=key, max_retries=3, timeout=600)
        self.client = client

    @staticmethod
    def max_tokens(task: AgentTask[Any]) -> int:
        return min(64000, max(MIN_MAX_TOKENS, task.max_tokens * 4))

    def estimate_usd(self, task: AgentTask[Any], model: str) -> float:
        # Expect about twice the answer size in output once thinking is counted.
        return pricing.token_cost(
            model or DEFAULT_MODEL, estimate_input_tokens(task), task.max_tokens * 2
        )

    def request(
        self, task: AgentTask[Any], model: str, extra_user: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """The request body (pure; unit-tested)."""
        model = model or DEFAULT_MODEL
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_mime(img),
                    "data": base64.standard_b64encode(img).decode(),
                },
            }
            for img in task.images
        ]
        text = task.prompt + (f"\n\n{extra_user}" if extra_user else "")
        content.append({"type": "text", "text": text})
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens(task),
            "system": task.system,
            "messages": [{"role": "user", "content": content}],
            "output_config": {
                "effort": options.get("effort") or "medium",
                "format": {
                    "type": "json_schema",
                    "schema": anthropic.transform_schema(task.schema),
                },
            },
        }
        if model in FALLBACK_MODELS:
            body["betas"] = [FALLBACK_BETA]
            body["fallbacks"] = "default"
        return body

    def complete_json(
        self,
        task: AgentTask[Any],
        model: str,
        extra_user: str = "",
        options: dict[str, Any] | None = None,
    ) -> tuple[str, Usage]:
        body = self.request(task, model, extra_user, options or {})
        with self.client.beta.messages.stream(**body) as stream:
            msg = stream.get_final_message()
        text = "".join(b.text for b in msg.content if b.type == "text")
        u = msg.usage
        used_model = msg.model or body["model"]
        cost = pricing.token_cost(
            used_model,
            u.input_tokens,
            u.output_tokens,
            u.cache_read_input_tokens or 0,
            u.cache_creation_input_tokens or 0,
        )
        return text, Usage(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cost_usd=cost,
            stop=str(msg.stop_reason or ""),
            model=used_model,
        )
