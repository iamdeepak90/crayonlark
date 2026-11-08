"""Telegram bot (long-polling). Full approval flows arrive in Phase 2."""

from __future__ import annotations

import logging
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=_heartbeat, daemon=True).start()
    if not get_settings().telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN not set: bot idle")
        while True:
            time.sleep(3600)
    from crayonlark.bot.app import run

    run()


if __name__ == "__main__":
    main()
