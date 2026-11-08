"""One interface for every LLM (Anthropic, OpenAI, Gemini, offline).

Agents describe *what* they need as an AgentTask (system + prompt + Pydantic schema + a free
offline fallback). `run_task()` picks the provider/model configured for that agent in
Settings → agent_models, wraps paid calls in the budget guard, validates the JSON against the
schema and retries once with the validation error if the model got it wrong.
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
        self, task: AgentTask[Any], model: str, extra_user: str = ""
    ) -> tuple[str, Usage]:
        """Return raw JSON text matching task.schema plus token usage/cost."""
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


def agent_config(agent: str) -> dict[str, str]:
    from crayonlark.core import app_settings

    models = app_settings.get("agent_models") or {}
    return dict(models.get(agent) or {"provider": "offline", "model": ""})


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
            raw, usage = provider.complete_json(task, model, extra)
            call.actual_usd = usage.cost_usd
            call.input_tokens, call.output_tokens = usage.input_tokens, usage.output_tokens
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
