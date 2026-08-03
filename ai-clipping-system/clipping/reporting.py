"""Weekly per-client summary: videos processed, clips generated, top clips by score."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class VideoRunResult:
    video_id: str
    video_title: str
    clip_count: int
    top_clips: list[dict] = field(default_factory=list)  # {"file", "score", "suggested_caption"}


def append_weekly_summary(client_dir: str | Path, results: list[VideoRunResult]) -> Path:
    """Appends a dated entry to <client_dir>/weekly_summary.json summarizing
    this run, and returns the path. Called once per client per pipeline run;
    the file accumulates one entry per run so a week's worth can be reviewed
    together."""

    client_dir = Path(client_dir)
    client_dir.mkdir(parents=True, exist_ok=True)
    summary_path = client_dir / "weekly_summary.json"

    entries = []
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as f:
            entries = json.load(f)

    all_clips = [
        {"video_id": r.video_id, "video_title": r.video_title, **clip}
        for r in results
        for clip in r.top_clips
    ]
    top3 = sorted(all_clips, key=lambda c: c["score"], reverse=True)[:3]

    entries.append(
        {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "videos_processed": len(results),
            "clips_generated": sum(r.clip_count for r in results),
            "top_3_clips": top3,
        }
    )

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    return summary_path
