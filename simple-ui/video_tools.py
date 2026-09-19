"""Small video helpers for the Extend video feature (PyAV based).

PyAV ships with ComfyUI's requirements, and the UI runs in ComfyUI's venv, so
no external ffmpeg binary is needed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import av
from PIL import Image


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    frames: int
    duration: float  # seconds

    @property
    def aspect(self) -> str:
        if self.width > self.height * 1.15:
            return "Landscape"
        if self.height > self.width * 1.15:
            return "Portrait"
        return "Square"


def _open(path: str | Path) -> av.container.InputContainer:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise RuntimeError("Video file not found or empty.")
    try:
        return av.open(str(p))
    except av.AVError as err:  # pragma: no cover - depends on file
        raise RuntimeError(f"Could not open video: {err}") from err


def _video_stream(container):
    if not container.streams.video:
        raise RuntimeError("That file has no video track.")
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    return stream


def probe_video(path: str | Path) -> VideoInfo:
    """Width, height, fps, frame count and duration (counting frames if needed)."""
    with _open(path) as container:
        stream = _video_stream(container)
        fps = float(stream.average_rate or stream.guessed_rate or stream.base_rate or 0) or 16.0
        frames = int(stream.frames or 0)
        width, height = int(stream.codec_context.width), int(stream.codec_context.height)
        if frames <= 0:
            frames = sum(1 for _ in container.decode(stream))
        duration = frames / fps if fps else 0.0
    return VideoInfo(width=width, height=height, fps=fps, frames=frames, duration=duration)


def extract_last_frame(path: str | Path, dest_dir: Path) -> Path:
    """Save the final frame of the video as a PNG in dest_dir and return its path."""
    last: Image.Image | None = None
    with _open(path) as container:
        stream = _video_stream(container)
        for frame in container.decode(stream):
            last = frame.to_image()
    if last is None:
        raise RuntimeError("Could not read any frames from that video.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"lastframe_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    last.convert("RGB").save(out)
    return out


def _iter_frames(path: str | Path):
    with _open(path) as container:
        stream = _video_stream(container)
        for frame in container.decode(stream):
            yield frame.to_image().convert("RGB")


def _resample(frames: list[Image.Image], src_fps: float, dst_fps: float) -> list[Image.Image]:
    """Re-time a clip to another frame rate by nearest-frame picking (keeps duration)."""
    if not frames or abs(src_fps - dst_fps) < 1e-6:
        return frames
    duration = len(frames) / src_fps
    count = max(1, round(duration * dst_fps))
    return [frames[min(len(frames) - 1, int(i * src_fps / dst_fps))] for i in range(count)]


def concat_videos(
    first: str | Path,
    second: str | Path,
    dest: Path,
    fps: float | None = None,
    second_fps: float | None = None,
) -> Path:
    """Append `second` after `first` into `dest` (H.264 MP4, no audio).

    The output uses the first clip's size and (by default) its frame rate; the
    second clip is resized to match and re-timed so its real-time length is kept.
    """
    info1 = probe_video(first)
    info2 = probe_video(second)
    out_fps = float(fps or info1.fps)
    size = (info1.width, info1.height)

    dest.parent.mkdir(parents=True, exist_ok=True)
    rate = Fraction(out_fps).limit_denominator(1001)
    with av.open(str(dest), mode="w") as out:
        stream = out.add_stream("libx264", rate=rate)
        stream.width, stream.height = size
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "18", "preset": "medium"}

        def write(img: Image.Image) -> None:
            if img.size != size:
                img = img.resize(size, Image.LANCZOS)
            frame = av.VideoFrame.from_image(img)
            for packet in stream.encode(frame):
                out.mux(packet)

        for img in _iter_frames(first):
            write(img)
        tail = _resample(list(_iter_frames(second)), second_fps or info2.fps, out_fps)
        for img in tail:
            write(img)
        for packet in stream.encode():
            out.mux(packet)
    return dest
