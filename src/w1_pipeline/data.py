"""DAVIS manifest validation and deterministic W1 preprocessing."""

import json
from pathlib import Path
from typing import List, Sequence, Tuple

import imageio.v2 as imageio
import numpy as np
import yaml
from PIL import Image

from .hashing import combined_file_sha256, sha256_file
from .models import CropParameters, ExperimentSpec, InputRecord


EXPECTED_SEEDS = [101, 202, 303, 404, 505]
EXPECTED_TASK_COUNTS = {"attribute": 4, "object": 3, "local": 3}


def load_spec(path: Path) -> ExperimentSpec:
    with path.open("r", encoding="utf-8") as handle:
        return ExperimentSpec.model_validate(yaml.safe_load(handle))


def validate_spec(spec: ExperimentSpec) -> None:
    if spec.seeds != EXPECTED_SEEDS:
        raise ValueError(f"W1 seeds must be exactly {EXPECTED_SEEDS}")
    if len(spec.inputs) != 10:
        raise ValueError("W1 requires exactly 10 inputs")
    counts = {name: 0 for name in EXPECTED_TASK_COUNTS}
    for item in spec.inputs:
        counts[item.task_type.value] += 1
        text = " ".join([item.sample_id, item.sequence, item.instruction, item.target_caption]).lower()
        if "ivebench" in text:
            raise ValueError("IVEBench is forbidden in the W1 development manifest")
    if counts != EXPECTED_TASK_COUNTS:
        raise ValueError(f"task distribution must be {EXPECTED_TASK_COUNTS}, got {counts}")


def _paths(root: Path, sequence: str) -> Tuple[List[Path], List[Path]]:
    frames = sorted((root / "JPEGImages" / "480p" / sequence).glob("*.jpg"))
    masks = sorted((root / "Annotations" / "480p" / sequence).glob("*.png"))
    if len(frames) != len(masks):
        raise ValueError(f"frame/mask count mismatch for {sequence}: {len(frames)} != {len(masks)}")
    if len(frames) < 48:
        raise ValueError(f"{sequence} has {len(frames)} frames; at least 48 required")
    if [p.stem for p in frames] != [p.stem for p in masks]:
        raise ValueError(f"frame/mask names are not aligned for {sequence}")
    return frames, masks


def _mask_area(path: Path) -> int:
    return int(np.count_nonzero(np.asarray(Image.open(path))))


def _best_window(masks: Sequence[Path]) -> int:
    areas = [_mask_area(path) for path in masks]
    window = sum(areas[:48])
    best_start, best_score = 0, window
    for start in range(1, len(areas) - 47):
        window += areas[start + 47] - areas[start - 1]
        if window > best_score:
            best_start, best_score = start, window
    if best_score <= 0:
        raise ValueError("selected object mask is empty in every possible window")
    return best_start


def _square_crop(masks: Sequence[Path]) -> Tuple[int, int, int]:
    first = np.asarray(Image.open(masks[0]))
    height, width = first.shape[:2]
    xs: List[int] = []
    ys: List[int] = []
    for path in masks:
        mask = np.asarray(Image.open(path))
        if mask.shape[:2] != (height, width):
            raise ValueError("mask dimensions are inconsistent")
        y, x = np.nonzero(mask)
        xs.extend((int(x.min()), int(x.max())))
        ys.extend((int(y.min()), int(y.max())))
    box_w, box_h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    side = min(max(1, int(np.ceil(max(box_w, box_h) * 1.25))), width, height)
    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2
    x0 = min(max(0, int(round(center_x - side / 2))), width - side)
    y0 = min(max(0, int(round(center_y - side / 2))), height - side)
    return x0, y0, side


def _prepare_one(root: Path, output_dir: Path, spec: ExperimentSpec, item) -> InputRecord:
    source_paths, mask_paths = _paths(root, item.sequence)
    start = _best_window(mask_paths)
    indices = [start + offset for offset in range(0, 48, 3)]
    selected_sources = [source_paths[index] for index in indices]
    selected_masks = [mask_paths[index] for index in indices]
    x, y, side = _square_crop(selected_masks)

    sample_dir = output_dir / item.sample_id
    frame_dir, mask_dir = sample_dir / "frames", sample_dir / "masks"
    frame_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    prepared_frames: List[Path] = []
    prepared_masks: List[Path] = []
    for index, (source_path, mask_path) in enumerate(zip(selected_sources, selected_masks)):
        frame = Image.open(source_path).convert("RGB").crop((x, y, x + side, y + side)).resize((512, 512), Image.Resampling.LANCZOS)
        mask = Image.open(mask_path).crop((x, y, x + side, y + side)).resize((512, 512), Image.Resampling.NEAREST)
        frame_out, mask_out = frame_dir / f"{index:05d}.png", mask_dir / f"{index:05d}.png"
        frame.save(frame_out)
        mask.save(mask_out)
        prepared_frames.append(frame_out)
        prepared_masks.append(mask_out)

    video_path = sample_dir / "source.mp4"
    with imageio.get_writer(video_path, fps=8, codec="libx264", quality=8, macro_block_size=None) as writer:
        for path in prepared_frames:
            writer.append_data(np.asarray(Image.open(path)))

    return InputRecord(
        sample_id=item.sample_id,
        dataset=spec.dataset,
        split=spec.split,
        sequence=item.sequence,
        task_type=item.task_type,
        instruction=item.instruction,
        target_caption=item.target_caption,
        source_frame_paths=[str(path.resolve()) for path in prepared_frames],
        mask_frame_paths=[str(path.resolve()) for path in prepared_masks],
        source_video_path=str(video_path.resolve()),
        source_checksum=combined_file_sha256(prepared_frames),
        mask_checksum=combined_file_sha256(prepared_masks),
        video_checksum=sha256_file(video_path),
        crop=CropParameters(x=x, y=y, side=side, window_start=start),
    )


def prepare_dataset(spec: ExperimentSpec, davis_root: Path, output_dir: Path) -> List[InputRecord]:
    validate_spec(spec)
    records = [_prepare_one(davis_root, output_dir, spec, item) for item in spec.inputs]
    manifest_path = output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps([record.model_dump(mode="json") for record in records], indent=2), encoding="utf-8")
    temp_path.replace(manifest_path)
    return records


def validate_prepared_manifest(path: Path) -> List[InputRecord]:
    records = [InputRecord.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
    if len(records) != 10 or len({record.sample_id for record in records}) != 10:
        raise ValueError("prepared W1 manifest must contain 10 unique inputs")
    for record in records:
        source_paths = [Path(value) for value in record.source_frame_paths]
        mask_paths = [Path(value) for value in record.mask_frame_paths]
        if not all(path.is_file() for path in source_paths + mask_paths + [Path(record.source_video_path)]):
            raise ValueError(f"prepared files missing for {record.sample_id}")
        if combined_file_sha256(source_paths) != record.source_checksum:
            raise ValueError(f"source checksum mismatch for {record.sample_id}")
        if combined_file_sha256(mask_paths) != record.mask_checksum:
            raise ValueError(f"mask checksum mismatch for {record.sample_id}")
    return records

