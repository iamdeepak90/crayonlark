"""Configuration.

Infra and the 7 required secrets come from environment variables (set in Coolify; only
`.env.example` is committed). Optional integrations (AI keys, Telegram, email, Etsy, Pinterest,
off-site backup, website extras) are entered in admin → Settings → Integrations and merged in
by `get_settings()`, see core/integrations.py. Other runtime knobs (models per agent,
blocklist, prompt templates, budget) live in the `settings` table, see core/app_settings.py.
"""

from __future__ import annotations

import logging
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"


class Settings(BaseSettings):
    # Coolify passes every variable it has stored into each container, including empty leftovers
    # from older deploys: an empty value means "not set" and the default below applies.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    # --- general ---
    environment: str = "development"  # development | production | test
    secret_key: str = "dev-insecure-change-me"
    public_site_url: str = "http://localhost:3000"
    admin_site_url: str = "http://admin.localhost:3000"
    timezone: str = "UTC"

    # --- infra ---
    database_url: str = "postgresql+psycopg://crayonlark:crayonlark@localhost:5432/crayonlark"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:3900"
    s3_region: str = "garage"
    s3_access_key: str = "GK000000000000000000000000"
    s3_secret_key: str = "0" * 64
    s3_public_base_url: str = ""  # optional CDN/public URL for the public-assets bucket
    garage_admin_url: str = "http://localhost:3903"
    garage_admin_token: str = ""

    # --- budget: starting values only; the owner edits them in admin → Settings → Budget ---
    monthly_budget_inr: float = 2000.0
    usd_inr_rate: float = 88.0
    budget_warn_ratio: float = 0.8

    # --- KDP ---
    # Hard rule (CLAUDE.md): not configurable, so a stray env var can never raise it.
    kdp_weekly_paperbacks: ClassVar[int] = 2
    kdp_weekly_hardcovers: ClassVar[int] = 2
    spine_text_min_pages: int = 100
    default_kdp_price_usd: float = 9.99

    # --- providers (all optional) ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""  # one key, many models (Claude, GPT, Gemini, …) via openrouter.ai
    websearch_provider: str = ""  # "tavily" | "brave" | ""
    websearch_api_key: str = ""

    # --- telegram ---
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    # --- email (generic SMTP) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Crayonlark <hello@crayonlark.com>"
    smtp_starttls: bool = True
    owner_email: str = ""

    # --- etsy / pinterest ---
    etsy_api_key: str = ""  # Etsy "keystring"
    etsy_shared_secret: str = ""
    etsy_shop_id: str = ""
    etsy_taxonomy_id: int = 0
    etsy_when_made: str = "2020_2026"
    pinterest_app_id: str = ""
    pinterest_app_secret: str = ""
    pinterest_pins_per_day: int = 4

    # --- website ---
    revalidate_secret: str = "dev-revalidate"
    web_internal_url: str = "http://web:3000"  # API → web on-demand revalidation
    amazon_associates_tag: str = ""
    turnstile_site_key: str = ""
    turnstile_secret: str = ""
    umami_url: str = ""
    umami_website_id: str = ""

    # --- worker ---
    upscale_enabled: bool = False
    upscale_window_utc: str = "01:00-05:00"
    backup_dir: str = "/backups"
    backup_retention_days: int = 14
    # optional off-site copy to any S3-compatible storage (B2, R2, Wasabi, ...)
    backup_s3_endpoint: str = ""
    backup_s3_region: str = ""
    backup_s3_bucket: str = ""
    backup_s3_access_key: str = ""
    backup_s3_secret_key: str = ""

    # --- derived ---
    buckets: dict[str, str] = Field(
        default_factory=lambda: {
            "originals": "originals",
            "processed": "processed",
            "outputs": "outputs",
            "public": "public-assets",
            "inbox": "inbox",
        }
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def env_settings() -> Settings:
    """Settings from env vars only (infra; used to reach the database itself)."""
    return Settings()


log = logging.getLogger("crayonlark.config")


class _SettingsWithIntegrations:
    """`get_settings()`: env settings + integrations saved in admin → Settings.

    The stored integrations are re-read at most every TTL seconds per process, so a change in
    the admin reaches workers, the bot and the scheduler within a minute. If the database is
    not reachable (tests, first boot) the env settings are used as they are.
    """

    TTL = 30.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cached: Settings | None = None
        self._at = 0.0
        self._loading = False

    def __call__(self) -> Settings:
        base = env_settings()
        now = time.monotonic()
        with self._lock:
            if self._cached is not None and now - self._at < self.TTL:
                return self._cached
            if self._loading:  # opening the DB session itself asked for settings
                return self._cached or base
            self._loading = True
        try:
            merged = self._merge(base)
        finally:
            with self._lock:
                self._loading = False
        with self._lock:
            self._cached, self._at = merged, time.monotonic()
        return merged

    @staticmethod
    def _merge(base: Settings) -> Settings:
        try:
            from crayonlark.core import integrations
            from crayonlark.core.db import session_scope

            with session_scope() as s:
                stored = integrations.load_stored(s)
        except Exception as exc:  # DB down / table missing: env only
            log.debug("integrations not loaded: %s", exc)
            return base
        over: dict[str, Any] = {
            k: v
            for k, v in integrations.overrides(stored, base.secret_key).items()
            if not getattr(base, k, None)  # a non-empty env var wins
        }
        return base.model_copy(update=over) if over else base

    def cache_clear(self) -> None:
        env_settings.cache_clear()
        with self._lock:
            self._cached, self._at = None, 0.0


get_settings = _SettingsWithIntegrations()
