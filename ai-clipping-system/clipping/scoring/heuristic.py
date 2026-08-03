"""Keyword/punctuation heuristic transcript scorer.

This is the baseline "clip_finder" signal: it scores each transcript segment
by looking for hook words, emotional/emphasis language, punctuation that
signals a punchline or reaction, and segment length. It has no external
dependencies, so it always runs, and other scorers (chat spikes, comment
velocity) are combined with it via scoring/fusion.py rather than replacing
it.
"""

from __future__ import annotations

import re

from ..transcribe import Transcript
from .base import ScoredSegment

HOOK_KEYWORDS = [
    "crazy",
    "insane",
    "unbelievable",
    "no way",
    "what the",
    "oh my god",
    "wait what",
    "let me tell you",
    "here's the thing",
    "the secret",
    "nobody tells you",
    "biggest mistake",
    "game changer",
    "life changing",
    "i can't believe",
    "you won't believe",
    "this changed everything",
    "worst",
    "best",
    "never seen",
    "actually",
    "literally",
    "honestly",
]

EMPHASIS_KEYWORDS = [
    "important",
    "key",
    "remember",
    "warning",
    "secret",
    "truth",
    "mistake",
    "wrong",
    "right",
    "amazing",
    "incredible",
    "shocking",
]

REACTION_MARKERS = ["lol", "lmao", "wow", "damn", "oh no", "yo", "bro"]


class TranscriptHeuristicScorer:
    name = "transcript_heuristic"

    def __init__(
        self,
        hook_keywords: list[str] | None = None,
        emphasis_keywords: list[str] | None = None,
        reaction_markers: list[str] | None = None,
    ):
        self.hook_keywords = hook_keywords or HOOK_KEYWORDS
        self.emphasis_keywords = emphasis_keywords or EMPHASIS_KEYWORDS
        self.reaction_markers = reaction_markers or REACTION_MARKERS

    def score(self, transcript: Transcript) -> list[ScoredSegment]:
        return [self._score_segment(seg.text, seg.start, seg.end) for seg in transcript.segments]

    def _score_segment(self, text: str, start: float, end: float) -> ScoredSegment:
        lowered = text.lower()
        score = 0.0
        reasons: list[str] = []

        for kw in self.hook_keywords:
            if kw in lowered:
                score += 3
                reasons.append(f"hook:{kw}")

        for kw in self.emphasis_keywords:
            if kw in lowered:
                score += 2
                reasons.append(f"emphasis:{kw}")

        for kw in self.reaction_markers:
            if re.search(rf"\b{re.escape(kw)}\b", lowered):
                score += 1.5
                reasons.append(f"reaction:{kw}")

        exclamations = text.count("!")
        if exclamations:
            score += min(exclamations, 3) * 1.5
            reasons.append(f"exclamations:{exclamations}")

        questions = text.count("?")
        if questions:
            score += min(questions, 2) * 1.0
            reasons.append(f"questions:{questions}")

        word_count = len(text.split())
        if word_count > 40:
            score += 2
            reasons.append("long_explanation")
        elif word_count < 4:
            score -= 1
            reasons.append("too_short")

        return ScoredSegment(start=start, end=end, text=text, score=score, reasons=reasons)
