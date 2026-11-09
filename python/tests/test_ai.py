"""Phase 6: providers (mocked HTTP / fake SDK client), schemas, costs, agents and the pipeline."""

from __future__ import annotations

import base64
import io
import json
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx
from PIL import Image as PILImage
from pydantic import BaseModel, Field

from crayonlark.core.config import get_settings
from crayonlark.providers import ProviderBusy, pricing
from crayonlark.providers.llm.base import AgentTask, portable_schema


class Pet(BaseModel):
    name: str = Field(max_length=20)
    legs: int = Field(ge=0, le=8)
    tags: list[str] = Field(default_factory=list, max_length=3)


class Owner(BaseModel):
    title: str  # a field literally named "title" must survive the schema clean-up
    pets: list[Pet]


def _task(images: list[bytes] | None = None) -> AgentTask[Owner]:
    return AgentTask(
        agent="concept",
        system="sys",
        prompt="make one",
        schema=Owner,
        offline=lambda: Owner(title="x", pets=[]),
        images=images or [],
        max_tokens=1000,
    )


def _png() -> bytes:
    buf = io.BytesIO()
    PILImage.new("L", (8, 8), 255).save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- schema + pricing


def test_portable_schema_is_strict_everywhere() -> None:
    sch = portable_schema(Owner)
    assert "title" in sch["properties"] and sch["required"] == ["title", "pets"]
    assert sch["additionalProperties"] is False
    pet = sch["$defs"]["Pet"]
    assert pet["additionalProperties"] is False and pet["required"] == ["name", "legs", "tags"]
    text = json.dumps(sch)
    assert "maxLength" not in text and '"default"' not in text


def test_token_and_image_costs() -> None:
    assert pricing.token_cost("claude-opus-5-5", 1_000_000, 0) == pytest.approx(4.0)
    assert pricing.token_cost("claude-haiku-5-5", 0, 1_000_000) == pytest.approx(0.5)
    # unknown models are priced high on purpose
    assert pricing.token_price("mystery-model") == pricing.UNKNOWN_TOKEN_PRICE
    assert pricing.image_token_cost("gpt-image-2.5-flare", 100, 1000) == pytest.approx(0.0305)


# --------------------------------------------------------------------------- Anthropic


class FakeStream:
    def __init__(self, msg: Any) -> None:
        self.msg = msg

    def get_final_message(self) -> Any:
        return self.msg


def fake_anthropic(text: str, stop: str = "end_turn", model: str = "claude-opus-5-5") -> Any:
    calls: list[dict[str, Any]] = []
    msg = SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=2000,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        ),
        model=model,
        stop_reason=stop,
    )

    @contextmanager
    def stream(**kw: Any) -> Any:
        calls.append(kw)
        yield FakeStream(msg)

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    return client, calls


