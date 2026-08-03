"""Builds the ffmpeg filter that reframes a clip to vertical 9:16 (1080x1920).

Default is a center crop. `face_track` is the stretch goal: sample a few
frames with a lightweight OpenCV Haar-cascade face detector to find where
the speaker is horizontally, then offset the crop window toward them
(still a single static offset per clip, not per-frame tracking — enough to
keep a stationary speaker in frame without the cost of a full tracker).
"""

from __future__ import annotations

from pathlib import Path

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT


def _crop_geometry(source_width: int, source_height: int, x_center_frac: float) -> tuple[int, int, int, int]:
    """Returns (crop_w, crop_h, x, y) for a 9:16 crop centered horizontally at
    x_center_frac (0..1) of the source width, clamped to stay in bounds."""

    source_ratio = source_width / source_height
    if source_ratio > TARGET_RATIO:
        # Source is wider than 9:16: crop width, keep full height.
        crop_h = source_height
        crop_w = int(round(crop_h * TARGET_RATIO))
    else:
        # Source is taller/narrower than 9:16: crop height, keep full width.
        crop_w = source_width
        crop_h = int(round(crop_w / TARGET_RATIO))

    x = int(round(x_center_frac * source_width - crop_w / 2))
    x = max(0, min(x, source_width - crop_w))
    y = max(0, (source_height - crop_h) // 2)
    return crop_w, crop_h, x, y


def build_vertical_filter(
    source_width: int,
    source_height: int,
    mode: str = "center",
    x_center_frac: float = 0.5,
) -> str:
    crop_w, crop_h, x, y = _crop_geometry(source_width, source_height, x_center_frac)
    return f"crop={crop_w}:{crop_h}:{x}:{y},scale={TARGET_WIDTH}:{TARGET_HEIGHT}"


def detect_face_x_center(video_path: str | Path, sample_count: int = 5) -> float | None:
    """Sample a few frames and return the average detected-face x-center as a
    fraction (0..1) of frame width, or None if no faces were found / OpenCV
    isn't installed. Caller falls back to a plain center crop in that case."""

    try:
        import cv2  # lazy import: optional stretch-goal dependency
    except ImportError:
        return None

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1
    centers: list[float] = []

    for i in range(sample_count):
        frame_idx = int(total_frames * (i + 1) / (sample_count + 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            continue
        # Largest face by area is assumed to be the speaker.
        fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        centers.append((fx + fw / 2) / width)

    cap.release()
    if not centers:
        return None
    return sum(centers) / len(centers)
