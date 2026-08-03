"""Combines the transcript heuristic score with an optional secondary signal.

Secondary signals (chat spikes, comment velocity) are weighted higher than
the transcript alone, per spec: any primary segment that overlaps a
secondary-signal window gets a boosted score, and windows with no
transcript overlap are kept too (a chat spike can happen where the
heuristic found nothing interesting to say).
"""

from __future__ import annotations

from .base import ScoredSegment

DEFAULT_SECONDARY_WEIGHT = 2.0


def _overlaps(a: ScoredSegment, b: ScoredSegment) -> bool:
    return a.start < b.end and b.start < a.end


def combine_scores(
    primary: list[ScoredSegment],
    secondary: list[ScoredSegment] | None = None,
    secondary_weight: float = DEFAULT_SECONDARY_WEIGHT,
) -> list[ScoredSegment]:
    if not secondary:
        return list(primary)

    combined: list[ScoredSegment] = []
    used_secondary_idx: set[int] = set()

    for seg in primary:
        boost = 0.0
        reasons = list(seg.reasons)
        for i, sec in enumerate(secondary):
            if _overlaps(seg, sec):
                boost += sec.score * secondary_weight
                reasons.extend(sec.reasons)
                used_secondary_idx.add(i)
        combined.append(
            ScoredSegment(start=seg.start, end=seg.end, text=seg.text, score=seg.score + boost, reasons=reasons)
        )

    # Secondary-only windows (e.g. a chat spike with no matching transcript
    # segment) still deserve a candidate clip.
    for i, sec in enumerate(secondary):
        if i in used_secondary_idx:
            continue
        combined.append(
            ScoredSegment(
                start=sec.start,
                end=sec.end,
                text=sec.text,
                score=sec.score * secondary_weight,
                reasons=list(sec.reasons),
            )
        )

    return combined
