"""Deterministic CPU-only F/P/T/Q metrics for the Defense MVP."""

from __future__ import annotations

import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .config import load_config
from .io import rename_noreplace, write_json
from .models import (
    ColorRuleV1, DefenseConfigV1, PackageCandidateV1, PackageSampleV1,
    validate_relative_path,
)


METRIC_PROTOCOL = "cpu-fptq-v1"
DIMENSIONS = ("F", "P", "T", "Q")


def _finite_float(value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("metric calculation produced a non-finite value")
    return result


def _clipped(value: float) -> float:
    return _finite_float(np.clip(value, 0.0, 1.0))


def _masked_per_frame(values: np.ndarray, masks: np.ndarray) -> np.ndarray:
    if values.shape != masks.shape:
        raise ValueError("masked metric values/masks shape mismatch")
    denominator = masks.sum(axis=(1, 2), dtype=np.float64)
    if np.any(denominator <= 0):
        raise ValueError("masked metric encountered an empty mask")
    numerator = (values * masks).sum(axis=(1, 2), dtype=np.float64)
    return (numerator / denominator).astype(np.float64)


def _target_color(rgb: np.ndarray, rule: ColorRuleV1) -> np.ndarray:
    frames = []
    for frame in rgb:
        uint8 = np.clip(np.rint(frame * 255.0), 0, 255).astype(np.uint8)
        hsv = np.asarray(Image.fromarray(uint8).convert("HSV"), dtype=np.float32) / 255.0
        hue, saturation, value = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        hue_match = np.zeros(hue.shape, dtype=bool)
        for low, high in rule.hue_ranges:
            hue_match |= (hue >= low) & (hue <= high)
        frames.append(
            hue_match
            & (saturation >= rule.saturation_min)
            & (saturation <= rule.saturation_max)
            & (value >= rule.value_min)
            & (value <= rule.value_max)
        )
    return np.stack(frames, axis=0)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return (
        rgb[..., 0] * np.float32(0.299)
        + rgb[..., 1] * np.float32(0.587)
        + rgb[..., 2] * np.float32(0.114)
    )


def _gradient_energy(luma: np.ndarray) -> np.ndarray:
    horizontal = np.abs(np.diff(luma, axis=2)).mean(axis=(1, 2), dtype=np.float64)
    vertical = np.abs(np.diff(luma, axis=1)).mean(axis=(1, 2), dtype=np.float64)
    return horizontal + vertical


def score_arrays(
    source: np.ndarray, candidate: np.ndarray, masks: np.ndarray,
    rule: ColorRuleV1, cfg: DefenseConfigV1,
) -> Dict[str, Any]:
    """Score aligned RGB arrays and binary masks without filesystem side effects."""
    source = np.asarray(source, dtype=np.float32)
    candidate = np.asarray(candidate, dtype=np.float32)
    masks = np.asarray(masks, dtype=bool)
    if source.shape != candidate.shape or source.ndim != 4 or source.shape[-1] != 3:
        raise ValueError("source/candidate arrays must be aligned T×H×W×3")
    if masks.shape != source.shape[:3] or source.shape[0] < 2:
        raise ValueError("mask shape or frame count is invalid")
    if np.any(source < 0) or np.any(source > 1) or np.any(candidate < 0) or np.any(candidate > 1):
        raise ValueError("RGB arrays must be in float32 [0,1]")

    fractions = masks.mean(axis=(1, 2), dtype=np.float64)
    if np.any(fractions < cfg.min_mask_fraction) or np.any(fractions > cfg.max_mask_fraction):
        raise ValueError("mask fraction falls outside the frozen protocol")
    outside = ~masks

    pixel_edit = np.abs(candidate - source).mean(axis=3, dtype=np.float32)
    edit_per_frame = _masked_per_frame(pixel_edit, masks)
    candidate_target = _target_color(candidate, rule)
    if rule.require_new_color:
        source_target = _target_color(source, rule)
        color_evidence = candidate_target & ~source_target
    else:
        color_evidence = candidate_target
    color_per_frame = _masked_per_frame(color_evidence.astype(np.float32), masks)
    edit_strength = _clipped(float(edit_per_frame.mean()))
    color_support = _clipped(float(color_per_frame.mean()))
    faithfulness = _clipped(math.sqrt(edit_strength * color_support))

    preservation_per_frame = 1.0 - _masked_per_frame(pixel_edit, outside)
    preservation = _clipped(float(preservation_per_frame.mean()))

    residual = candidate - source
    residual_change = np.abs(residual[1:] - residual[:-1]).mean(axis=3, dtype=np.float32)
    pair_inside = masks[1:] | masks[:-1]
    temporal_full_pairs = 1.0 - residual_change.mean(axis=(1, 2), dtype=np.float64)
    temporal_inside_pairs = 1.0 - _masked_per_frame(residual_change, pair_inside)
    temporal_outside_pairs = 1.0 - _masked_per_frame(residual_change, ~pair_inside)
    temporal = _clipped(float(temporal_full_pairs.mean()))

    source_luma, candidate_luma = _luma(source), _luma(candidate)
    source_gradient = _gradient_energy(source_luma)
    candidate_gradient = _gradient_energy(candidate_luma)
    epsilon = 1e-8
    gradient_ratio = candidate_gradient / np.maximum(source_gradient, epsilon)
    reciprocal = source_gradient / np.maximum(candidate_gradient, epsilon)
    gradient_retention = np.minimum(gradient_ratio, reciprocal)
    gradient_retention[(source_gradient <= epsilon) & (candidate_gradient <= epsilon)] = 1.0
    gradient_retention = np.clip(gradient_retention, 0.0, 1.0)
    exposure_good = 1.0 - (
        (candidate_luma < cfg.exposure_low) | (candidate_luma > cfg.exposure_high)
    ).mean(axis=(1, 2), dtype=np.float64)
    brightness_residual = (candidate_luma - source_luma).mean(axis=(1, 2), dtype=np.float64)
    brightness_delta = np.concatenate((np.zeros(1), np.abs(np.diff(brightness_residual))))
    brightness_stability = np.clip(
        1.0 - brightness_delta / cfg.brightness_flicker_scale, 0.0, 1.0
    )
    quality_per_frame = np.cbrt(
        np.clip(gradient_retention, 0.0, 1.0)
        * np.clip(exposure_good, 0.0, 1.0)
        * brightness_stability
    )
    quality = _clipped(float(np.cbrt(
        float(gradient_retention.mean())
        * float(exposure_good.mean())
        * float(brightness_stability.mean())
    )))
    abnormal = (
        (exposure_good < 1.0 - cfg.abnormal_exposure_fraction)
        | (gradient_ratio < cfg.abnormal_gradient_ratio_min)
        | (gradient_ratio > cfg.abnormal_gradient_ratio_max)
        | (brightness_delta > cfg.abnormal_brightness_delta)
    )

    result = {
        "scores": {"F": faithfulness, "P": preservation, "T": temporal, "Q": quality},
        "components": {
            "edit_strength": edit_strength,
            "target_color_support": color_support,
            "target_color_pixel_hits": int((color_evidence & masks).sum()),
            "temporal_inside": _clipped(float(temporal_inside_pairs.mean())),
            "temporal_outside": _clipped(float(temporal_outside_pairs.mean())),
            "temporal_full": temporal,
            "gradient_retention": _clipped(float(gradient_retention.mean())),
            "exposure_good": _clipped(float(exposure_good.mean())),
            "brightness_stability": _clipped(float(brightness_stability.mean())),
            "abnormal_frame_count": int(abnormal.sum()),
            "mask_fraction_mean": _finite_float(float(fractions.mean())),
            "mask_fraction_min": _finite_float(float(fractions.min())),
            "mask_fraction_max": _finite_float(float(fractions.max())),
        },
        "per_frame": {
            "edit_strength": [_finite_float(value) for value in edit_per_frame],
            "target_color_support": [_finite_float(value) for value in color_per_frame],
            "preservation": [_clipped(value) for value in preservation_per_frame],
            "temporal_full": [1.0] + [_clipped(value) for value in temporal_full_pairs],
            "temporal_inside": [1.0] + [_clipped(value) for value in temporal_inside_pairs],
            "temporal_outside": [1.0] + [_clipped(value) for value in temporal_outside_pairs],
            "gradient_energy_source": [_finite_float(value) for value in source_gradient],
            "gradient_energy_candidate": [_finite_float(value) for value in candidate_gradient],
            "gradient_ratio": [_finite_float(value) for value in gradient_ratio],
            "gradient_retention": [_clipped(value) for value in gradient_retention],
            "exposure_good": [_clipped(value) for value in exposure_good],
            "brightness_residual_delta": [_finite_float(value) for value in brightness_delta],
            "brightness_stability": [_clipped(value) for value in brightness_stability],
            "quality": [_clipped(value) for value in quality_per_frame],
        },
    }
    if any(not 0.0 <= result["scores"][key] <= 1.0 for key in DIMENSIONS):
        raise ValueError("one or more scores are outside [0,1]")
    return result


def _package_file(root: Path, relative: str, expected_sha256: str) -> Path:
    relative = validate_relative_path(relative)
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"metric input is missing or not regular: {relative}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"metric input escapes delivery root: {relative}") from exc
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"metric input checksum mismatch: {relative}")
    return path


