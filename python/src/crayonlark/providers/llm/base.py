"""One interface for every LLM (Anthropic, OpenAI, Gemini, OpenRouter, offline).

Agents describe *what* they need as an AgentTask (system + prompt + Pydantic schema + a free
offline fallback). `run_task()` picks the provider/model for that agent (fixed in code:
AUTO_MODELS through OpenRouter once its key is set, else the free offline templates), wraps paid
calls in the budget guard, validates the JSON against the schema and retries once with the
validation error if the model got it wrong.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

log = logging.getLogger("crayonlark.llm")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    stop: str = ""  # provider stop reason; "refusal" means the model declined
    model: str = ""  # the model that actually answered (may differ after a fallback)


class LLMRefused(RuntimeError):
    """The model declined the request (safety refusal). Not retried."""


IMAGE_TOKENS = 1600  # rough input tokens per attached image, for estimates


@dataclass
class AgentTask[T: BaseModel]:
    agent: str
    system: str
    prompt: str
    schema: type[T]
    offline: Callable[[], T]
    images: list[bytes] = field(default_factory=list)  # PNG/JPEG for vision tasks
    max_tokens: int = 4000
    book_id: int | None = None
    estimate_usd: float | None = None  # override the budget reservation estimate


class LLMProvider(Protocol):
    name: str

    def complete_json(
        self,
        task: AgentTask[Any],
        model: str,
        extra_user: str = "",
        options: dict[str, Any] | None = None,
    ) -> tuple[str, Usage]:
        """Return raw JSON text matching task.schema plus token usage/cost.
        `options` is the agent's settings entry (e.g. {"effort": "medium"})."""
        ...

    def estimate_usd(self, task: AgentTask[Any], model: str) -> float: ...


def schema_hint(schema: type[BaseModel]) -> str:
    return json.dumps(schema.model_json_schema(), separators=(",", ":"))


def parse_json(text: str) -> Any:
    """Tolerate ```json fences and leading prose."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    start = min((i for i in (t.find("{"), t.find("[")) if i >= 0), default=0)
    return json.loads(t[start:])


def estimate_input_tokens(task: AgentTask[Any], extra_user: str = "") -> int:
    from crayonlark.providers.pricing import estimate_tokens

    text = task.system + task.prompt + extra_user + schema_hint(task.schema)
    return estimate_tokens(text) + IMAGE_TOKENS * len(task.images)


def image_mime(data: bytes) -> str:
    return "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"


# One OpenRouter key runs every agent. Haiku is cheap and good at JSON and pictures; the listing
# (the text buyers read) gets Sonnet. About ₹1–3 per book in total (docs/DECISIONS.md 76–77).
AUTO_DEFAULT_MODEL = "anthropic/claude-haiku-5.5"
AUTO_MODELS = {"listing": "anthropic/claude-sonnet-5.5"}


def agent_config(agent: str) -> dict[str, str]:
    from crayonlark.core import app_settings
    from crayonlark.core.config import get_settings

    stored = (app_settings.get("agent_models") or {}).get(agent)
    if stored:  # not shown in admin any more; kept for tests and emergencies
        return dict(stored)
    if get_settings().openrouter_api_key:
        return {"provider": "openrouter", "model": AUTO_MODELS.get(agent, AUTO_DEFAULT_MODEL)}
    return {"provider": "offline", "model": ""}


def run_task[T: BaseModel](task: AgentTask[T]) -> T:
    from crayonlark.core import budget
    from crayonlark.providers.llm.registry import get_provider

    cfg = agent_config(task.agent)
    provider_name = cfg.get("provider", "offline")
    if provider_name == "offline":
        return task.offline()
    provider = get_provider(provider_name)
    model = cfg.get("model") or ""
    extra = ""
    last_error: Exception | None = None
    for _attempt in range(2):  # one repair attempt on invalid JSON
        estimate = task.estimate_usd or provider.estimate_usd(task, model)
        with budget.paid_call(
            provider_name,
            model,
            task.agent,
            "vision" if task.images else "llm",
            estimate,
            book_id=task.book_id,
        ) as call:
            raw, usage = provider.complete_json(task, model, extra, cfg)
            call.actual_usd = usage.cost_usd
            call.input_tokens, call.output_tokens = usage.input_tokens, usage.output_tokens
            call.model = usage.model or None
        if usage.stop == "refusal":
            raise LLMRefused(f"{task.agent}: {provider_name}/{model} declined the request")
        try:
            return task.schema.model_validate(parse_json(raw))
        except (ValidationError, ValueError) as exc:
            last_error = exc
            log.warning("%s: invalid JSON from %s/%s: %s", task.agent, provider_name, model, exc)
            extra = (
                f"Your previous answer was invalid: {str(exc)[:1500]}\n"
                "Reply again with ONLY valid JSON matching the schema."
            )
    raise ValueError(f"{task.agent}: model returned invalid output twice: {last_error}")


DROP_KEYWORDS = {"minLength", "maxLength", "default", "title", "uniqueItems"}


def portable_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """A JSON schema that OpenAI strict mode and Gemini both accept: every object has
    additionalProperties=false and lists all its properties as required; string-length and
    default keywords are dropped (Pydantic still enforces them after the call)."""

    def fix(node: Any) -> Any:
        if isinstance(node, list):
            return [fix(n) for n in node]
        if not isinstance(node, dict):
            return node
        out = {k: fix(v) for k, v in node.items() if k not in DROP_KEYWORDS}
        for mapping in ("properties", "$defs"):  # name → schema maps: recurse into values only
            if mapping in node:
                out[mapping] = {k: fix(v) for k, v in node[mapping].items()}
        if out.get("type") == "object" or "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out.get("properties", {}))
        return out

    result: dict[str, Any] = fix(schema.model_json_schema())
    return result
