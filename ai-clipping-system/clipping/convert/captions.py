"""Builds styled burned-in captions (ASS subtitles) from Whisper word timestamps.

Words are grouped into short (max ~4 word / ~2.2s) chunks so captions read
like punchy short-form subtitles rather than a wall of text, and are styled
(bold, outlined, centered low-third) instead of relying on ffmpeg's default
raw subtitle rendering.
"""

from __future__ import annotations

from pathlib import Path

from ..transcribe import Word

MAX_WORDS_PER_CHUNK = 4
MAX_CHUNK_SECONDS = 2.2

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Black,72,&H00FFFFFF,&H00000000,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,5,0,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_ts(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    centiseconds = int(round((s - int(s)) * 100))
    return f"{h:d}:{m:02d}:{int(s):02d}.{centiseconds:02d}"


def _chunk_words(words: list[Word]) -> list[list[Word]]:
    chunks: list[list[Word]] = []
    current: list[Word] = []

    for word in words:
        if current:
            span = word.end - current[0].start
            if len(current) >= MAX_WORDS_PER_CHUNK or span > MAX_CHUNK_SECONDS:
                chunks.append(current)
                current = []
        current.append(word)

    if current:
        chunks.append(current)
    return chunks


def generate_ass_captions(words: list[Word], clip_start: float, output_path: str | Path) -> Path:
    """Writes an .ass file with captions timed relative to clip_start (i.e.
    word.start - clip_start = time within the cut clip)."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [ASS_HEADER]
    for chunk in _chunk_words(words):
        start = max(0.0, chunk[0].start - clip_start)
        end = max(start + 0.1, chunk[-1].end - clip_start)
        text = " ".join(w.text for w in chunk).upper().replace("\n", " ")
        lines.append(
            f"Dialogue: 0,{_format_ts(start)},{_format_ts(end)},Caption,,0,0,0,,{text}\n"
        )

    output_path.write_text("".join(lines), encoding="utf-8")
    return output_path


def ass_filter_arg(ass_path: str | Path) -> str:
    """Escapes an .ass path for use inside an ffmpeg -vf filtergraph."""

    escaped = str(ass_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return f"ass='{escaped}'"
