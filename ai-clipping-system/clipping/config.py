"""Loads and validates sources.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_PLATFORMS = {"youtube", "twitch"}


class ConfigError(ValueError):
    """Raised when sources.yaml is missing or malformed."""


@dataclass
class Source:
    client: str
    platform: str
    channel: str
    check_frequency_minutes: int = 60
    max_clips_per_video: int = 10
    min_clip_seconds: int = 15
    max_clip_seconds: int = 60
    vertical_crop: str = "center"  # "center" or "face_track"
    secondary_signal: bool = True
    name: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.channel


@dataclass
class PipelineConfig:
    clients_dir: Path
    downloads_dir: Path
    state_path: Path
    default_max_clips_per_video: int = 10
    default_min_clip_seconds: int = 15
    default_max_clip_seconds: int = 60
    whisper_model: str = "base"
    caption_backend: str = "rule_based"  # "rule_based" or "claude"
    sources: list[Source] = field(default_factory=list)


def load_config(path: str | Path) -> PipelineConfig:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    base_dir = path.parent
    defaults = raw.get("defaults", {}) or {}

    clients_dir = base_dir / raw.get("output_dir", "clients")
    downloads_dir = base_dir / raw.get("downloads_dir", "downloads")
    state_path = base_dir / raw.get("state_file", "state.json")

    cfg = PipelineConfig(
        clients_dir=clients_dir,
        downloads_dir=downloads_dir,
        state_path=state_path,
        default_max_clips_per_video=defaults.get("max_clips_per_video", 10),
        default_min_clip_seconds=defaults.get("min_clip_seconds", 15),
        default_max_clip_seconds=defaults.get("max_clip_seconds", 60),
        whisper_model=raw.get("whisper_model", "base"),
        caption_backend=raw.get("caption_backend", "rule_based"),
    )

    raw_sources = raw.get("sources")
    if not raw_sources:
        raise ConfigError("sources.yaml must define at least one entry under 'sources'")

    for i, entry in enumerate(raw_sources):
        try:
            client = entry["client"]
            platform = str(entry["platform"]).lower()
            channel = entry["channel"]
        except KeyError as exc:
            raise ConfigError(f"sources[{i}] is missing required field {exc}") from exc

        if platform not in VALID_PLATFORMS:
            raise ConfigError(
                f"sources[{i}] has unsupported platform '{platform}'. "
                f"Must be one of {sorted(VALID_PLATFORMS)}"
            )

        cfg.sources.append(
            Source(
                client=client,
                platform=platform,
                channel=channel,
                check_frequency_minutes=entry.get("check_frequency_minutes", 60),
                max_clips_per_video=entry.get(
                    "max_clips_per_video", cfg.default_max_clips_per_video
                ),
                min_clip_seconds=entry.get(
                    "min_clip_seconds", cfg.default_min_clip_seconds
                ),
                max_clip_seconds=entry.get(
                    "max_clip_seconds", cfg.default_max_clip_seconds
                ),
                vertical_crop=entry.get("vertical_crop", "center"),
                secondary_signal=entry.get("secondary_signal", True),
                name=entry.get("name"),
            )
        )

    return cfg
