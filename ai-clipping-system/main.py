#!/usr/bin/env python3
"""CLI entrypoint: python main.py --config sources.yaml"""

from __future__ import annotations

import argparse
import logging
import sys

from clipping.config import ConfigError, load_config
from clipping.pipeline import run


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI clipping pipeline: find, clip, and convert new source videos.")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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
