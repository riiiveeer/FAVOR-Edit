"""Lossless, audited browser presentation copies; original videos stay immutable."""

from __future__ import annotations

import json
import subprocess
import time
from fractions import Fraction
from pathlib import Path

import imageio_ffmpeg

from w1_pipeline.hashing import sha256_file

from .ingest import _package_file
from .io import write_json

PRESENTATION = "lossless-vp9-yuv420p-v1"


def decoded_signature(executable: str, path: Path) -> dict:
    command = [executable, "-v", "error", "-threads", "1", "-i", str(path), "-map", "0:v:0",
               "-an", "-pix_fmt", "rgb24", "-fps_mode", "passthrough", "-f", "framehash", "-hash", "sha256", "-"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    dimensions, timebase, frames = None, None, []
    for line in result.stdout.splitlines():
        if line.startswith("#dimensions 0:"):
            dimensions = line.split(":", 1)[1].strip()
        elif line.startswith("#tb 0:"):
            timebase = Fraction(line.split(":", 1)[1].strip())
        elif line and not line.startswith("#"):
            stream, dts, pts, duration, size, digest = [s.strip() for s in line.split(",")]
            frames.append({"pts_seconds": str(int(pts) * timebase),
                           "duration_seconds": str(int(duration) * timebase),
                           "size": int(size), "sha256": digest})
    if not frames or dimensions is None:
        raise ValueError("presentation decode produced no frames")
    return {"pixel_format": "rgb24", "dimensions": dimensions, "frames": frames}


def comparison_refs(data: dict) -> dict:
    refs = {}
    for c in data["comparisons"]:
        for ref in (c["source_video"], c["candidate_x"]["video"], c["candidate_y"]["video"]):
            refs[ref["relative_path"]] = ref["sha256"]
    return refs


def create_presentation(data: dict, staging: Path, fixture_native: bool) -> dict:
    refs = comparison_refs(data)
    if fixture_native:
        return {"presentation_mode": "fixture-native-v1",
                "presentation_media": {p: {"relative_path": p, "sha256": h} for p, h in refs.items()},
                "presentation_proof_sha256": None}
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    started = time.perf_counter()
    (staging / "presentation").mkdir()
    media, proofs, cache = {}, [], {}
    for relative, original_sha in sorted(refs.items()):
        source = _package_file(Path(data["delivery_root"]), relative)
        if sha256_file(source) != original_sha:
            raise ValueError("original media changed before presentation")
        target = staging / "presentation" / f"{original_sha}.webm"
        if original_sha not in cache:
            before = decoded_signature(executable, source)
            if (before["dimensions"] != "512x512" or len(before["frames"]) != 16
                    or [f["pts_seconds"] for f in before["frames"]] != [str(Fraction(i, 8)) for i in range(16)]
                    or any(f["duration_seconds"] != "1/8" for f in before["frames"])):
                raise ValueError("presentation expects unchanged 512x512, 16 frames, 8fps timing")
            command = [executable, "-v", "error", "-n", "-threads", "1", "-i", str(source),
                       "-map", "0:v:0", "-an", "-sn", "-dn", "-map_metadata", "-1",
                       "-c:v", "libvpx-vp9", "-lossless", "1", "-pix_fmt", "yuv420p",
                       "-cpu-used", "4", "-row-mt", "0", "-threads", "2",
                       "-fps_mode", "passthrough", str(target)]
            subprocess.run(command, capture_output=True, text=True, check=True)
            after = decoded_signature(executable, target)
            if before != after or sha256_file(source) != original_sha:
                raise ValueError("presentation is not pixel/time equivalent to original")
            cache[original_sha] = {"signature": before, "command": command,
                                   "video": {"relative_path": target.relative_to(staging).as_posix(), "sha256": sha256_file(target)}}
        item = cache[original_sha]
        media[relative] = item["video"]
        proofs.append({"original_relative_path": relative, "original_sha256": original_sha,
                       "presentation": item["video"], "equivalence": "exact-rgb24-frame-hashes-and-timestamps",
                       "decoded_signature": item["signature"], "command": item["command"]})
    write_json(staging / "presentation-proof.json", {
        "protocol": PRESENTATION, "ffmpeg_sha256": sha256_file(Path(executable)),
        "ffmpeg_version": subprocess.check_output([executable, "-version"], text=True).splitlines()[0],
        "elapsed_seconds": time.perf_counter() - started, "media": proofs,
    })
    return {"presentation_mode": PRESENTATION, "presentation_media": media,
            "presentation_proof_sha256": sha256_file(staging / "presentation-proof.json")}
