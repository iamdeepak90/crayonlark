"""OpenRouter: chat completions with JSON schema, live model list + prices, image API."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from crayonlark.providers import ProviderBusy, openrouter
from tests.test_ai import _png, _task
from tests.test_api_admin import H, login

MODELS = {
    "data": [
        {
            "id": "anthropic/claude-haiku-5.5",
            "name": "Claude Haiku 5.5",
            "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
            "architecture": {"input_modalities": ["text", "image"]},
            "supported_parameters": ["max_tokens", "response_format", "structured_outputs"],
        },
        {
            "id": "some/no-json-model",
            "pricing": {"prompt": "0", "completion": "0"},
            "supported_parameters": ["max_tokens"],
        },
    ]
}


@pytest.fixture(autouse=True)
def _fresh_cache():  # type: ignore[no-untyped-def]
    openrouter._cache.clear()
    yield
    openrouter._cache.clear()


def test_text_models_keep_only_json_capable_and_price_per_million() -> None:
    models = openrouter.parse_text_models(MODELS)
    assert [m["id"] for m in models] == ["anthropic/claude-haiku-5.5"]
    m = models[0]
    assert (m["input_per_m"], m["output_per_m"], m["vision"]) == (0.1, 0.5, True)


@respx.mock
def test_chat_request_shape_cost_and_attribution(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.llm.openrouter_provider import OpenRouterProvider

    route = respx.post("https://openrouter.ai/api/v1/chat/completions").respond(
        200,
        json={
            "model": "anthropic/claude-haiku-5.5",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": '{"title":"a","pets":[]}'},
                }
            ],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "cost": 0.0123},
        },
    )
    text, usage = OpenRouterProvider().complete_json(
        _task([_png()]), "anthropic/claude-haiku-5.5", options={"effort": "low"}
    )
    req = route.calls[0].request
    sent = json.loads(req.content)
    assert req.headers["authorization"] == "Bearer test-key"
    assert req.headers["x-openrouter-title"] == "Crayonlark"
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert sent["provider"] == {"require_parameters": True}
    assert sent["reasoning"] == {"effort": "low"}
    assert sent["messages"][0] == {"role": "system", "content": "sys"}
    img = sent["messages"][1]["content"][1]
    assert img["image_url"]["url"].startswith("data:image/png;base64,")
    assert json.loads(text)["title"] == "a"
    assert usage.cost_usd == pytest.approx(0.0123)  # the real cost OpenRouter reports
    assert usage.model == "anthropic/claude-haiku-5.5"


@respx.mock
def test_chat_without_cost_uses_live_prices_and_errors(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.llm.openrouter_provider import OpenRouterProvider

    respx.get("https://openrouter.ai/api/v1/models").respond(200, json=MODELS)
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
                },
            ),
            httpx.Response(429, text="slow down"),
            # errors can also arrive with HTTP 200
            httpx.Response(200, json={"error": {"code": 402, "message": "insufficient credits"}}),
            httpx.Response(
                200,
                json={"choices": [{"finish_reason": "content_filter", "message": {"content": ""}}]},
            ),
        ]
    )
    p = OpenRouterProvider()
    sent_model = "anthropic/claude-haiku-5.5"
    _, usage = p.complete_json(_task(), sent_model)
    assert usage.cost_usd == pytest.approx((1000 * 0.1 + 500 * 0.5) / 1e6)
    with pytest.raises(ProviderBusy):
        p.complete_json(_task(), sent_model)
    with pytest.raises(RuntimeError, match="insufficient credits"):
        p.complete_json(_task(), sent_model)
    _, usage = p.complete_json(_task(), sent_model)
    assert usage.stop == "refusal"
    with pytest.raises(RuntimeError, match="pick an OpenRouter model"):
        p.complete_json(_task(), "")


@respx.mock
def test_openrouter_image(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.image.base import get_image_provider

    b64 = base64.b64encode(_png()).decode()
    route = respx.post("https://openrouter.ai/api/v1/images").respond(
        200, json={"data": [{"b64_json": b64, "media_type": "image/png"}], "usage": {"cost": 0.04}}
    )
    res = get_image_provider("openrouter").generate("a cat", "google/gemini-2.5-flash-image")
    sent = json.loads(route.calls[0].request.content)
    assert sent["aspect_ratio"] == "3:4" and sent["n"] == 1
    assert res.data == _png() and res.cost_usd == pytest.approx(0.04)


def test_settings_save_requires_openrouter_model(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.config import get_settings

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    get_settings.cache_clear()
    login(client)
    body = {
        "agent_models": {"listing": {"provider": "openrouter", "model": ""}},
        "image_provider": "manual",
    }
    assert client.put("/api/admin/ai/providers", json=body, headers=H).status_code == 400
    body["agent_models"]["listing"]["model"] = "anthropic/claude-haiku-5.5"  # type: ignore[index]
    assert client.put("/api/admin/ai/providers", json=body, headers=H).status_code == 200
    keys_shown = client.get("/api/admin/ai/providers").json()["keys"]
    assert keys_shown["openrouter"] is True
    get_settings.cache_clear()
