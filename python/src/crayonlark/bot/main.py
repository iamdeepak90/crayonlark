"""Telegram bot (long-polling).

The token is set in admin → Settings → Integrations → Telegram. The bot waits until a token is
saved, and exits when it changes or is switched off; Docker restarts it with the new one.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from crayonlark.core.config import get_settings

HEARTBEAT = Path("/tmp/bot-heartbeat")
log = logging.getLogger("crayonlark.bot")


def _heartbeat() -> None:
    while True:
        HEARTBEAT.write_text(str(time.time()))
        time.sleep(30)


CHECK_SECONDS = 30


def _token() -> str:
    return get_settings().telegram_bot_token


def _exit_when_token_changes(token: str) -> None:
    while True:
        time.sleep(CHECK_SECONDS)
        if _token() != token:
            log.info("Telegram token changed in Settings: restarting the bot")
            os._exit(0)  # restart: unless-stopped brings us back with the new token


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=_heartbeat, daemon=True).start()
    token = _token()
    if not token:
        log.warning("Telegram is off (admin → Settings → Integrations): bot idle")
        while not (token := _token()):
            time.sleep(CHECK_SECONDS)
    threading.Thread(target=_exit_when_token_changes, args=(token,), daemon=True).start()
    from crayonlark.bot.app import run

    run()


if __name__ == "__main__":
    main()
