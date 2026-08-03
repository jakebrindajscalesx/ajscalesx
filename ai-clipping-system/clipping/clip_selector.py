"""Turns scored transcript segments into a ranked, deduped list of candidate clips."""

from __future__ import annotations

from dataclasses import dataclass

from .scoring.base import ScoredSegment

MERGE_GAP_SECONDS = 4.0


@dataclass
class ClipCandidate:
    start: float
    end: float
    score: float
    transcript: str
    reasons: list[str]

    @property
    def duration(self) -> float:
        return self.end - self.start


def _merge_nearby(segments: list[ScoredSegment], merge_gap: float) -> list[ClipCandidate]:
    """Merge segments that are adjacent/overlapping (within merge_gap) into
    single windows, summing score and concatenating transcript text."""

    positive = [s for s in segments if s.score > 0]
    if not positive:
        return []

    ordered = sorted(positive, key=lambda s: s.start)
    merged: list[ClipCandidate] = []
    current = ClipCandidate(
        start=ordered[0].start,
        end=ordered[0].end,
        score=ordered[0].score,
        transcript=ordered[0].text,
        reasons=list(ordered[0].reasons),
    )

    for seg in ordered[1:]:
        if seg.start - current.end <= merge_gap:
            current.end = max(current.end, seg.end)
            current.score += seg.score
            if seg.text:
                current.transcript = f"{current.transcript} {seg.text}".strip()
            current.reasons.extend(seg.reasons)
        else:
            merged.append(current)
            current = ClipCandidate(
                start=seg.start,
                end=seg.end,
                score=seg.score,
                transcript=seg.text,
                reasons=list(seg.reasons),
            )
    merged.append(current)
    return merged


def _fit_to_length(
    clip: ClipCandidate, min_seconds: float, max_seconds: float
) -> ClipCandidate:
    """Pad short clips out to min_seconds, and trim long ones to max_seconds
    around the highest-density (start) point."""

    duration = clip.duration
    if duration < min_seconds:
        pad = (min_seconds - duration) / 2
        clip.start = max(0.0, clip.start - pad)
        clip.end = clip.start + min_seconds
    elif duration > max_seconds:
        clip.end = clip.start + max_seconds
    return clip


def _dedupe_overlaps(clips: list[ClipCandidate], overlap_threshold: float = 0.5) -> list[ClipCandidate]:
    """Given clips already sorted by descending score, drop any clip whose
    overlap with a higher-scored, already-kept clip exceeds the threshold
    (fraction of the shorter clip's duration)."""

    kept: list[ClipCandidate] = []
    for clip in clips:
        overlaps_existing = False
        for existing in kept:
            overlap = min(clip.end, existing.end) - max(clip.start, existing.start)
            if overlap <= 0:
                continue
            shorter = min(clip.duration, existing.duration)
            if shorter > 0 and overlap / shorter >= overlap_threshold:
                overlaps_existing = True
                break
        if not overlaps_existing:
            kept.append(clip)
    return kept


def select_clips(
    scored_segments: list[ScoredSegment],
    min_seconds: float = 15,
    max_seconds: float = 60,
    max_clips: int = 10,
    merge_gap: float = MERGE_GAP_SECONDS,
) -> list[ClipCandidate]:
    """Merge -> fit-to-length -> rank -> dedupe -> cap at max_clips."""

    merged = _merge_nearby(scored_segments, merge_gap)
    fitted = [_fit_to_length(c, min_seconds, max_seconds) for c in merged]
    ranked = sorted(fitted, key=lambda c: c.score, reverse=True)
    deduped = _dedupe_overlaps(ranked)
    return deduped[:max_clips]
