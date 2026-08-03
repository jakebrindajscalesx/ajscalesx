"""Finds new uploads/VODs for a tracked channel and downloads them with yt-dlp."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Source
from .state import StateStore

logger = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    pass


@dataclass
class VideoRef:
    video_id: str
    url: str
    title: str
    upload_date: str | None = None  # YYYYMMDD, from yt-dlp
    duration: float | None = None


def _channel_listing_url(source: Source) -> str:
    if source.platform == "twitch":
        # /videos lists past broadcasts (VODs); yt-dlp handles channel URLs
        # and bare login names.
        if source.channel.startswith("http"):
            return source.channel
        return f"https://www.twitch.tv/{source.channel}/videos"
    # youtube
    if source.channel.startswith("http"):
        return source.channel
    return f"https://www.youtube.com/{source.channel}"


def find_new_videos(source: Source, state: StateStore, limit: int = 15) -> list[VideoRef]:
    """List recent videos for a channel and filter out ones already processed."""

    listing_url = _channel_listing_url(source)
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--playlist-end",
        str(limit),
        listing_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    except FileNotFoundError as exc:
        raise DownloadError("yt-dlp is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"yt-dlp listing failed for {listing_url}: {exc.stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DownloadError(f"yt-dlp listing timed out for {listing_url}") from exc

    payload = json.loads(result.stdout)
    entries = payload.get("entries") or []

    processed = state.processed_video_ids(source.platform, source.channel)
    fresh: list[VideoRef] = []
    for entry in entries:
        video_id = str(entry.get("id"))
        if not video_id or video_id in processed:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            continue
        if not url.startswith("http"):
            # --flat-playlist sometimes only returns bare IDs.
            url = f"https://www.youtube.com/watch?v={video_id}" if source.platform == "youtube" else url
        fresh.append(
            VideoRef(
                video_id=video_id,
                url=url,
                title=entry.get("title") or video_id,
                upload_date=entry.get("upload_date"),
                duration=entry.get("duration"),
            )
        )

    return fresh


def download_video(video: VideoRef, dest_dir: str | Path) -> Path:
    """Download a video with yt-dlp and return the path to the downloaded file."""

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(dest_dir / f"{video.video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f",
        "bv*[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format",
        "mp4",
        "-o",
        out_template,
        video.url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=True)
    except FileNotFoundError as exc:
        raise DownloadError("yt-dlp is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"yt-dlp download failed for {video.url}: {exc.stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DownloadError(f"yt-dlp download timed out for {video.url}") from exc

    matches = sorted(dest_dir.glob(f"{video.video_id}.*"))
    video_files = [p for p in matches if p.suffix.lower() in {".mp4", ".mkv", ".webm"}]
    if not video_files:
        raise DownloadError(f"yt-dlp reported success but no output file found for {video.video_id}")
    return video_files[0]
