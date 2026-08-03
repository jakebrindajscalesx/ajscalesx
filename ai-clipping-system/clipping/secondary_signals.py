"""Optional secondary-signal inputs: Twitch chat replay logs and YouTube
timestamped comments.

Live chat capture (Twitch IRC) and comment scraping (YouTube Data API) are
out of scope for this pipeline — they need their own credentials/tooling
(e.g. TwitchDownloaderCLI for chat replay export, or a Data API key for
comments). Instead, this module is the pluggable seam: if a matching
sidecar file exists next to the downloaded video, it's parsed and fed into
the chat-spike / comment-velocity scorers; if not, the pipeline silently
falls back to the transcript heuristic alone. Drop in a fetcher that writes
these sidecar files and the secondary signal activates with no pipeline
changes.
"""

from __future__ import annotations

import json
from pathlib import Path

from .scoring import ChatEvent, Comment

CHAT_LOG_SUFFIX = ".chat.json"
COMMENTS_SUFFIX = ".comments.json"


def sidecar_path(video_path: str | Path, suffix: str) -> Path:
    video_path = Path(video_path)
    return video_path.with_suffix("").with_suffix(suffix)


def load_twitch_chat_log(video_path: str | Path) -> list[ChatEvent] | None:
    """Expects TwitchDownloaderCLI-style JSON: {"comments": [{"content_offset_seconds": 12.3, "message": {"body": "..."}}]}."""

    path = sidecar_path(video_path, CHAT_LOG_SUFFIX)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    events: list[ChatEvent] = []
    for entry in data.get("comments", []):
        ts = entry.get("content_offset_seconds")
        if ts is None:
            continue
        message = (entry.get("message") or {}).get("body", "")
        events.append(ChatEvent(timestamp=float(ts), message=message))
    return events


def load_youtube_comments(video_path: str | Path) -> list[Comment] | None:
    """Expects a JSON list: [{"text": "2:14 lol", "like_count": 12}, ...]."""

    path = sidecar_path(video_path, COMMENTS_SUFFIX)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return [Comment(text=c.get("text", ""), like_count=c.get("like_count", 0)) for c in data]
