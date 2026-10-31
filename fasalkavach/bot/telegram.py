"""Telegram adapter: converts Telegram updates <-> bot core messages.

Two ways to receive messages:
- polling  (run_telegram_bot.py): the bot asks Telegram "anything new?" - works on a laptop
- webhook  (/telegram/webhook in app.py): Telegram pushes to our server - used when deployed
"""
import logging
import time

import requests

from config import CHECK_INTERVAL_HOURS, TELEGRAM_BOT_TOKEN

from .core import Bot, Incoming, Outgoing

log = logging.getLogger("fasalkavach.telegram")
CHANNEL = "telegram"
MAX_LEN = 4096  # Telegram's message length limit

COMMANDS = [
    ("add", "Register a field / खेत जोड़ें"),
    ("status", "Check my fields now / अभी जाँच"),
    ("fields", "List my fields / मेरे खेत"),
    ("language", "Change language / भाषा"),
    ("stop", "Pause alerts / अलर्ट बंद"),
    ("resume", "Resume alerts / अलर्ट चालू"),
    ("help", "Help / मदद"),
]


def api(method: str, payload: dict | None = None, timeout: int = 15) -> dict:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")
    resp = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
                         json=payload or {}, timeout=timeout)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
    return data["result"]


def parse_update(update: dict) -> Incoming | None:
    msg = update.get("message") or update.get("edited_message")
    if not msg or "chat" not in msg:
        return None
    loc = msg.get("location")
    return Incoming(
        channel=CHANNEL,
        chat_id=str(msg["chat"]["id"]),
        text=msg.get("text"),
        location=(loc["latitude"], loc["longitude"]) if loc else None,
    )


def build_payload(chat_id: str, out: Outgoing) -> dict:
    payload = {"chat_id": chat_id, "text": out.text[:MAX_LEN]}
    if out.request_location:
        payload["reply_markup"] = {"keyboard": [[{"text": out.request_location, "request_location": True}]],
                                   "resize_keyboard": True, "one_time_keyboard": True}
    elif out.buttons:
        payload["reply_markup"] = {"keyboard": [[{"text": b} for b in row] for row in out.buttons],
                                   "resize_keyboard": True, "one_time_keyboard": True}
    elif out.remove_keyboard:
        payload["reply_markup"] = {"remove_keyboard": True}
    return payload


def send(channel: str, chat_id: str, out: Outgoing):
    try:
        api("sendMessage", build_payload(chat_id, out))
    except Exception as e:  # a failed send must not crash the bot
        log.warning("Could not send to %s: %s", chat_id, e)


def handle_update(bot: Bot, update: dict):
    msg = parse_update(update)
    if msg is None:
        return
    try:
        bot.handle(msg)
    except Exception:
        log.exception("Error handling message from %s", msg.chat_id)
        send(CHANNEL, msg.chat_id, Outgoing("⚠️ Something went wrong. Please try again or send /help."))


def setup_commands():
    api("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in COMMANDS]})


def set_webhook(url: str, secret: str):
    api("setWebhook", {"url": url, "secret_token": secret, "allowed_updates": ["message", "edited_message"]})


def run_polling(bot: Bot):
    """Long-polling loop for local use. Also runs the monitor every CHECK_INTERVAL_HOURS."""
    api("deleteWebhook")   # polling and webhook cannot both be active
    setup_commands()
    me = api("getMe")
    log.info("Bot @%s is running. Open Telegram and send /start", me["username"])
    print(f"\n✅ Bot @{me['username']} is running - open https://t.me/{me['username']} and send /start")
    print("   Press Ctrl+C to stop.\n")

    offset = None
    next_check = time.time() + CHECK_INTERVAL_HOURS * 3600
    backoff = 1
    while True:
        try:
            updates = api("getUpdates", {"timeout": 30, "offset": offset}, timeout=40)
            backoff = 1
        except Exception as e:
            log.warning("getUpdates failed (%s), retrying in %ss", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            handle_update(bot, u)
        if time.time() >= next_check:
            bot.run_monitor()
            next_check = time.time() + CHECK_INTERVAL_HOURS * 3600
