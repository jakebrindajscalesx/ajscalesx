# AI Clipping System

Finds new VODs/uploads from tracked streamers/YouTubers, detects the best
moments with transcript scoring, and converts each one into a captioned,
vertical short-form clip with a JSON manifest ready to hand to a
scheduler (Metricool/Blotato) or post manually.

## Requirements

- Python 3.11+
- [`ffmpeg`](https://ffmpeg.org/) and `ffprobe` on `PATH` (not pip-installable — use your OS package manager, e.g. `apt install ffmpeg` / `brew install ffmpeg`)
- `pip install -r requirements.txt`

## Setup

```bash
cd ai-clipping-system
pip install -r requirements.txt
cp sources.yaml.example sources.yaml
# edit sources.yaml with real client/channel entries
python main.py --config sources.yaml
```

Re-running `python main.py --config sources.yaml` only processes videos
that haven't been seen before — per-channel progress is tracked in
`state.json` (path configurable in `sources.yaml`, gitignored by default).

## How it works

1. **Find** (`clipping/downloader.py`) — lists recent uploads/VODs per
   channel with `yt-dlp`, diffs against `state.json`, downloads anything new.
2. **Clips** (`clipping/transcribe.py`, `clipping/scoring/`,
   `clipping/clip_selector.py`) — transcribes with local Whisper
   (word-level timestamps), scores every segment with a pluggable heuristic,
   merges/dedupes high-scoring segments into 15–60s candidate clips, and
   caps output at `max_clips_per_video` (default 10).
3. **Convert** (`clipping/convert/`) — cuts each candidate with `ffmpeg`,
   reframes to vertical 1080x1920 (center crop by default, optional
   face-tracking crop), burns in styled captions from Whisper word
   timestamps, and grabs a thumbnail at the clip's loudest moment.
4. **Manifest** (`clipping/manifest.py`) — writes `manifest.json` per source
   video with each clip's file, timestamps, score, transcript, and a
   suggested caption/title.

Output is organized per client for billing/reporting:

```
clients/<client_name>/<video_id>/
├── manifest.json
└── clips/
    ├── clip_1.mp4
    ├── clip_1_thumb.jpg
    ├── clip_2.mp4
    └── ...
clients/<client_name>/weekly_summary.json   # appended to on every run
```

## Scoring is pluggable

`clipping/scoring/heuristic.py` holds the baseline keyword/punctuation
transcript scorer. `clipping/scoring/fusion.py` combines it with an
optional secondary engagement signal, weighted higher than the transcript
alone:

- Twitch: `clipping/scoring/twitch_chat.py` scores chat message-rate spikes
  from a chat replay log.
- YouTube: `clipping/scoring/youtube_comments.py` scores timestamped
  comments (e.g. "2:14 lol") as an engagement-velocity proxy.

Neither requires live API access to run: `clipping/secondary_signals.py`
looks for a sidecar file next to the downloaded video —
`<video_id>.chat.json` (TwitchDownloaderCLI export format) or
`<video_id>.comments.json` — and activates the matching scorer only if
found. Drop a fetcher that writes one of those files and the secondary
signal turns on with no other pipeline changes. Set `secondary_signal: false`
on a source in `sources.yaml` to skip this entirely.

To swap the primary heuristic for something else, implement the `Scorer`
protocol in `clipping/scoring/base.py` and pass it into
`clipping/pipeline.py::process_video` — nothing else in the pipeline
depends on how segments get scored.

## Captions/titles

Default is rule-based (`clipping/caption_gen.py`, no API calls): the
shortest well-formed sentence in the clip's transcript becomes the caption.
Set `caption_backend: claude` in `sources.yaml` and export
`ANTHROPIC_API_KEY` to use the Claude API for punchier captions instead.

## Config reference (`sources.yaml`)

See `sources.yaml.example`. Per-source fields:

| Field | Default | Notes |
|---|---|---|
| `client` | required | used for `clients/<client>/...` output path |
| `platform` | required | `youtube` or `twitch` |
| `channel` | required | channel URL, handle, or login name |
| `check_frequency_minutes` | `60` | informational; run the CLI on this cadence via cron/systemd timer |
| `max_clips_per_video` | `10` | cap on candidate clips per source video |
| `min_clip_seconds` / `max_clip_seconds` | `15` / `60` | clip-length window |
| `vertical_crop` | `center` | `center` or `face_track` |
| `secondary_signal` | `true` | enable chat/comment sidecar scoring when available |

## What's out of scope (by design)

- Native TikTok/IG posting or scheduling — hand `manifest.json` to
  Metricool/Blotato or post manually.
- A UI — this is CLI + config file only.
- Live Twitch chat capture / YouTube comment scraping — see "Scoring is
  pluggable" above for the sidecar-file extension point.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover the scoring heuristic, fusion, clip selection, and manifest
modules — no `ffmpeg`/`yt-dlp`/Whisper required to run them.
