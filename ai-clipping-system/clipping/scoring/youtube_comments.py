"""Secondary scoring signal: YouTube comment velocity / timestamped comments.

Two inputs are folded into one score per referenced moment:
  - Plain comment velocity isn't timestamp-addressable on its own, so the
    useful signal is *timestamped* comments (e.g. "2:14 lol", "13:05 this
    part") which viewers leave to point at specific highlights.
  - Each timestamped comment becomes a scored window around that moment;
    windows referenced by multiple comments score higher (clustering acts
    as a velocity proxy).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .base import ScoredSegment

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
WINDOW_RADIUS_SECONDS = 8


@dataclass
class Comment:
    text: str
    like_count: int = 0


def _extract_timestamp_seconds(text: str) -> float | None:
    match = TIMESTAMP_PATTERN.search(text)
    if not match:
        return None
    h, m, s = match.groups()
    total = int(m) * 60 + int(s)
    if h:
        total += int(h) * 3600
    return float(total)


class YoutubeCommentVelocityScorer:
    name = "youtube_comment_velocity"

    def __init__(self, window_radius_seconds: float = WINDOW_RADIUS_SECONDS):
        self.window_radius_seconds = window_radius_seconds

    def score(self, comments: list[Comment]) -> list[ScoredSegment]:
        timestamped: list[tuple[float, Comment]] = []
        for c in comments:
            ts = _extract_timestamp_seconds(c.text)
            if ts is not None:
                timestamped.append((ts, c))

        if not timestamped:
            return []

        segments: list[ScoredSegment] = []
        for ts, comment in timestamped:
            weight = 1.0 + min(comment.like_count, 500) / 100.0
            segments.append(
                ScoredSegment(
                    start=max(0.0, ts - self.window_radius_seconds),
                    end=ts + self.window_radius_seconds,
                    text=comment.text,
                    score=weight * 2,
                    reasons=[f"timestamped_comment(likes={comment.like_count})"],
                )
            )
        return segments
