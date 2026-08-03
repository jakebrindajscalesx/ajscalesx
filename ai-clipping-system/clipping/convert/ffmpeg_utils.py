"""Thin subprocess wrappers around ffmpeg/ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class FfmpegError(RuntimeError):
    pass


def run_ffmpeg(args: list[str], timeout: int = 600) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
    except FileNotFoundError as exc:
        raise FfmpegError("ffmpeg is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise FfmpegError(f"ffmpeg failed: {exc.stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise FfmpegError(f"ffmpeg timed out: {' '.join(cmd)}") from exc


def probe_dimensions(video_path: str | Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
    except FileNotFoundError as exc:
        raise FfmpegError("ffprobe is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise FfmpegError(f"ffprobe failed: {exc.stderr}") from exc

    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def cut_clip(source_path: str | Path, start: float, end: float, dest_path: str | Path) -> None:
    """Cut [start, end) out of source_path into dest_path, re-encoding so the
    cut is frame-accurate (stream-copy can only cut on keyframes)."""

    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(end - start, 0.1)
    run_ffmpeg(
        [
            "-ss",
            f"{start:.3f}",
            "-i",
            str(source_path),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            str(dest_path),
        ]
    )
