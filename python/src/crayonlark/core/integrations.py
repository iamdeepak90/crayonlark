"""Optional integrations (AI keys, Telegram, email, Etsy, Pinterest, off-site backup, website
extras) are set in admin → Settings → Integrations, not in Coolify.

Only the 7 infra secrets are env vars (see .env.example). Everything here is stored in the
`settings` table under the key "integrations":

    {"telegram": {"enabled": true, "values": {"telegram_bot_token": "enc:…", …}}, …}

- Secret fields are encrypted with a key derived from SECRET_KEY (Fernet) and are never sent
  back to the browser; the admin only sees "set" / "not set".
- Each group has an on/off switch. Off = the feature behaves as if nothing was entered.
- A non-empty env var with the same name still wins (handy for local development).

`overrides()` is merged into `config.get_settings()`, so the rest of the code just reads
`get_settings().telegram_bot_token` etc. as before.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

SETTING_KEY = "integrations"
ENC_PREFIX = "enc:"


@dataclass(frozen=True)
class Field:
    name: str  # attribute on config.Settings (env var = NAME.upper())
    label: str
    secret: bool = False
    placeholder: str = ""
    kind: str = "text"  # text | int | select
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class Group:
    id: str
    title: str
    help: str
    fields: tuple[Field, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "ai",
        "AI providers",
        "Keys for paid AI. Keys alone change nothing: choose the provider per agent in "
        "'AI providers & models'. Empty = free offline/manual mode.",
        (
            Field("anthropic_api_key", "Anthropic API key", True, "sk-ant-…"),
            Field("openai_api_key", "OpenAI API key", True, "sk-…"),
            Field("gemini_api_key", "Gemini API key", True),
            Field("openrouter_api_key", "OpenRouter API key", True, "sk-or-…"),
        ),
    ),
    Group(
        "websearch",
        "Web search (research agent)",
        "Optional search API for the research agent. Off = it uses your notes only.",
        (
            Field("websearch_provider", "Provider", kind="select", options=("tavily", "brave")),
            Field("websearch_api_key", "API key", True),
        ),
    ),
    Group(
        "telegram",
        "Telegram",
        "Approvals, alerts and the weekly report on your phone. Create a bot with @BotFather, "
        "send it /start to get your chat id. The bot picks up changes within a minute.",
        (
            Field("telegram_bot_token", "Bot token", True, "123456:ABC…"),
            Field("telegram_admin_chat_id", "Your chat id", placeholder="123456789"),
        ),
    ),
    Group(
        "email",
        "Email (SMTP, port 587)",
        "Free printables (double opt-in), contact form and weekly report. Any SMTP provider: "
        "Brevo, Resend, SES, Zoho…",
        (
            Field("smtp_host", "SMTP host", placeholder="smtp-relay.brevo.com"),
            Field("smtp_user", "SMTP user"),
            Field("smtp_password", "SMTP password", True),
            Field("smtp_from", "From", placeholder="Crayonlark <hello@crayonlark.com>"),
            Field("owner_email", "Your email (reports, contact messages)"),
        ),
    ),
    Group(
        "etsy",
        "Etsy",
        "Etsy Open API v3 app. Callback URL: https://admin.crayonlark.com/api/oauth/etsy/callback. "
        "Then connect the shop in Etsy & Pinterest.",
        (
            Field("etsy_api_key", "Keystring", True),
            Field("etsy_shared_secret", "Shared secret", True),
            Field("etsy_shop_id", "Shop id"),
            Field("etsy_taxonomy_id", "Taxonomy id", kind="int", placeholder="0"),
        ),
    ),
    Group(
        "pinterest",
        "Pinterest",
        "Pinterest API v5 app. Redirect URI: "
        "https://admin.crayonlark.com/api/oauth/pinterest/callback.",
        (
            Field("pinterest_app_id", "App id"),
            Field("pinterest_app_secret", "App secret", True),
        ),
    ),
    Group(
        "backup",
        "Off-site backup copy",
        "Copies the nightly backup to any S3-compatible storage (Backblaze B2, R2, Wasabi…). "
        "Off = backups stay on the server only.",
        (
            Field(
                "backup_s3_endpoint",
                "Endpoint",
                placeholder="https://s3.eu-central-003.backblazeb2.com",
            ),
            Field("backup_s3_region", "Region (if needed)"),
            Field("backup_s3_bucket", "Bucket"),
            Field("backup_s3_access_key", "Access key", True),
            Field("backup_s3_secret_key", "Secret key", True),
        ),
    ),
    Group(
        "website",
        "Website extras",
        "Amazon Associates tag on Amazon links, Cloudflare Turnstile on the contact form, Umami "
        "analytics. The website picks up changes within 5 minutes.",
        (
            Field("amazon_associates_tag", "Amazon Associates tag", placeholder="crayonlark-20"),
            Field("turnstile_site_key", "Turnstile site key"),
            Field("turnstile_secret", "Turnstile secret key", True),
            Field("umami_url", "Umami URL", placeholder="https://stats.crayonlark.com"),
            Field("umami_website_id", "Umami website id"),
        ),
    ),
)

GROUP_BY_ID = {g.id: g for g in GROUPS}
ALL_FIELDS = {f.name: f for g in GROUPS for f in g.fields}


# --------------------------------------------------------------------------- encryption


def _fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256(f"crayonlark-integrations:{secret_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str, secret_key: str) -> str:
    return ENC_PREFIX + _fernet(secret_key).encrypt(value.encode()).decode()


def decrypt(value: str, secret_key: str) -> str:
    if not value.startswith(ENC_PREFIX):
        return value
    try:
        return _fernet(secret_key).decrypt(value[len(ENC_PREFIX) :].encode()).decode()
    except InvalidToken:
        return ""  # SECRET_KEY changed: treat as not set; the admin shows it as "re-enter"


# --------------------------------------------------------------------------- read


def _coerce(field: Field, value: str) -> Any:
    if field.kind == "int":
        try:
            return int(value or 0)
        except ValueError:
            return 0
    return value


def overrides(stored: dict[str, Any] | None, secret_key: str) -> dict[str, Any]:
    """Settings attributes from the stored integrations. Pure; unit-tested.

    Enabled group → its non-empty values. Disabled group → every field blank (feature off).
    """
    out: dict[str, Any] = {}
    for gid, data in (stored or {}).items():
        group = GROUP_BY_ID.get(gid)
        if group is None or not isinstance(data, dict):
            continue
        values = data.get("values") or {}
        for f in group.fields:
            if not data.get("enabled"):
                out[f.name] = _coerce(f, "")
                continue
            raw = str(values.get(f.name) or "")
            value = decrypt(raw, secret_key) if f.secret else raw
            if value:
                out[f.name] = _coerce(f, value)
    return out


def load_stored(session: Session) -> dict[str, Any]:
    from crayonlark.core.models import Setting

    row = session.get(Setting, SETTING_KEY)
    return dict(row.value) if row is not None and isinstance(row.value, dict) else {}


def describe(session: Session) -> list[dict[str, Any]]:
    """For the admin page. Never contains secret values."""
    from crayonlark.core.config import env_settings

    env = env_settings()
    stored = load_stored(session)
    out = []
    for g in GROUPS:
        data = stored.get(g.id) or {}
        values = data.get("values") or {}
        fields = []
        for f in g.fields:
            raw = str(values.get(f.name) or "")
            item: dict[str, Any] = {
                "name": f.name,
                "label": f.label,
                "secret": f.secret,
                "placeholder": f.placeholder,
                "kind": f.kind,
                "options": list(f.options),
                "from_env": bool(getattr(env, f.name, "")),
            }
            if f.secret:
                item["set"] = bool(raw) and bool(decrypt(raw, env.secret_key))
                item["unreadable"] = bool(raw) and not item["set"]
            else:
                item["value"] = raw
                item["set"] = bool(raw)
            fields.append(item)
        out.append(
            {
                "id": g.id,
                "title": g.title,
                "help": g.help,
                "configured": g.id in stored,
                "enabled": bool(data.get("enabled")),
                "fields": fields,
            }
        )
    return out


# --------------------------------------------------------------------------- write


def save_group(
    session: Session,
    group_id: str,
    enabled: bool,
    values: dict[str, str | None],
    actor: str,
) -> None:
    """Update one group. For secrets: None/missing = keep, "" = clear, text = replace."""
    from crayonlark.core.audit import record
    from crayonlark.core.config import env_settings, get_settings
    from crayonlark.core.models import Setting

    group = GROUP_BY_ID.get(group_id)
    if group is None:
        raise ValueError(f"unknown integration {group_id!r}")
    unknown = set(values) - {f.name for f in group.fields}
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")

    secret_key = env_settings().secret_key
    row = session.get(Setting, SETTING_KEY)
    stored = load_stored(session)
    old = dict((stored.get(group_id) or {}).get("values") or {})
    new = dict(old)
    changed = []
    for f in group.fields:
        if f.name not in values or (f.secret and values[f.name] is None):
            continue
        value = (values[f.name] or "").strip()
        if f.kind == "int" and value and not value.isdigit():
            raise ValueError(f"{f.label} must be a number")
        if f.kind == "select" and value and value not in f.options:
            raise ValueError(f"{f.label} must be one of: {', '.join(f.options)}")
        stored_value = encrypt(value, secret_key) if (f.secret and value) else value
        was = old.get(f.name, "")
        if (f.secret and (value or was)) or (not f.secret and was != value):
            changed.append(f.name)
        new[f.name] = stored_value
    stored[group_id] = {"enabled": bool(enabled), "values": new}

    if row is None:
        session.add(Setting(key=SETTING_KEY, value=stored, updated_by=actor))
    else:
        row.value = stored
        row.updated_by = actor
    # audit without values: secrets must never land in the audit log
    record(
        session,
        actor,
        "integrations.update",
        "setting",
        group_id,
        {"enabled": bool(enabled), "changed": changed},
    )
    session.flush()
    get_settings.cache_clear()  # this process sees it now; others within a minute


def public_site_config() -> dict[str, str]:
    """Non-secret values the public website needs at runtime."""
    from crayonlark.core.config import get_settings

    s = get_settings()
    return {
        "amazon_associates_tag": s.amazon_associates_tag,
        "turnstile_site_key": s.turnstile_site_key,
        "umami_url": s.umami_url.rstrip("/"),
        "umami_website_id": s.umami_website_id,
    }
