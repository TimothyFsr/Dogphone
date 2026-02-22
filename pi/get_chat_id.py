#!/usr/bin/env python3
"""
One-time helper: print the Telegram Chat ID for the user who last messaged the bot.
Usage:
  1. Create a bot via @BotFather and copy the token.
  2. Send any message to your bot (e.g. "hi").
  3. Run: TELEGRAM_BOT_TOKEN=your_token python get_chat_id.py
  Or set TELEGRAM_BOT_TOKEN in config.env and run: python get_chat_id.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


def main():
    cfg = load_config()
    token = cfg["telegram_bot_token"] or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN in config.env or environment.")
        sys.exit(1)
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        print("API error:", data)
        sys.exit(1)
    updates = data.get("result", [])
    if not updates:
        print("No messages yet. Send any message to your bot (e.g. 'hi'), then run this again.")
        sys.exit(0)
    # Latest update
    last = updates[-1]
    chat_id = None
    if "message" in last:
        chat_id = last["message"]["chat"]["id"]
    elif "edited_message" in last:
        chat_id = last["edited_message"]["chat"]["id"]
    if chat_id is not None:
        print(f"Your Telegram Chat ID: {chat_id}")
        print(f"Add to config.env: TELEGRAM_CHAT_ID={chat_id}")
    else:
        print("Could not find a chat ID in the last update. Send a normal text message to the bot and try again.")


if __name__ == "__main__":
    main()
