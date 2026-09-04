from __future__ import annotations

import json
from pathlib import Path

import requests

from meme_bot.logger import get_logger

log = get_logger(__name__)


class TelegramClient:
    """Same shape as ../trading-bot/trading_bot/telegram_bot.py's client --
    sends alerts and polls for commands typed by you in your chat with the
    bot. Only messages from the configured chat_id are ever acted on. Kept
    as a separate copy (rather than importing across the two bots) because
    CI checks out each bot from a single directory independently."""

    def __init__(self, bot_token: str, chat_id: str, offset: int = 0):
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._offset = offset

    @classmethod
    def load(cls, bot_token: str, chat_id: str, offset_path: str | Path) -> "TelegramClient":
        offset = 0
        path = Path(offset_path)
        if path.exists():
            try:
                offset = json.loads(path.read_text()).get("offset", 0)
            except Exception as exc:
                log.warning(f"Could not read Telegram offset file: {exc}")
        return cls(bot_token, chat_id, offset=offset)

    def save_offset(self, offset_path: str | Path) -> None:
        path = Path(offset_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"offset": self._offset}))

    def send(self, text: str) -> None:
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                data={"chat_id": self.chat_id, "text": text},
                timeout=10,
            )
        except Exception as exc:
            log.warning(f"Telegram send failed: {exc}")

    def poll_commands(self) -> list[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/getUpdates",
                params={"offset": self._offset, "timeout": 0},
                timeout=10,
            )
            resp.raise_for_status()
            updates = resp.json().get("result", [])
        except Exception as exc:
            log.warning(f"Telegram poll failed: {exc}")
            return []

        commands = []
        for update in updates:
            self._offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            sender_chat_id = str(message.get("chat", {}).get("id", ""))
            if sender_chat_id != self.chat_id:
                log.warning(f"Ignoring Telegram message from unrecognized chat {sender_chat_id}")
                continue
            if text:
                commands.append(text.strip())
        return commands


def parse_command(text: str) -> dict | None:
    """Supported commands, typed by you into the Telegram chat:
      /confirm <id>   -- execute the proposed trade with that id
      /reject <id>    -- discard the proposed trade with that id
      /pause          -- stop proposing new trades until /resume
      /resume         -- clear pause
      /status         -- report tracked wallets, open positions, today's spend
    """
    parts = text.split()
    if not parts:
        return None
    cmd = parts[0].lower()

    if cmd in ("/confirm", "/reject") and len(parts) == 2:
        return {"type": cmd.lstrip("/"), "trade_id": parts[1]}

    if cmd in ("/pause", "/resume", "/status"):
        return {"type": cmd.lstrip("/")}

    return None
