"""Transcribes a video with local openai-whisper, producing word-level timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: list[Word]


@dataclass
class Transcript:
    segments: list[TranscriptSegment]

    @property
    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)


_MODEL_CACHE: dict[str, object] = {}


def _load_model(model_name: str):
    if model_name not in _MODEL_CACHE:
        import whisper  # lazy import: heavy dependency, only needed here

        _MODEL_CACHE[model_name] = whisper.load_model(model_name)
    return _MODEL_CACHE[model_name]


def transcribe(video_path: str | Path, model_name: str = "base") -> Transcript:
    """Run Whisper with word-level timestamps on the given media file."""

    model = _load_model(model_name)
    result = model.transcribe(str(video_path), word_timestamps=True)

    segments: list[TranscriptSegment] = []
    for seg in result.get("segments", []):
        words = [
            Word(text=w["word"].strip(), start=w["start"], end=w["end"])
            for w in seg.get("words", [])
        ]
        segments.append(
            TranscriptSegment(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=words,
            )
        )
    return Transcript(segments=segments)
