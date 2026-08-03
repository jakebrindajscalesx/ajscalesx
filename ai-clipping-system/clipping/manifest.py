"""Builds and writes manifest.json for a source video's generated clips."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ManifestClip:
    file: str
    start: float
    end: float
    score: float
    transcript: str
    suggested_caption: str
    thumbnail: str


@dataclass
class Manifest:
    source_video: str
    clips: list[ManifestClip] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_video": self.source_video,
            "clips": [asdict(c) for c in self.clips],
        }


def write_manifest(manifest: Manifest, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "manifest.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2)
    return path
