"""Cross-platform media executable and metadata helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Union

import imageio.v2 as imageio
import imageio_ffmpeg


def resolve_ffmpeg() -> str:
    """Return an explicit or imageio-bundled ffmpeg executable."""
    configured = os.environ.get("W1_FFMPEG_EXE")
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise FileNotFoundError(f"W1_FFMPEG_EXE does not exist: {path}")
        return str(path)
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg_version(executable: str) -> str:
    proc = subprocess.run([executable, "-version"], capture_output=True, text=True, check=True)
    return proc.stdout.splitlines()[0] if proc.stdout else "unknown"


def probe_video(path: Path) -> Dict[str, Union[int, float]]:
    """Probe a video through ImageIO without requiring a system ffprobe."""
    reader = imageio.get_reader(path)
    try:
        meta = reader.get_meta_data()
        count = reader.count_frames()
        first = reader.get_data(0)
    finally:
        reader.close()
    return {
        "width": int(first.shape[1]),
        "height": int(first.shape[0]),
        "fps": float(meta.get("fps", 0.0)),
        "frames": int(count),
    }