def _load_rgb_frames(root: Path, relative_paths: Sequence[str], hashes: Sequence[str]) -> np.ndarray:
    frames = []
    for relative, digest in zip(relative_paths, hashes):
        path = _package_file(root, relative, digest)
        with Image.open(path) as image:
            image.load()
            if image.size != (512, 512) or image.mode != "RGB":
                raise ValueError(f"RGB frame must be 512x512 RGB: {relative}")
            frames.append(np.asarray(image, dtype=np.float32) / np.float32(255.0))
    return np.stack(frames, axis=0)


def _load_masks(
    root: Path, relative_paths: Sequence[str], hashes: Sequence[str], decode: str
) -> np.ndarray:
    if decode != "index-nonzero-v1":
        raise ValueError(f"unsupported mask decode protocol: {decode}")
    frames = []
    for relative, digest in zip(relative_paths, hashes):
        path = _package_file(root, relative, digest)
        with Image.open(path) as image:
            image.load()
            if image.size != (512, 512):
                raise ValueError(f"mask frame must be 512x512: {relative}")
            if image.mode not in {"1", "L", "P", "I", "I;16"}:
                raise ValueError(f"mask must be an indexed/integer single-channel image: {relative}")
            raw = np.asarray(image)
            if raw.ndim != 2 or raw.dtype.kind not in {"b", "i", "u"}:
                raise ValueError(f"mask pixels must be a 2D integer index array: {relative}")
            frames.append(raw != 0)
    return np.stack(frames, axis=0)


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_sums(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    rows = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "METRICS_SHA256SUMS").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )


