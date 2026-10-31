"""Start the FasalKavach Telegram bot on your laptop.

    python run_telegram_bot.py              # run the bot (Ctrl+C to stop)
    python run_telegram_bot.py --check-now  # re-check all fields once and send alerts, then exit
"""
import argparse
import logging

from agent.loop import run_agent
from bot import telegram
from bot.core import Bot
from bot.store import Store
from config import ANTHROPIC_API_KEY


def make_bot() -> Bot:
    return Bot(Store(), send=telegram.send, agent=run_agent if ANTHROPIC_API_KEY else None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-now", action="store_true", help="run the alert check once and exit")
    args = parser.parse_args()

    bot = make_bot()
    if args.check_now:
        print(bot.run_monitor())
    else:
        try:
            telegram.run_polling(bot)
        except KeyboardInterrupt:
            print("\nBot stopped.")
