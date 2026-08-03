"""Orchestrates the per-clip conversion: cut -> vertical crop -> caption
burn-in -> thumbnail. This is the only module pipeline.py needs to call for
the "Convert" stage; the individual steps live in ffmpeg_utils/crop/captions/
thumbnail so each is independently testable.
"""

from __future__ import annotations

from pathlib import Path

from ..clip_selector import ClipCandidate
from ..transcribe import Word
from . import captions as captions_mod
from . import crop as crop_mod
from . import thumbnail as thumbnail_mod
from .ffmpeg_utils import cut_clip, probe_dimensions, run_ffmpeg


def render_clip(
    source_video: str | Path,
    clip: ClipCandidate,
    words: list[Word],
    out_dir: str | Path,
    clip_name: str,
    vertical_crop_mode: str = "center",
) -> tuple[Path, Path]:
    """Renders one candidate clip to `<out_dir>/<clip_name>.mp4` with a
    `<clip_name>_thumb.jpg` thumbnail. Returns (video_path, thumbnail_path)."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_cut = out_dir / f"{clip_name}_raw.mp4"
    final_video = out_dir / f"{clip_name}.mp4"
    ass_path = out_dir / f"{clip_name}.ass"
    thumb_path = out_dir / f"{clip_name}_thumb.jpg"

    cut_clip(source_video, clip.start, clip.end, raw_cut)

    width, height = probe_dimensions(raw_cut)
    x_center_frac = 0.5
    if vertical_crop_mode == "face_track":
        detected = crop_mod.detect_face_x_center(raw_cut)
        if detected is not None:
            x_center_frac = detected
    vertical_filter = crop_mod.build_vertical_filter(width, height, vertical_crop_mode, x_center_frac)

    clip_words = [w for w in words if clip.start <= w.start < clip.end]
    captions_mod.generate_ass_captions(clip_words, clip.start, ass_path)

    filter_graph = f"{vertical_filter},{captions_mod.ass_filter_arg(ass_path)}"
    run_ffmpeg(
        [
            "-i",
            str(raw_cut),
            "-vf",
            filter_graph,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            str(final_video),
        ]
    )

    thumbnail_mod.generate_thumbnail(final_video, clip.duration, thumb_path)

    raw_cut.unlink(missing_ok=True)
    ass_path.unlink(missing_ok=True)

    return final_video, thumb_path