def score_ingest(
    ingest_manifest: Path, config_path: Path, output: Path
) -> Dict[str, Any]:
    ingest_manifest, config_path, output = (
        Path(ingest_manifest).resolve(), Path(config_path).resolve(), Path(output).resolve()
    )
    if os.path.lexists(output):
        raise FileExistsError(f"metrics output already exists: {output}")
    cfg = load_config(config_path)
    if cfg.metric_protocol != METRIC_PROTOCOL:
        raise ValueError("unsupported metric protocol")
    payload = json.loads(ingest_manifest.read_text(encoding="utf-8"))
    if payload.get("experiment_id") != "DEFENSE-MVP-v01" or payload.get("schema_version") != "1":
        raise ValueError("normalized ingest manifest identity mismatch")
    samples = [PackageSampleV1.model_validate(item) for item in payload.get("samples", [])]
    candidates = [PackageCandidateV1.model_validate(item) for item in payload.get("candidates", [])]
    if [item.sample_id for item in samples] != cfg.sample_ids or len(candidates) != 50:
        raise ValueError("normalized ingest sample/candidate matrix is incomplete")
    expected_pairs = [
        (sample_id, seed) for sample_id in cfg.sample_ids for seed in cfg.seeds
    ]
    if [(item.sample_id, item.seed) for item in candidates] != expected_pairs:
        raise ValueError("normalized ingest candidate matrix/order drifted")
    delivery_root = Path(payload["delivery_root"]).resolve()
    if not delivery_root.is_dir():
        raise ValueError("normalized ingest delivery root is unavailable")

    output.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging = output.parent / f".{output.name}.score-{token}.staging"
    failed = output.parent / f".{output.name}.score-{token}.failed"
    staging.mkdir()
    started = time.perf_counter()
    runtimes = []
    try:
        sample_by_id = {item.sample_id: item for item in samples}
        source_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        for sample in samples:
            _package_file(delivery_root, sample.source_video.relative_path, sample.source_video.sha256)
            if sample.sample_id in cfg.primary_sample_ids:
                source_cache[sample.sample_id] = (
                    _load_rgb_frames(
                        delivery_root, sample.source_frames.relative_paths, sample.source_frames.sha256
                    ),
                    _load_masks(
                        delivery_root, sample.masks.relative_paths, sample.masks.sha256,
                        cfg.mask_decode,
                    ),
                )
            else:
                _load_rgb_frames(
                    delivery_root, sample.source_frames.relative_paths, sample.source_frames.sha256
                )
                _load_masks(
                    delivery_root, sample.masks.relative_paths, sample.masks.sha256,
                    cfg.mask_decode,
                )

        records = []
        for candidate in candidates:
            candidate_started = time.perf_counter()
            _package_file(delivery_root, candidate.video.relative_path, candidate.video.sha256)
            base = {
                "schema_version": "1", "metric_protocol": METRIC_PROTOCOL,
                "candidate_id": candidate.candidate_id, "sample_id": candidate.sample_id,
                "seed": candidate.seed, "candidate_video_sha256": candidate.video.sha256,
                "historical_generation_runtime_seconds": candidate.runtime_seconds,
                "historical_peak_vram_mb": candidate.peak_vram_mb,
            }
            if candidate.sample_id not in cfg.primary_sample_ids:
                _load_rgb_frames(
                    delivery_root, candidate.frames.relative_paths, candidate.frames.sha256
                )
                record = {
                    **base, "measurement_status": "qualitative_only", "scores": None,
                    "components": None, "per_frame": None,
                    "reason": "object-transformation-outside-cpu-color-proxy-boundary",
                }
            else:
                source, masks = source_cache[candidate.sample_id]
                candidate_frames = _load_rgb_frames(
                    delivery_root, candidate.frames.relative_paths, candidate.frames.sha256
                )
                measured = score_arrays(
                    source, candidate_frames, masks,
                    cfg.color_rules[candidate.sample_id], cfg,
                )
                record = {**base, "measurement_status": "scored", **measured}
            records.append(record)
            runtimes.append({
                "candidate_id": candidate.candidate_id,
                "cpu_seconds": time.perf_counter() - candidate_started,
            })

        metrics_path = staging / "metrics.jsonl"
        _write_jsonl(metrics_path, records)
        scored = [row for row in records if row["measurement_status"] == "scored"]
        qualitative = [row for row in records if row["measurement_status"] == "qualitative_only"]
        summary = {
            "schema_version": "1", "metric_protocol": METRIC_PROTOCOL,
            "status": "passed", "records": len(records), "scored": len(scored),
            "qualitative_only": len(qualitative),
            "score_ranges": {
                dimension: {
                    "min": min(row["scores"][dimension] for row in scored),
                    "mean": sum(row["scores"][dimension] for row in scored) / len(scored),
                    "max": max(row["scores"][dimension] for row in scored),
                }
                for dimension in DIMENSIONS
            },
            "metrics_sha256": sha256_file(metrics_path),
        }
        write_json(staging / "metrics-summary.json", summary)
        protocol = {
            "metric_protocol": METRIC_PROTOCOL,
            "dimensions": list(DIMENSIONS),
            "faithfulness": "sqrt(masked_rgb_mae * masked_target_color_support)",
            "preservation": "1 - outside_mask_rgb_mae",
            "temporal": "1 - adjacent_edit_residual_mae",
            "quality": "geomean(gradient_retention, exposure_good, brightness_stability)",
            "luma": [0.299, 0.587, 0.114],
            "mask_decode": cfg.mask_decode,
            "candidate_count": 50, "scored_candidate_count": 35,
        }
        lock = {
            "schema_version": "1", "experiment_id": "DEFENSE-MVP-v01",
            "config_sha256": sha256_file(config_path),
            "ingest_manifest_sha256": sha256_file(ingest_manifest),
            "package_manifest_sha256": payload["package_manifest_sha256"],
            "protocol": protocol,
            "protocol_sha256": canonical_sha256(protocol),
        }
        write_json(staging / "metrics-config-lock.json", lock)
        elapsed = time.perf_counter() - started
        write_json(staging / "scoring-runtime.json", {
            "schema_version": "1", "cpu_only": True,
            "candidate_seconds": runtimes, "total_cpu_seconds": elapsed,
        })
        receipt = {
            "schema_version": "1", "status": "passed", "ready_for_design": True,
            "metrics_sha256": summary["metrics_sha256"],
            "config_sha256": lock["config_sha256"],
            "ingest_manifest_sha256": lock["ingest_manifest_sha256"],
            "records": 50, "scored": 35, "qualitative_only": 15,
            "total_cpu_seconds": elapsed,
        }
        write_json(staging / "score-receipt.json", receipt)
        _write_sums(staging)
        rename_noreplace(staging, output)
        return receipt
    except Exception as exc:
        if staging.exists():
            write_json(staging / "SCORING_FAILED.json", {
                "status": "failed", "error": str(exc),
            })
            rename_noreplace(staging, failed)
        raise
