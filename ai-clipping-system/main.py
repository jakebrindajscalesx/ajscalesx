#!/usr/bin/env python3
"""CLI entrypoint: python main.py --config sources.yaml"""

from __future__ import annotations

import argparse
import logging
import sys

from clipping.config import ConfigError, default_config, load_config
from clipping.downloader import DownloadError
from clipping.pipeline import run, run_single_video


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI clipping pipeline: find, clip, and convert new source videos.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--config", help="Path to sources.yaml: poll all tracked channels for new videos")
    mode.add_argument("--video", help="Process a single video URL directly, no config file needed")

    parser.add_argument("--client", default="adhoc", help="Client/output folder name for --video mode (default: adhoc)")
    parser.add_argument("--platform", default="youtube", choices=["youtube", "twitch"], help="Platform for --video mode")
    parser.add_argument("--vertical-crop", default="center", choices=["center", "face_track"], help="Crop mode for --video mode")
    parser.add_argument("--max-clips", type=int, default=None, help="Cap on clips for --video mode (default: 10)")
    parser.add_argument("--whisper-model", default="base", help="Whisper model size for --video mode (default: base)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.video:
        cfg = default_config(whisper_model=args.whisper_model)
        try:
            result = run_single_video(
                cfg,
                client=args.client,
                url=args.video,
                platform=args.platform,
                vertical_crop=args.vertical_crop,
                max_clips=args.max_clips,
            )
        except DownloadError as exc:
            print(f"Download error: {exc}", file=sys.stderr)
            return 1

        print(f"Generated {result.clip_count} clip(s) from '{result.video_title}'.")
        print(f"Output: {cfg.clients_dir / args.client / result.video_id}")
        return 0

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    results_by_client = run(cfg)

    total_videos = sum(len(r) for r in results_by_client.values())
    total_clips = sum(res.clip_count for results in results_by_client.values() for res in results)
    print(f"Processed {total_videos} new video(s) across {len(results_by_client)} client(s), "
          f"generated {total_clips} clip(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
