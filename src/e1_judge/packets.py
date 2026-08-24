"""E1 media packet construction: symlinks + contact sheets + metadata."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .hashing import canonical_sha256


def _read_pairs(pairs_path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in Path(pairs_path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _symlink_or_copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"media missing: {source}")
    if target.exists() or target.is_symlink():
        return
    try:
        target.symlink_to(source)
    except OSError:
        shutil.copy2(source, target)


def _contact_sheet(video_path: Path, out_jpg: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", "scale=160:160:flags=lanczos,tile=4x4:padding=2:margin=2",
            "-frames:v", "1", str(out_jpg),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _mask_overlay(source_mask: Path, out_jpg: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(source_mask), "-frames:v", "1", str(out_jpg)],
        capture_output=True,
        text=True,
        check=True,
    )


def build_packets(pairs_path: Path, output_dir: Path) -> List[dict]:
    """Create one directory per pair with symlinked media and contact sheets."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"packet output dir already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    pairs = _read_pairs(pairs_path)
    metadata_records: List[dict] = []

    for pair in pairs:
        pair_dir = output_dir / pair["pair_id"]
        pair_dir.mkdir()

        source = Path(pair["source_video_path"])
        candidate_a = Path(pair["candidate_left_path"])
        candidate_b = Path(pair["candidate_right_path"])

        _symlink_or_copy(source, pair_dir / "source.mp4")
        _symlink_or_copy(candidate_a, pair_dir / "candidate-a.mp4")
        _symlink_or_copy(candidate_b, pair_dir / "candidate-b.mp4")

        _contact_sheet(source, pair_dir / "source-contact.jpg")
        _contact_sheet(candidate_a, pair_dir / "candidate-a-contact.jpg")
        _contact_sheet(candidate_b, pair_dir / "candidate-b-contact.jpg")

        mask_paths = pair.get("mask_paths") or []
        mask_available = bool(mask_paths) and Path(mask_paths[0]).is_file()
        if mask_available:
            _mask_overlay(Path(mask_paths[0]), pair_dir / "mask-overlay.jpg")
        else:
            (pair_dir / "mask-overlay.jpg").write_bytes(b"")

        metadata = {
            "pair_id": pair["pair_id"],
            "sample_id": pair["sample_id"],
            "task_type": pair["task_type"],
            "instruction": pair["instruction"],
            "target_caption": pair["target_caption"],
            "source_video_path": str(source),
            "source_checksum": pair["source_checksum"],
            "candidate_a_path": str(candidate_a),
            "candidate_a_checksum": pair["candidate_left_checksum"],
            "candidate_b_path": str(candidate_b),
            "candidate_b_checksum": pair["candidate_right_checksum"],
            "mask_available": mask_available,
            "packet_checksum": canonical_sha256(
                {
                    "source": pair["source_checksum"],
                    "a": pair["candidate_left_checksum"],
                    "b": pair["candidate_right_checksum"],
                }
            ),
        }
        (pair_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        metadata_records.append(metadata)

    return metadata_records
