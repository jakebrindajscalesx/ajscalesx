"""Shared types for the pluggable scoring system.

Every scorer takes a Transcript and returns a list of ScoredSegment, one per
transcript segment. `fusion.combine_scores` merges a primary (transcript)
scorer with an optional secondary (chat/comments) scorer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..transcribe import Transcript


@dataclass
class ScoredSegment:
    start: float
    end: float
    text: str
    score: float
    reasons: list[str] = field(default_factory=list)


class Scorer(Protocol):
    """A pluggable scoring signal. Implementations may be transcript-based
    (heuristic keyword/punctuation) or engagement-based (chat/comments)."""

    name: str

    def score(self, transcript: Transcript) -> list[ScoredSegment]:
        ...
