"""Secondary scoring signal: Twitch chat message-rate spikes.

Takes a chat replay log (list of (timestamp_seconds, message) tuples, as
produced by a chat replay/IRC log dump) and buckets messages into fixed
windows. Windows with a message rate well above the video's average are
scored highly — chat blowing up is a strong signal of a clippable moment,
so this is weighted higher than the transcript-only heuristic when fused
(see scoring/fusion.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ScoredSegment

WINDOW_SECONDS = 10


@dataclass
class ChatEvent:
    timestamp: float
    message: str = ""


class TwitchChatSpikeScorer:
    name = "twitch_chat_spike"

    def __init__(self, window_seconds: float = WINDOW_SECONDS):
        self.window_seconds = window_seconds

    def score(self, events: list[ChatEvent]) -> list[ScoredSegment]:
        if not events:
            return []

        max_ts = max(e.timestamp for e in events)
        n_windows = int(max_ts // self.window_seconds) + 1
        counts = [0] * n_windows
        for e in events:
            idx = int(e.timestamp // self.window_seconds)
            counts[idx] += 1

        avg = sum(counts) / max(len(counts), 1)
        if avg == 0:
            return []

        segments: list[ScoredSegment] = []
        for i, count in enumerate(counts):
            if count <= avg:
                continue
            spike_ratio = count / avg
            start = i * self.window_seconds
            end = start + self.window_seconds
            segments.append(
                ScoredSegment(
                    start=start,
                    end=end,
                    text="",
                    score=min(spike_ratio, 10) * 2,
                    reasons=[f"chat_spike:{count}msgs_vs_avg{avg:.1f}"],
                )
            )
        return segments