def test_anthropic_request_and_cost() -> None:
    from crayonlark.providers.llm.anthropic_provider import AnthropicProvider

    client, calls = fake_anthropic('{"title": "t", "pets": []}')
    p = AnthropicProvider(client=client)
    text, usage = p.complete_json(_task([_png()]), "claude-opus-5-5", "", {"effort": "low"})
    body = calls[0]
    assert body["model"] == "claude-opus-5-5"
    assert body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["fallbacks"] == "default" and body["betas"] == ["server-side-fallback-2026-07-01"]
    assert body["max_tokens"] >= 16000
    blocks = body["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/png"
    assert "temperature" not in body
    assert json.loads(text)["title"] == "t"
    assert usage.cost_usd == pytest.approx((1000 * 4 + 2000 * 20) / 1e6)


def test_anthropic_haiku_has_no_fallbacks_and_fallback_model_is_priced() -> None:
    from crayonlark.providers.llm.anthropic_provider import AnthropicProvider

    client, calls = fake_anthropic("{}", model="claude-opus-4-8")
    _, usage = AnthropicProvider(client=client).complete_json(_task(), "claude-haiku-5-5")
    assert "fallbacks" not in calls[0]
    assert usage.model == "claude-opus-4-8"  # priced as the model that answered (unknown → high)
    assert usage.cost_usd == pytest.approx((1000 * 10 + 2000 * 50) / 1e6)


# --------------------------------------------------------------------------- OpenAI + Gemini


@respx.mock
def test_openai_responses_shape_and_usage(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.llm.openai_provider import OpenAIProvider

    route = respx.post("https://api.openai.com/v1/responses").respond(
        200,
        json={
            "model": "gpt-6-luna",
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"title":"a","pets":[]}'}],
                },
            ],
            "usage": {
                "input_tokens": 1000,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 500,
            },
        },
    )
    text, usage = OpenAIProvider().complete_json(_task([_png()]), "gpt-6-luna")
    sent = json.loads(route.calls[0].request.content)
    assert route.calls[0].request.headers["authorization"] == "Bearer test-key"
    assert sent["text"]["format"]["strict"] is True
    assert sent["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
    assert sent["instructions"] == "sys"
    assert json.loads(text)["title"] == "a"
    assert usage.cost_usd == pytest.approx((1000 * 0.10 + 500 * 0.50) / 1e6)


@respx.mock
def test_openai_refusal_and_busy(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.llm.openai_provider import OpenAIProvider

    respx.post("https://api.openai.com/v1/responses").mock(
        side_effect=[
            httpx.Response(429, text="slow down"),
            httpx.Response(
                200,
                json={"output": [{"type": "message", "content": [{"type": "refusal"}]}]},
            ),
        ]
    )
    with pytest.raises(ProviderBusy):
        OpenAIProvider().complete_json(_task(), "gpt-6-luna")
    _, usage = OpenAIProvider().complete_json(_task(), "gpt-6-luna")
    assert usage.stop == "refusal"


@respx.mock
def test_gemini_shape_counts_thinking_tokens(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.llm.gemini_provider import GeminiProvider

    route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
    ).respond(
        200,
        json={
            "candidates": [
                {
                    "content": {"parts": [{"text": "thinking...", "thought": True},
                                          {"text": '{"title":"g","pets":[]}'}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 1000,
                "candidatesTokenCount": 100,
                "thoughtsTokenCount": 400,
            },
        },
    )  # fmt: skip
    text, usage = GeminiProvider().complete_json(_task([_png()]), "")
    req = route.calls[0].request
    sent = json.loads(req.content)
    assert req.headers["x-goog-api-key"] == "test-key"
    assert sent["generationConfig"]["responseMimeType"] == "application/json"
    assert sent["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/png"
    assert json.loads(text)["title"] == "g"
    assert usage.output_tokens == 500
    assert usage.cost_usd == pytest.approx((1000 * 1.5 + 500 * 7.5) / 1e6)


@respx.mock
def test_image_providers(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.image.gemini_image import GeminiImageProvider
    from crayonlark.providers.image.openai_image import OpenAIImageProvider

    b64 = base64.b64encode(_png()).decode()
    o = respx.post("https://api.openai.com/v1/images/generations").respond(
        200,
        json={"data": [{"b64_json": b64}], "usage": {"input_tokens": 100, "output_tokens": 1000}},
    )
    res = OpenAIImageProvider().generate("a cat", "")
    sent = json.loads(o.calls[0].request.content)
    assert sent["size"] == "1024x1536" and sent["n"] == 1 and sent["model"] == "gpt-image-2.5-flare"
    assert res.data == _png() and res.cost_usd == pytest.approx(0.0305)

    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-nano-banana-2.1:generateContent"
    ).respond(
        200,
        json={
            "candidates": [
                {"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": b64}}]}}
            ],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 1120},
        },
    )  # fmt: skip
    g = GeminiImageProvider().generate("a cat", "")
    assert g.data == _png() and g.cost_usd == pytest.approx((20 * 0.5 + 1120 * 30) / 1e6)


# --------------------------------------------------------------------------- web search


@respx.mock
def test_websearch_excludes_amazon_and_etsy(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.integrations import websearch

    monkeypatch.setenv("WEBSEARCH_PROVIDER", "brave")
    monkeypatch.setenv("WEBSEARCH_API_KEY", "k")
    get_settings.cache_clear()
    route = respx.get("https://api.search.brave.com/res/v1/web/search").respond(
        200,
        json={
            "web": {
                "results": [
                    {"title": "A", "url": "https://www.amazon.com/x", "description": "no"},
                    {"title": "B", "url": "https://www.etsy.com/listing/1", "description": "no"},
                    {"title": "C", "url": "https://blog.example.org/ocean", "description": "yes"},
                ]
            }
        },
    )
    rows = websearch.search("ocean coloring")
    get_settings.cache_clear()
    assert [r["title"] for r in rows] == ["C"]
    assert route.calls[0].request.headers["x-subscription-token"] == "k"
    from crayonlark.core import budget

    with db() as s:
        assert budget.spent_usd(s, budget.month_key()) == pytest.approx(0.005)


# --------------------------------------------------------------------------- run_task + budget


class FakeLLM:
    name = "anthropic"

    def __init__(self, answers: list[str], stop: str = "end_turn") -> None:
        self.answers, self.stop, self.prompts = answers, stop, []

    def estimate_usd(self, task: Any, model: str) -> float:
        return 0.01

    def complete_json(self, task, model, extra_user="", options=None):  # type: ignore[no-untyped-def]
        from crayonlark.providers.llm.base import Usage

        self.prompts.append(extra_user)
        return self.answers.pop(0), Usage(10, 20, 0.002, self.stop, "claude-sonnet-5-5")


def _use(monkeypatch: pytest.MonkeyPatch, fake: FakeLLM) -> None:
    from crayonlark.core import app_settings
    from crayonlark.providers.llm import registry

    monkeypatch.setattr(registry, "get_provider", lambda name: fake)
    real_get = app_settings.get
    monkeypatch.setattr(
        app_settings,
        "get",
        lambda key, session=None: (
            {"concept": {"provider": "anthropic", "model": "claude-opus-5-5"}}
            if key == "agent_models"
            else real_get(key, session)
        ),
    )


def test_run_task_repairs_invalid_json_and_records_cost(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import budget
    from crayonlark.core.models import ApiCost
    from crayonlark.providers.llm.base import run_task

    fake = FakeLLM(['{"title": 1}', '{"title": "ok", "pets": []}'])
    _use(monkeypatch, fake)
    out = run_task(_task())
    assert out.title == "ok"
    assert "invalid" in fake.prompts[1]
    with db() as s:
        rows = list(s.query(ApiCost))
        assert len(rows) == 2 and all(r.status == "committed" for r in rows)
        assert {r.model for r in rows} == {"claude-sonnet-5-5"}  # the model that answered
        assert budget.spent_usd(s, budget.month_key()) == pytest.approx(0.004)


def test_refusal_is_charged_and_not_retried(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.models import ApiCost
    from crayonlark.providers.llm.base import LLMRefused, run_task

    fake = FakeLLM(["", ""], stop="refusal")
    _use(monkeypatch, fake)
    with pytest.raises(LLMRefused):
        run_task(_task())
    with db() as s:
        assert s.query(ApiCost).count() == 1


# --------------------------------------------------------------------------- agents (offline)


def test_research_offline_and_blocklist(db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.agents import research
    from crayonlark.core import generation
    from crayonlark.core.blocklist import BlockedContent

    out = research.offline("dinosaurs")
    out.ideas[0].name = "Peppa Pig Dinosaurs"  # must be dropped
    with db() as s:
        saved, dropped = research.save_ideas(s, "dinosaurs", out)
        assert len(saved) == 9 and dropped == ["Peppa Pig Dinosaurs"]
        assert all(n.status == "proposed" and n.source == "research_agent" for n in saved)
        with pytest.raises(BlockedContent):
            generation.run_research(s, "Bluey adventures")


def test_concepts_offline_make_pending_images(db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.agents import concept
    from crayonlark.core import generation, pipeline
    from crayonlark.core.actors import SYSTEM
    from crayonlark.core.enums import BookStatus, ImageStatus
    from crayonlark.core.state_machine import transition

    with db() as s:
        book = pipeline.create_book(s, "Farm Friends", SYSTEM, themes=["farm animal"])
        from crayonlark.core.actors import HumanActor

        transition(s, book, BookStatus.NICHE_APPROVED, HumanActor.from_cli("test"))
        res = generation.make_concepts(s, book)
        assert res["saved"] == 60
        assert book.status == BookStatus.CONCEPTS_READY
        imgs = generation.pending_concepts(book)
        assert len(imgs) == 60 and all(i.status == ImageStatus.PENDING for i in imgs)
        assert "Thick bold black outlines" in imgs[0].prompt
        assert len({i.prompt for i in imgs}) == 60
        # re-running replaces unused concepts instead of piling them up
        out = concept.ConceptOut(
            scenes=[concept.Scene(title=f"S{i}", scene=f"a cow number {i}") for i in range(10)]
            + [concept.Scene(title="Bad", scene="Mickey Mouse on a farm")]
        )
        saved, dropped = concept.save_concepts(s, book, out)
        s.expire(book, ["images"])
        assert saved == 10 and dropped == ["Bad"] and len(book.images) == 10


def test_vision_scores_merge() -> None:
    from crayonlark.agents.vision_qa import VisionQAOut, to_scores

    ok = VisionQAOut(
        matches_scene=True, anatomy_ok=True, scary=False, has_text=False, lookalike="",
        age_ok=True, line_art_ok=True, score=0.9, recommendation="keep",
    )  # fmt: skip
    assert to_scores(ok)["recommendation"] == "keep"
    bad = ok.model_copy(update={"lookalike": "a famous mouse"})
    s = to_scores(bad)
    assert s["recommendation"] == "reject" and s["flags"] == ["looks like a famous mouse"]
