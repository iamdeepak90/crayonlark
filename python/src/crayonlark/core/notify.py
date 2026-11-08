"""Notifications to me: Telegram (if configured) + always the log. Never raises."""

from __future__ import annotations

import logging

import httpx

from crayonlark.core.config import get_settings

log = logging.getLogger("crayonlark.notify")


def notify(text: str, kind: str = "info", book_id: int | None = None) -> bool:
    log.info("[notify:%s] %s", kind, text)
    s = get_settings()
    if not (s.telegram_bot_token and s.telegram_admin_chat_id):
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
            json={
                "chat_id": s.telegram_admin_chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        return r.status_code == 200
    except httpx.HTTPError as exc:
        log.warning("telegram notify failed: %s", exc)
        return False
