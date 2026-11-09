"""All configuration comes from environment variables (set in Coolify).

Only `.env.example` is committed. Anything editable at runtime (models per agent,
blocklist, prompt templates) lives in the `settings` table instead, see core/app_settings.py.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    kdp_weekly_paperbacks: int = 2
    kdp_weekly_hardcovers: int = 2
    spine_text_min_pages: int = 100
    default_kdp_price_usd: float = 9.99

    # --- providers (all optional) ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
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
    turnstile_secret: str = ""

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
def get_settings() -> Settings:
    return Settings()
