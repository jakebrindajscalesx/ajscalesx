"""Local state.json: last-checked timestamp and processed video IDs per channel.

Keeping this separate from the manifest lets a re-run skip already-handled
videos without having to re-read every client's manifest.json.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock


def _channel_key(platform: str, channel: str) -> str:
    return f"{platform}:{channel}"


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = Lock()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {"channels": {}}

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, sort_keys=True)
            tmp.replace(self.path)

    def last_checked(self, platform: str, channel: str) -> float | None:
        entry = self._data["channels"].get(_channel_key(platform, channel))
        return entry.get("last_checked_at") if entry else None

    def processed_video_ids(self, platform: str, channel: str) -> set[str]:
        entry = self._data["channels"].get(_channel_key(platform, channel))
        return set(entry.get("processed_video_ids", [])) if entry else set()

    def mark_checked(self, platform: str, channel: str) -> None:
        key = _channel_key(platform, channel)
        entry = self._data["channels"].setdefault(
            key, {"last_checked_at": None, "processed_video_ids": []}
        )
        entry["last_checked_at"] = time.time()

    def mark_processed(self, platform: str, channel: str, video_id: str) -> None:
        key = _channel_key(platform, channel)
        entry = self._data["channels"].setdefault(
            key, {"last_checked_at": None, "processed_video_ids": []}
        )
        if video_id not in entry["processed_video_ids"]:
            entry["processed_video_ids"].append(video_id)
