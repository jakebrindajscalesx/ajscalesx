"""Grabs a thumbnail frame at the highest-energy (loudest) point of a clip.

Energy is approximated from audio RMS rather than pulling in a video
analysis dependency: the clip's audio is extracted to mono WAV, RMS is
computed per short window with the stdlib `audioop`, and the frame at the
loudest window is grabbed as the thumbnail.
"""

from __future__ import annotations

import audioop
import wave
from pathlib import Path

from .ffmpeg_utils import run_ffmpeg

WINDOW_SECONDS = 0.5


def _loudest_timestamp(clip_path: str | Path, duration: float) -> float:
    wav_path = Path(clip_path).with_suffix(".energy.wav")
    try:
        run_ffmpeg(["-i", str(clip_path), "-ac", "1", "-ar", "16000", "-vn", str(wav_path)])
        with wave.open(str(wav_path), "rb") as wf:
            sample_width = wf.getsampwidth()
            frame_rate = wf.getframerate()
            window_frames = max(1, int(WINDOW_SECONDS * frame_rate))

            best_ts = duration / 2
            best_rms = -1
            index = 0
            while True:
                chunk = wf.readframes(window_frames)
                if not chunk:
                    break
                rms = audioop.rms(chunk, sample_width)
                if rms > best_rms:
                    best_rms = rms
                    best_ts = index * WINDOW_SECONDS
                index += 1
            return min(best_ts, max(duration - 0.1, 0))
    except Exception:
        return duration / 2
    finally:
        wav_path.unlink(missing_ok=True)


def generate_thumbnail(clip_path: str | Path, duration: float, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _loudest_timestamp(clip_path, duration)
    run_ffmpeg(
        [
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ]
    )
    return output_path
