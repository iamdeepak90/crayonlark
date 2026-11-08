"""Outgoing Telegram Bot API calls (used by workers/API). The `bot` service handles replies."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from crayonlark.core.config import get_settings

log = logging.getLogger("crayonlark.telegram")
Buttons = list[list[tuple[str, str]]]  # rows of (label, callback_data)


def enabled() -> bool:
    s = get_settings()
    return bool(s.telegram_bot_token and s.telegram_admin_chat_id)


def _markup(buttons: Buttons | None) -> str | None:
    if not buttons:
        return None
    return json.dumps(
        {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in buttons]}
    )


def call(method: str, data: dict[str, Any], files: dict[str, Any] | None = None) -> dict:
    s = get_settings()
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/{method}"
    for attempt in range(4):
        r = httpx.post(url, data=data, files=files, timeout=30)
        if r.status_code == 429:  # flood control
            wait = r.json().get("parameters", {}).get("retry_after", 2 + attempt * 2)
            time.sleep(float(wait))
            continue
        r.raise_for_status()
        out: dict = r.json()
        return out
    raise RuntimeError(f"telegram {method}: rate limited")


def send_message(text: str, buttons: Buttons | None = None) -> None:
    if not enabled():
        log.info("[telegram disabled] %s", text)
        return
    data = {
        "chat_id": get_settings().telegram_admin_chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }
    if m := _markup(buttons):
        data["reply_markup"] = m
    call("sendMessage", data)


def send_photo(
    photo: bytes, caption: str, buttons: Buttons | None = None, filename: str = "image.jpg"
) -> None:
    if not enabled():
        log.info("[telegram disabled] photo: %s", caption)
        return
    data = {"chat_id": get_settings().telegram_admin_chat_id, "caption": caption[:1000]}
    if m := _markup(buttons):
        data["reply_markup"] = m
    call("sendPhoto", data, files={"photo": (filename, photo)})


def send_album(photos: list[tuple[bytes, str]]) -> None:
    """Up to 10 photos per album (Telegram limit); captions per photo."""
    if not enabled():
        return
    for start in range(0, len(photos), 10):
        chunk = photos[start : start + 10]
        media = [
            {"type": "photo", "media": f"attach://p{i}", "caption": cap[:200]}
            for i, (_, cap) in enumerate(chunk)
        ]
        files = {f"p{i}": (f"p{i}.jpg", data) for i, (data, _) in enumerate(chunk)}
        call(
            "sendMediaGroup",
            {"chat_id": get_settings().telegram_admin_chat_id, "media": json.dumps(media)},
            files=files,
        )
        time.sleep(1)
