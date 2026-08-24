"""Deterministic schema-v2 media packet construction."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from w1_pipeline.hashing import sha256_file

from .hashing import canonical_sha256
from .models import MediaAssetV2, MediaFileV2, MediaManifestV2, PairPacketV2, PairRecordV2


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-") or "asset"
    if cleaned == value and len(cleaned) <= 100:
        return cleaned
    return f"{cleaned[:80]}-{canonical_sha256(value)[:10]}"


def _read_pairs(path: Path) -> List[PairRecordV2]:
    records = [
        PairRecordV2.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != 100 or len({record.pair_id for record in records}) != 100:
        raise ValueError("packet construction requires 100 unique schema-v2 pairs")
    return records


def _symlink_or_copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"media missing: {source}")
    try:
        target.symlink_to(source.resolve())
    except OSError:
        shutil.copy2(source, target)


def _decode_exact_frames(video: Path) -> List[Image.Image]:
    reader = imageio.get_reader(video)
    frames: List[Image.Image] = []
    try:
        for raw in reader:
            array = np.asarray(raw)
            if array.ndim == 2:
                array = np.repeat(array[..., None], 3, axis=2)
            if array.shape[2] == 4:
                array = array[:, :, :3]
            frames.append(Image.fromarray(array.astype(np.uint8)))
    finally:
        reader.close()
    if len(frames) != 16:
        raise ValueError(f"media {video} must decode to exactly 16 frames, got {len(frames)}")
    return frames


def _write_contact_sheet(frames: Iterable[Image.Image], output: Path) -> None:
    images = list(frames)
    if len(images) != 16:
        raise ValueError("contact sheet requires exactly 16 frames")
    canvas = Image.new("RGB", (650, 650), "black")
    for index, frame in enumerate(images):
        resized = frame.convert("RGB").resize((160, 160), Image.Resampling.LANCZOS)
        row, column = divmod(index, 4)
        canvas.paste(resized, (2 + column * 162, 2 + row * 162))
    canvas.save(output, format="JPEG", quality=90, optimize=False, progressive=False)


def _media_file(path: Path) -> MediaFileV2:
    return MediaFileV2(path=str(path.resolve()), sha256=sha256_file(path))


def _build_asset(asset_id: str, original: Path, expected_sha256: str, asset_dir: Path) -> MediaAssetV2:
    if not original.is_file():
        raise FileNotFoundError(f"media missing: {original}")
    actual = sha256_file(original)
    if actual != expected_sha256:
        raise ValueError(f"media checksum mismatch for {asset_id}")
    asset_dir.mkdir(parents=True)
    linked_video = asset_dir / "video.mp4"
    _symlink_or_copy(original, linked_video)
    frames = _decode_exact_frames(original)
    frame_dir = asset_dir / "frames"
    frame_dir.mkdir()
    frame_refs: List[MediaFileV2] = []
    for index, frame in enumerate(frames):
        frame_path = frame_dir / f"frame-{index:03d}.png"
        frame.save(frame_path, format="PNG", optimize=False)
        frame_refs.append(_media_file(frame_path))
    contact_path = asset_dir / "contact-sheet.jpg"
    _write_contact_sheet(frames, contact_path)
    return MediaAssetV2(
        asset_id=asset_id,
        original_path=str(original.resolve()),
        original_sha256=actual,
        video=_media_file(linked_video),
        frames=frame_refs,
        contact_sheet=_media_file(contact_path),
    )


def _build_mask_overlay(mask_paths: List[str], output: Path) -> MediaFileV2 | None:
    if not mask_paths:
        return None
    paths = [Path(path) for path in mask_paths]
    if len(paths) != 16 or not all(path.is_file() for path in paths):
        raise ValueError("mask overlay requires 16 existing mask frames")
    frames = [Image.open(path).convert("RGB") for path in paths]
    try:
        _write_contact_sheet(frames, output)
    finally:
        for frame in frames:
            frame.close()
    return _media_file(output)


def build_packets(pairs_path: Path, output_dir: Path) -> Dict[str, object]:
    """Build shared assets plus pair metadata and return the v2 manifest."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"packet output dir already exists: {output_dir}")
    pairs = _read_pairs(pairs_path)
    output_dir.mkdir(parents=True)

    sources: Dict[str, MediaAssetV2] = {}
    candidates: Dict[str, MediaAssetV2] = {}
    source_root = output_dir / "assets" / "sources"
    candidate_root = output_dir / "assets" / "candidates"
    pair_root = output_dir / "pairs"
    pair_root.mkdir(parents=True)

    for pair in pairs:
        if pair.sample_id not in sources:
            sources[pair.sample_id] = _build_asset(
                pair.sample_id,
                Path(pair.source.video_path),
                pair.source.video_sha256,
                source_root / _safe_slug(pair.sample_id),
            )
        for candidate in (pair.candidate_a, pair.candidate_b):
            if candidate.candidate_id not in candidates:
                candidates[candidate.candidate_id] = _build_asset(
                    candidate.candidate_id,
                    Path(candidate.video_path),
                    candidate.video_sha256,
                    candidate_root / _safe_slug(candidate.candidate_id),
                )

    packets: Dict[str, PairPacketV2] = {}
    for pair in pairs:
        pair_dir = pair_root / _safe_slug(pair.pair_id)
        pair_dir.mkdir()
        mask_ref = _build_mask_overlay(pair.source.mask_frame_paths, pair_dir / "mask-overlay.jpg")
        identity = {
            "schema_version": "2",
            "pair_id": pair.pair_id,
            "source": sources[pair.sample_id].model_dump(mode="json"),
            "candidate_a": candidates[pair.candidate_a.candidate_id].model_dump(mode="json"),
            "candidate_b": candidates[pair.candidate_b.candidate_id].model_dump(mode="json"),
            "mask_overlay": mask_ref.model_dump(mode="json") if mask_ref else None,
        }
        checksum = canonical_sha256(identity)
        metadata_path = pair_dir / "metadata.json"
        metadata = {**identity, "packet_checksum": checksum}
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        packets[pair.pair_id] = PairPacketV2(
            pair_id=pair.pair_id,
            source_asset_id=pair.sample_id,
            candidate_a_asset_id=pair.candidate_a.candidate_id,
            candidate_b_asset_id=pair.candidate_b.candidate_id,
            mask_overlay=mask_ref,
            metadata_path=str(metadata_path.resolve()),
            packet_checksum=checksum,
        )

    manifest = MediaManifestV2(sources=sources, candidates=candidates, pairs=packets)
    payload = manifest.model_dump(mode="json")
    (output_dir / "media-manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload
