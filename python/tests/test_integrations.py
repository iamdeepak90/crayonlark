from __future__ import annotations

import pytest

from crayonlark.core import integrations
from crayonlark.core.integrations import decrypt, encrypt, overrides

KEY = "k" * 64


def test_encrypt_roundtrip_and_wrong_key() -> None:
    token = encrypt("sk-secret", KEY)
    assert token.startswith("enc:") and "sk-secret" not in token
    assert decrypt(token, KEY) == "sk-secret"
    assert decrypt(token, "another-key") == ""  # SECRET_KEY changed → treated as not set


def test_overrides_enabled_disabled_and_types() -> None:
    stored = {
        "telegram": {
            "enabled": True,
            "values": {
                "telegram_bot_token": encrypt("123:abc", KEY),
                "telegram_admin_chat_id": "42",
            },
        },
        "etsy": {"enabled": True, "values": {"etsy_taxonomy_id": "1234", "etsy_shop_id": ""}},
        "email": {"enabled": False, "values": {"smtp_host": "smtp.example.com"}},
        "nope": {"enabled": True, "values": {"secret_key": "hijack"}},
    }
    out = overrides(stored, KEY)
    assert out["telegram_bot_token"] == "123:abc" and out["telegram_admin_chat_id"] == "42"
    assert out["etsy_taxonomy_id"] == 1234 and "etsy_shop_id" not in out
    assert out["smtp_host"] == "" and out["smtp_password"] == ""  # switched off
    assert "secret_key" not in out  # unknown groups/fields are ignored


def test_saved_in_settings_reaches_get_settings(db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.config import get_settings
    from crayonlark.core.models import AuditLog

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    get_settings.cache_clear()
    with db() as s:
        integrations.save_group(
            s,
            "telegram",
            True,
            {"telegram_bot_token": "123:abc", "telegram_admin_chat_id": "42"},
            "admin:me",
        )
    get_settings.cache_clear()
    assert get_settings().telegram_bot_token == "123:abc"
    with db() as s:
        # secret kept when not sent again; switching off hides it everywhere
        integrations.save_group(s, "telegram", False, {"telegram_admin_chat_id": "42"}, "admin:me")
        saved = integrations.load_stored(s)["telegram"]["values"]
        assert saved["telegram_bot_token"].startswith("enc:")
        logged = " ".join(str(a.details) for a in s.query(AuditLog))
    assert "123:abc" not in logged
    get_settings.cache_clear()
    assert get_settings().telegram_bot_token == ""
    with db() as s, pytest.raises(ValueError):
        integrations.save_group(s, "telegram", True, {"secret_key": "x"}, "admin:me")


def test_admin_api_never_returns_secrets(client) -> None:  # type: ignore[no-untyped-def]
    from tests.test_api_admin import H, login

    login(client)
    r = client.put(
        "/api/admin/integrations/ai",
        json={"enabled": True, "values": {"openrouter_api_key": "sk-or-very-secret"}},
        headers=H,
    )
    assert r.status_code == 200 and "sk-or-very-secret" not in r.text
    ai = next(g for g in r.json()["groups"] if g["id"] == "ai")
    field = next(f for f in ai["fields"] if f["name"] == "openrouter_api_key")
    assert field["set"] and "value" not in field
    apis = {a["id"]: a for a in client.get("/api/admin/paid-apis").json()["apis"]}
    assert apis["openrouter"]["key_set"]
    bad = client.put(
        "/api/admin/integrations/websearch",
        json={"enabled": True, "values": {"websearch_provider": "google"}},
        headers=H,
    )
    assert bad.status_code == 400
    client.put(
        "/api/admin/integrations/website",
        json={
            "enabled": True,
            "values": {"umami_url": "https://stats.example.com/", "turnstile_secret": "x"},
        },
        headers=H,
    )
    cfg = client.get("/api/public/site-config").json()
    assert cfg["umami_url"] == "https://stats.example.com" and "turnstile_secret" not in cfg


def test_empty_leftover_env_vars_use_defaults(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Coolify injects empty leftovers (MONTHLY_BUDGET_INR="" …); startup must not crash."""
    from crayonlark.core.config import Settings

    for name in (
        "MONTHLY_BUDGET_INR",
        "USD_INR_RATE",
        "SMTP_PORT",
        "ETSY_TAXONOMY_ID",
        "UPSCALE_ENABLED",
        "BACKUP_RETENTION_DAYS",
        "SMTP_FROM",
    ):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("KDP_WEEKLY_PAPERBACKS", "9")  # the hard rule can't be raised
    s = Settings()
    assert s.monthly_budget_inr == 2000 and s.smtp_port == 587 and s.etsy_taxonomy_id == 0
    assert not s.upscale_enabled and s.backup_retention_days == 14
    assert s.smtp_from.startswith("Crayonlark") and s.kdp_weekly_paperbacks == 2
