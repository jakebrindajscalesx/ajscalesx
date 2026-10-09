from __future__ import annotations

import json
from pathlib import Path

import requests

from trading_bot.logger import get_logger

log = get_logger(__name__)


class TelegramClient:
    """Minimal Telegram Bot API client: sends alerts and polls for commands
    typed by you in your chat with the bot. Only messages from the configured
    chat_id are ever acted on.
    """

    def __init__(self, bot_token: str, chat_id: str, offset: int = 0):
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._offset = offset

    @classmethod
    def load(cls, bot_token: str, chat_id: str, offset_path: str | Path) -> "TelegramClient":
        """Restores the update offset from disk. Needed when the process
        doesn't stay running between polls (e.g. a scheduled job) -- without
        this, each run would re-see and re-process every old command."""
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
        """Returns a list of raw command strings sent by the owner since the
        last poll. Non-blocking short poll (safe to call once per main loop)."""
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
    """Parses a raw command string into a structured dict, or None if it's
    not a recognized command.

    Supported commands, typed by you into the Telegram chat:
      /signal SYMBOL buy    -- manually trigger a buy on SYMBOL right now
                                (still subject to all normal risk checks:
                                position sizing, max open positions, circuit
                                breaker)
      /signal SYMBOL close  -- manually close an open position on SYMBOL
      /pause                -- stop opening new positions until /resume
      /resume               -- clear pause and any tripped daily circuit
                                breaker
      /status               -- report current portfolio state
    """
    parts = text.split()
    if not parts:
        return None
    cmd = parts[0].lower()

    if cmd == "/signal" and len(parts) == 3:
        symbol, action = parts[1].upper(), parts[2].lower()
        if action not in ("buy", "close"):
            return None
        return {"type": "signal", "symbol": symbol, "action": action}

    if cmd in ("/pause", "/resume", "/status"):
        return {"type": cmd.lstrip("/")}

    return None
