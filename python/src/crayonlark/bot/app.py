"""Telegram bot handlers (python-telegram-bot, long-polling).

Commands: /start (shows your chat id), /status, /help.
Inline buttons from notifications call core/telegram_actions.handle_callback.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from crayonlark.core import telegram_actions
from crayonlark.core.config import get_settings

log = logging.getLogger("crayonlark.bot")


def _is_admin(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and str(chat.id) == str(get_settings().telegram_admin_chat_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    if _is_admin(update):
        await update.message.reply_text("Hi! Crayonlark bot is connected. Try /status.")
    else:
        await update.message.reply_text(
            f"Your chat id is {chat.id}. Enter it in admin → Settings → Telegram."
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update) or update.message is None:
        return
    text = await asyncio.to_thread(telegram_actions.status_text)
    await update.message.reply_text(text)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None or q.data is None:
        return
    if not _is_admin(update):
        await q.answer("Not allowed", show_alert=True)
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0
    try:
        result = await asyncio.to_thread(telegram_actions.handle_callback, q.data, chat_id)
    except Exception as exc:  # report to me instead of crashing the bot
        log.exception("callback failed")
        result = f"⚠️ Error: {exc}"
    await q.answer(result[:190])
    msg = q.message
    try:
        if msg is not None and getattr(msg, "photo", None):
            base = (getattr(msg, "caption", "") or "").split("\n— ")[0]
            markup = getattr(msg, "reply_markup", None)
            await q.edit_message_caption(caption=f"{base}\n— {result}", reply_markup=markup)
        elif msg is not None:
            base = (getattr(msg, "text", "") or "").split("\n— ")[0]
            await q.edit_message_text(text=f"{base}\n— {result}")
    except Exception:  # "message is not modified" etc.
        pass


def run() -> None:
    app = Application.builder().token(get_settings().telegram_bot_token).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(on_button))
    log.info("bot polling")
    app.run_polling(allowed_updates=["message", "callback_query"])
