"""Suggests a short post title/caption for a clip from its transcript snippet.

Default is rule-based (no API calls): pick the most quotable short sentence
and title-case it. If caption_backend="claude" and ANTHROPIC_API_KEY is set,
delegate to the Claude API for a punchier caption instead.
"""

from __future__ import annotations

import os
import re

MAX_CAPTION_WORDS = 10


def _rule_based_caption(transcript: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if s.strip()]
    if not sentences:
        return "Watch this clip"

    # Prefer the shortest sentence that still reads like a complete thought
    # (avoids grabbing a run-on as the caption).
    candidates = sorted(sentences, key=len)
    best = next((s for s in candidates if 3 <= len(s.split()) <= 16), candidates[0])

    words = best.split()
    if len(words) > MAX_CAPTION_WORDS:
        words = words[:MAX_CAPTION_WORDS]
    caption = " ".join(words).strip(" .,!?")
    return caption[:1].upper() + caption[1:] if caption else "Watch this clip"


def _claude_caption(transcript: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # lazy import: optional dependency
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "Write a 6-10 word TikTok caption for this clip. "
        "No hashtags, no quotes, just the caption text.\n\n"
        f"Transcript: {transcript}"
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=40,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return text.strip().strip('"') or None
    except Exception:
        return None


def suggest_caption(transcript: str, backend: str = "rule_based") -> str:
    if backend == "claude":
        result = _claude_caption(transcript)
        if result:
            return result
    return _rule_based_caption(transcript)
