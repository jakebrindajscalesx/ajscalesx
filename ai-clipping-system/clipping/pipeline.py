"""Orchestrates Find -> Clips -> Convert -> Manifest for every tracked source."""

from __future__ import annotations

import logging

from . import secondary_signals
from .caption_gen import suggest_caption
from .clip_selector import select_clips
from .config import PipelineConfig, Source
from .convert.render import render_clip
from .downloader import DownloadError, VideoRef, download_video, find_new_videos, resolve_video_ref
from .manifest import Manifest, ManifestClip, write_manifest
from .reporting import VideoRunResult, append_weekly_summary
from .scoring import TranscriptHeuristicScorer, TwitchChatSpikeScorer, YoutubeCommentVelocityScorer, combine_scores
from .state import StateStore
from .transcribe import Transcript, Word, transcribe

logger = logging.getLogger(__name__)

TOP_CLIPS_FOR_SUMMARY = 3
SECONDARY_WEIGHT = 2.0


def _flatten_words(transcript: Transcript) -> list[Word]:
    return [w for seg in transcript.segments for w in seg.words]


def _secondary_scores(source: Source, local_video_path):
    if not source.secondary_signal:
        return None

    if source.platform == "twitch":
        events = secondary_signals.load_twitch_chat_log(local_video_path)
        if not events:
            return None
        return TwitchChatSpikeScorer().score(events)

    if source.platform == "youtube":
        comments = secondary_signals.load_youtube_comments(local_video_path)
        if not comments:
            return None
        return YoutubeCommentVelocityScorer().score(comments)

    return None


def _process_video_core(
    cfg: PipelineConfig,
    source: Source,
    video: VideoRef,
) -> VideoRunResult:
    logger.info("Processing %s (%s) for client %s", video.title, video.video_id, source.client)

    local_video_path = download_video(video, cfg.downloads_dir)
    transcript = transcribe(local_video_path, cfg.whisper_model)
    words = _flatten_words(transcript)

    primary_scores = TranscriptHeuristicScorer().score(transcript)
    secondary = _secondary_scores(source, local_video_path)
    combined = combine_scores(primary_scores, secondary, SECONDARY_WEIGHT)

    candidates = select_clips(
        combined,
        min_seconds=source.min_clip_seconds,
        max_seconds=source.max_clip_seconds,
        max_clips=source.max_clips_per_video,
    )

    video_dir = cfg.clients_dir / source.client / video.video_id
    clips_dir = video_dir / "clips"

    manifest = Manifest(source_video=video.url)
    top_clips_for_summary = []

    for i, clip in enumerate(candidates, start=1):
        clip_name = f"clip_{i}"
        video_path, thumb_path = render_clip(
            local_video_path,
            clip,
            words,
            clips_dir,
            clip_name,
            vertical_crop_mode=source.vertical_crop,
        )
        caption = suggest_caption(clip.transcript, backend=cfg.caption_backend)

        manifest.clips.append(
            ManifestClip(
                file=video_path.name,
                start=round(clip.start, 2),
                end=round(clip.end, 2),
                score=round(clip.score, 2),
                transcript=clip.transcript,
                suggested_caption=caption,
                thumbnail=thumb_path.name,
            )
        )
        if i <= TOP_CLIPS_FOR_SUMMARY:
            top_clips_for_summary.append(
                {"file": video_path.name, "score": round(clip.score, 2), "suggested_caption": caption}
            )

    write_manifest(manifest, video_dir)

    return VideoRunResult(
        video_id=video.video_id,
        video_title=video.title,
        clip_count=len(candidates),
        top_clips=top_clips_for_summary,
    )


def process_video(
    cfg: PipelineConfig,
    source: Source,
    video: VideoRef,
    state: StateStore,
) -> VideoRunResult:
    result = _process_video_core(cfg, source, video)
    state.mark_processed(source.platform, source.channel, video.video_id)
    return result


def run_single_video(
    cfg: PipelineConfig,
    client: str,
    url: str,
    platform: str = "youtube",
    vertical_crop: str = "center",
    max_clips: int | None = None,
    min_seconds: int | None = None,
    max_seconds: int | None = None,
) -> VideoRunResult:
    """Process exactly one video URL, bypassing channel polling/state
    tracking entirely — for ad-hoc `python main.py --video <url>` runs."""

    source = Source(
        client=client,
        platform=platform,
        channel=url,
        max_clips_per_video=max_clips or cfg.default_max_clips_per_video,
        min_clip_seconds=min_seconds or cfg.default_min_clip_seconds,
        max_clip_seconds=max_seconds or cfg.default_max_clip_seconds,
        vertical_crop=vertical_crop,
        secondary_signal=False,
    )
    video = resolve_video_ref(url)
    result = _process_video_core(cfg, source, video)
    append_weekly_summary(cfg.clients_dir / client, [result])
    return result


def run(cfg: PipelineConfig) -> dict[str, list[VideoRunResult]]:
    state = StateStore(cfg.state_path)
    results_by_client: dict[str, list[VideoRunResult]] = {}

    for source in cfg.sources:
        try:
            new_videos = find_new_videos(source, state)
        except DownloadError:
            logger.exception("Failed to list videos for %s/%s", source.platform, source.channel)
            continue

        for video in new_videos:
            try:
                result = process_video(cfg, source, video, state)
            except DownloadError:
                logger.exception("Failed to download %s", video.video_id)
                continue
            except Exception:
                logger.exception("Failed to process %s", video.video_id)
                continue

            results_by_client.setdefault(source.client, []).append(result)
            state.save()

        state.mark_checked(source.platform, source.channel)
        state.save()

    for client, results in results_by_client.items():
        append_weekly_summary(cfg.clients_dir / client, results)

    return results_by_client
