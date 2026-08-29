"""Read-only verification of the complete E1 phase-3 preparation bundle."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from w1_pipeline.hashing import sha256_file

from .hashing import canonical_sha256
from .models import (
    JudgeRequestV2,
    MediaAssetV2,
    MediaManifestV2,
    PairRecordV2,
    RuntimeConfigV2,
    load_runtime_config,
    validate_config,
)
from .prompts import load_prompt, render_prompt
from .runner import judge_key, runtime_fingerprint

EXPECTED_MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"
EXPECTED_MODEL_REVISION = "a22b9b202f87d21defc75df2652beed712e52261"
EXPECTED_MODEL_PATH = "/DATA/DATA4/hfy/models/Qwen2.5-VL-7B-Instruct-a22b9b2"
EXPECTED_ADAPTER_PYTHON = "/DATA/DATA4/hfy/envs/e1-judge-qwen25-vl/bin/python"
EXPECTED_ADAPTER_SCRIPT = "/home/sunyinan/FAVOR-Edit/scripts/e1_judge_qwen25_vl.py"

EXPECTED_DEV_SAMPLES = ["bear-white", "dog-tiger", "hiker-backpack"]
EXPECTED_FROZEN_SAMPLES = [
    "bus-red",
    "elephant-pink",
    "classic-car-blue",
    "horse-zebra",
    "mallard-swan",
    "rider-helmet",
    "car-headlights",
]
EXPECTED_METHODS = {
    "absolute-v1": {"requests": 50, "prompt": "prompt-absolute-v1.yaml", "swap": False},
    "pairwise-single-v1": {
        "requests": 100,
        "prompt": "prompt-pairwise-single-v1.yaml",
        "swap": False,
    },
    "pairwise-swap-v1": {
        "requests": 200,
        "prompt": "prompt-pairwise-swap-v1.yaml",
        "swap": True,
    },
    "rubric-swap-v1": {
        "requests": 200,
        "prompt": "prompt-rubric-swap-v1.yaml",
        "swap": True,
    },
}
EXPECTED_METHOD_SPLIT_COUNTS = {
    "absolute-v1": {"dev": 15, "frozen-eval": 35},
    "pairwise-single-v1": {"dev": 30, "frozen-eval": 70},
    "pairwise-swap-v1": {"dev": 60, "frozen-eval": 140},
    "rubric-swap-v1": {"dev": 60, "frozen-eval": 140},
}
EXPECTED_PROMPT_CHECKSUMS = {
    "absolute-v1": "7f6904467f0263bb7ba54bf1613e69120d0fabe39e978e1907d186dbe0a6653f",
    "pairwise-single-v1": "9fe3d4bb3b535d8d1e2803741ef7a7d559274d0cddc126e04282f8288fead8b5",
    "pairwise-swap-v1": "da9a25b99c65202de97c3bc414d85daaba99ca9a9941bb223a8f47031f4d813d",
    "rubric-swap-v1": "973180e6f73c819e976abf1d3318db71f73106a8bfd4a20b9b2aa03e1e75b9d9",
}
EXPECTED_GENERATION = {
    "absolute-v1": {
        "do_sample": False,
        "max_new_tokens": 384,
        "max_pixels": 65536,
        "fps": 8.0,
    },
    "pairwise-single-v1": {
        "do_sample": False,
        "max_new_tokens": 256,
        "max_pixels": 65536,
        "fps": 8.0,
    },
    "pairwise-swap-v1": {
        "do_sample": False,
        "max_new_tokens": 256,
        "max_pixels": 65536,
        "fps": 8.0,
    },
    "rubric-swap-v1": {
        "do_sample": False,
        "max_new_tokens": 768,
        "max_pixels": 65536,
        "fps": 8.0,
    },
}
HEX40 = re.compile(r"^[0-9a-f]{40}(?:\+dirty)?$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _absolute_lexical(path: Path | str) -> Path:
    """Return an absolute normalized path without resolving symlinks."""
    return Path(os.path.abspath(os.fspath(path)))


@dataclass(frozen=True)
class PreparationPathMapping:
    """Map final declared paths to their pre-publication staging locations."""

    declared_root: Path
    physical_root: Path

    def __post_init__(self) -> None:
        declared = _absolute_lexical(self.declared_root)
        physical = _absolute_lexical(self.physical_root)
        if declared == physical:
            raise ValueError("declared and physical preparation roots must differ")
        object.__setattr__(self, "declared_root", declared)
        object.__setattr__(self, "physical_root", physical)

    def physical_path(self, declared_path: Path | str) -> Path:
        path = _absolute_lexical(declared_path)
        try:
            relative = path.relative_to(self.declared_root)
        except ValueError:
            return path
        return self.physical_root / relative

    def declared_path(self, physical_path: Path | str) -> Path:
        path = _absolute_lexical(physical_path)
        try:
            relative = path.relative_to(self.physical_root)
        except ValueError:
            return path
        return self.declared_root / relative


class PreparationVerificationError(ValueError):
    """Raised after a failed report has been assembled and optionally published."""

    def __init__(self, report: dict):
        self.report = report
        failures = report.get("failures", [])
        summary = "; ".join(
            f"{item['check_id']}: {item['summary']}" for item in failures[:5]
        )
        if len(failures) > 5:
            summary += f"; and {len(failures) - 5} more failed checks"
        super().__init__(summary or "preparation verification failed")


class _Collector:
    def __init__(self) -> None:
        self.checks: List[dict] = []
        self.failures: List[dict] = []
        self.warnings: List[str] = []

    def record(
        self,
        check_id: str,
        errors: Iterable[str],
        passed_summary: str,
        details: Optional[dict] = None,
    ) -> None:
        error_list = list(errors)
        entry = {
            "check_id": check_id,
            "status": "failed" if error_list else "passed",
            "summary": error_list[0] if error_list else passed_summary,
        }
        if details:
            entry["details"] = details
        if error_list:
            entry["errors"] = error_list
            self.failures.append(
                {"check_id": check_id, "summary": error_list[0], "errors": error_list}
            )
        self.checks.append(entry)

    def failed(self, check_id: str, error: Exception | str) -> None:
        self.record(check_id, [str(error)], "")

    def skipped(self, check_id: str, reason: str) -> None:
        self.checks.append(
            {"check_id": check_id, "status": "skipped", "summary": reason}
        )


def _atomic_write_new_json(path: Path, payload: dict) -> None:
    """Atomically publish a new JSON file without ever replacing an existing path."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"verification output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise FileExistsError(f"verification output already exists: {path}") from exc
    finally:
        if temporary.exists():
            temporary.unlink()


def _jsonl_models(path: Path, model) -> List[Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate(json.loads(line)))
        except Exception as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return records


def _input_descriptor(
    path: Path,
    path_mapping: Optional[PreparationPathMapping] = None,
) -> dict:
    path = Path(path)
    reported_path = path_mapping.declared_path(path) if path_mapping else path.resolve()
    return {
        "path": str(reported_path),
        "sha256": sha256_file(path) if path.is_file() else None,
    }


def _same_path(left: str, right: str) -> bool:
    return Path(left).resolve(strict=False) == Path(right).resolve(strict=False)


def _verify_config_runtime(
    config_path: Path,
    runtime_path: Path,
    collector: _Collector,
) -> Tuple[Optional[dict], Optional[RuntimeConfigV2], Dict[str, Tuple[Any, str]]]:
    cfg: Optional[dict] = None
    runtime: Optional[RuntimeConfigV2] = None
    prompts: Dict[str, Tuple[Any, str]] = {}

    config_errors: List[str] = []
    try:
        cfg = validate_config(config_path)
    except Exception as exc:
        config_errors.append(f"config schema validation failed: {exc}")
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            cfg = raw if isinstance(raw, dict) else None
        except Exception:
            cfg = None
    if cfg is not None:
        expected_fields = {
            "protocol_schema_version": "2",
            "dataset": "DAVIS-2017",
            "split": "train",
            "seeds": [101, 202, 303, 404, 505],
            "randomization_seed": 20260820,
            "dev_samples": EXPECTED_DEV_SAMPLES,
            "frozen_eval_samples": EXPECTED_FROZEN_SAMPLES,
            "methods": EXPECTED_METHODS,
            "total_requests": 550,
            "thresholds": {
                "accuracy": 0.70,
                "swap_consistency": 0.85,
                "high_confidence_coverage": 0.60,
                "min_category_accuracy": 0.60,
            },
            "threshold_grids": {
                "confidence": [0.5, 0.6, 0.7, 0.8, 0.9],
                "absolute_delta": [0.0, 0.25, 0.5, 0.75, 1.0],
            },
            "method_selection": {
                "candidates": ["pairwise-swap-v1", "rubric-swap-v1"],
                "rubric_tie_tolerance": 0.01,
            },
            "bootstrap_seed": 20260820,
            "bootstrap_iterations": 2000,
        }
        for field, expected in expected_fields.items():
            if cfg.get(field) != expected:
                config_errors.append(
                    f"fixed protocol field {field} drifted: expected {expected!r}, got {cfg.get(field)!r}"
                )
    collector.record(
        "config.fixed-protocol",
        config_errors,
        "protocol schema, split, four methods, thresholds, and final selection candidates are fixed",
    )

    runtime_errors: List[str] = []
    try:
        runtime = load_runtime_config(runtime_path)
    except Exception as exc:
        runtime_errors.append(f"runtime schema validation failed: {exc}")
    if runtime is not None:
        expected = {
            "backend": "command",
            "model.name": EXPECTED_MODEL_NAME,
            "model.revision": EXPECTED_MODEL_REVISION,
            "model.local_path": EXPECTED_MODEL_PATH,
            "adapter.python": EXPECTED_ADAPTER_PYTHON,
            "adapter.script": EXPECTED_ADAPTER_SCRIPT,
            "adapter.timeout_seconds": 0,
        }
        actual = {
            "backend": runtime.backend,
            "model.name": runtime.model.name,
            "model.revision": runtime.model.revision,
            "model.local_path": runtime.model.local_path,
            "adapter.python": runtime.adapter.python,
            "adapter.script": runtime.adapter.script,
            "adapter.timeout_seconds": runtime.adapter.timeout_seconds,
        }
        for field, value in expected.items():
            if actual[field] != value:
                runtime_errors.append(
                    f"fixed runtime field {field} drifted: expected {value!r}, got {actual[field]!r}"
                )
        if runtime.adapter.replay_source is not None:
            runtime_errors.append("command runtime must not define adapter.replay_source")
    collector.record(
        "runtime.fixed-command-model",
        runtime_errors,
        "command backend, fixed Qwen model identity, and fixed adapter paths are valid",
        {
            "model_manifest_sha256": runtime.model.manifest_sha256,
            "runtime_fingerprint": runtime_fingerprint(runtime),
        }
        if runtime is not None
        else None,
    )

    prompt_errors: List[str] = []
    if cfg is not None:
        for method, method_cfg in EXPECTED_METHODS.items():
            try:
                prompt_path = config_path.parent / method_cfg["prompt"]
                spec, checksum = load_prompt(prompt_path)
                prompts[method] = (spec, checksum)
                if checksum != EXPECTED_PROMPT_CHECKSUMS[method]:
                    prompt_errors.append(
                        f"{method} prompt checksum drifted: expected "
                        f"{EXPECTED_PROMPT_CHECKSUMS[method]}, got {checksum}"
                    )
                if spec.prompt_version != method or spec.parser_version != "2":
                    prompt_errors.append(f"{method} prompt/parser version mismatch")
                if spec.status != "development":
                    prompt_errors.append(f"{method} prompt must have development status before smoke")
                if spec.generation_parameters != EXPECTED_GENERATION[method]:
                    prompt_errors.append(f"{method} generation parameters drifted")
            except Exception as exc:
                prompt_errors.append(f"{method} prompt validation failed: {exc}")
    else:
        prompt_errors.append("prompt checks require a readable pilot config")
    collector.record(
        "prompts.fixed-files-and-checksums",
        prompt_errors,
        "all four prompt files, parser identities, generation parameters, and checksums are fixed",
        {"prompt_checksums": {method: item[1] for method, item in prompts.items()}},
    )
    return cfg, runtime, prompts


def _verify_pairs(records: List[PairRecordV2], cfg: dict) -> Tuple[dict, dict, dict, List[str]]:
    errors: List[str] = []
    pair_ids = [record.pair_id for record in records]
    if len(records) != 100:
        errors.append(f"expected 100 pairs, got {len(records)}")
    if len(pair_ids) != len(set(pair_ids)):
        errors.append("pair IDs are not unique")

    by_sample: Dict[str, List[PairRecordV2]] = defaultdict(list)
    candidate_samples: Dict[str, set] = defaultdict(set)
    candidate_refs: Dict[str, Any] = {}
    source_refs: Dict[str, Any] = {}
    identical_count = 0
    excluded = Counter()
    expected_dev = set(cfg.get("dev_samples", []))
    expected_frozen = set(cfg.get("frozen_eval_samples", []))
    expected_seed = cfg.get("randomization_seed")
    for pair in records:
        by_sample[pair.sample_id].append(pair)
        expected_split = "dev" if pair.sample_id in expected_dev else "frozen-eval"
        if pair.sample_id not in expected_dev | expected_frozen:
            errors.append(f"pair {pair.pair_id} uses unknown sample {pair.sample_id}")
        elif pair.split != expected_split:
            errors.append(f"pair {pair.pair_id} has split {pair.split}, expected {expected_split}")
        if pair.randomization_seed != expected_seed:
            errors.append(f"pair {pair.pair_id} randomization seed drifted")
        for candidate in (pair.candidate_a, pair.candidate_b):
            candidate_samples[candidate.candidate_id].add(pair.sample_id)
            previous = candidate_refs.setdefault(candidate.candidate_id, candidate)
            if previous != candidate:
                errors.append(f"candidate identity drifts across pairs: {candidate.candidate_id}")
        previous_source = source_refs.setdefault(pair.sample_id, pair.source)
        if previous_source != pair.source:
            errors.append(f"source identity drifts across sample {pair.sample_id}")
        actual_identical = pair.candidate_a.video_sha256 == pair.candidate_b.video_sha256
        if pair.identical_media != actual_identical:
            errors.append(f"pair {pair.pair_id} identical_media flag is inconsistent")
        identical_count += int(pair.identical_media)
        excluded[str(pair.excluded_reason or "none")] += 1

    if set(by_sample) != expected_dev | expected_frozen:
        errors.append("pair samples do not exactly match the fixed 3/7 split")
    for sample_id, sample_pairs in by_sample.items():
        if len(sample_pairs) != 10:
            errors.append(f"sample {sample_id} has {len(sample_pairs)} pairs, expected 10")
        candidates = sorted(
            {
                candidate.candidate_id
                for pair in sample_pairs
                for candidate in (pair.candidate_a, pair.candidate_b)
            }
        )
        if len(candidates) != 5:
            errors.append(f"sample {sample_id} has {len(candidates)} candidates, expected 5")
        actual_combinations = {
            (pair.candidate_a.candidate_id, pair.candidate_b.candidate_id)
            for pair in sample_pairs
        }
        if actual_combinations != set(combinations(candidates, 2)):
            errors.append(f"sample {sample_id} does not contain each canonical candidate pair once")
        context = {
            (pair.task_type, pair.instruction, pair.target_caption, pair.source.model_dump_json())
            for pair in sample_pairs
        }
        if len(context) != 1:
            errors.append(f"sample {sample_id} pair context is inconsistent")
    for candidate_id, samples in candidate_samples.items():
        if len(samples) != 1:
            errors.append(f"candidate {candidate_id} belongs to multiple samples: {sorted(samples)}")
    if len(candidate_refs) != 50:
        errors.append(f"expected 50 unique candidate identities, got {len(candidate_refs)}")
    if identical_count != 0:
        errors.append(f"formal production preparation expected 0 identical-media pairs, got {identical_count}")
    excluded_nonempty = sum(count for reason, count in excluded.items() if reason != "none")
    if excluded_nonempty != 0:
        errors.append(f"formal production preparation contains {excluded_nonempty} excluded pairs")

    split_counts = Counter(record.split for record in records)
    if dict(split_counts) != {"dev": 30, "frozen-eval": 70}:
        errors.append(f"pair split counts must be 30/70, got {dict(split_counts)}")
    counts = {
        "pairs": len(records),
        "samples": len(by_sample),
        "candidates": len(candidate_refs),
        "pair_split_counts": dict(sorted(split_counts.items())),
        "pairs_per_sample": {
            sample_id: len(sample_pairs) for sample_id, sample_pairs in sorted(by_sample.items())
        },
        "identical_media_pairs": identical_count,
        "excluded_reason_counts": dict(sorted(excluded.items())),
    }
    return counts, source_refs, candidate_refs, errors


def _verify_asset(
    key: str,
    asset: MediaAssetV2,
    expected_ref: Any,
    kind: str,
    path_mapping: Optional[PreparationPathMapping],
) -> List[str]:
    errors: List[str] = []
    if asset.asset_id != key:
        errors.append(f"{kind} asset dict key {key} != asset_id {asset.asset_id}")
    if not _same_path(asset.original_path, expected_ref.video_path):
        errors.append(f"{kind} asset {key} original path does not match pairs")
    if asset.original_sha256 != expected_ref.video_sha256:
        errors.append(f"{kind} asset {key} original SHA does not match pairs")
    original = path_mapping.physical_path(asset.original_path) if path_mapping else Path(asset.original_path)
    if not original.is_file():
        errors.append(f"{kind} asset {key} original file is missing: {original}")
    elif sha256_file(original) != asset.original_sha256:
        errors.append(f"{kind} asset {key} original file SHA mismatch")
    linked = path_mapping.physical_path(asset.video.path) if path_mapping else Path(asset.video.path)
    if not linked.is_file():
        errors.append(f"{kind} asset {key} linked/copied video is missing: {linked}")
    else:
        actual = sha256_file(linked)
        if actual != asset.video.sha256:
            errors.append(f"{kind} asset {key} linked/copied video SHA mismatch")
        if actual != asset.original_sha256:
            errors.append(f"{kind} asset {key} linked/copied video differs from original SHA")
    if asset.video.sha256 != asset.original_sha256:
        errors.append(f"{kind} asset {key} video manifest SHA differs from original SHA")
    if len(asset.frames) != 16:
        errors.append(f"{kind} asset {key} has {len(asset.frames)} frames, expected 16")
    for index, frame in enumerate(asset.frames):
        path = path_mapping.physical_path(frame.path) if path_mapping else Path(frame.path)
        if not path.is_file():
            errors.append(f"{kind} asset {key} frame {index} is missing: {path}")
        elif sha256_file(path) != frame.sha256:
            errors.append(f"{kind} asset {key} frame {index} SHA mismatch")
    contact = (
        path_mapping.physical_path(asset.contact_sheet.path)
        if path_mapping
        else Path(asset.contact_sheet.path)
    )
    if not contact.is_file():
        errors.append(f"{kind} asset {key} contact sheet is missing: {contact}")
    elif sha256_file(contact) != asset.contact_sheet.sha256:
        errors.append(f"{kind} asset {key} contact sheet SHA mismatch")
    return errors


def _request_media(asset: MediaAssetV2) -> dict:
    return {
        "asset_id": asset.asset_id,
        "video_path": asset.video.path,
        "video_sha256": asset.original_sha256,
        "frame_paths": [frame.path for frame in asset.frames],
        "frame_sha256": [frame.sha256 for frame in asset.frames],
        "contact_sheet_path": asset.contact_sheet.path,
        "contact_sheet_sha256": asset.contact_sheet.sha256,
    }


def _verify_manifest(
    manifest: MediaManifestV2,
    pairs: List[PairRecordV2],
    source_refs: dict,
    candidate_refs: dict,
    path_mapping: Optional[PreparationPathMapping],
) -> Tuple[dict, List[str]]:
    errors: List[str] = []
    pair_by_id = {pair.pair_id: pair for pair in pairs}
    if set(manifest.sources) != set(source_refs):
        errors.append("manifest source keys do not exactly match pair source samples")
    if set(manifest.candidates) != set(candidate_refs):
        errors.append("manifest candidate keys do not exactly match pair candidate identities")
    if set(manifest.pairs) != set(pair_by_id):
        errors.append("manifest packet keys do not exactly match pair IDs")

    for key, asset in manifest.sources.items():
        expected = source_refs.get(key)
        if expected is None:
            errors.append(f"unexpected source asset {key}")
        else:
            errors.extend(_verify_asset(key, asset, expected, "source", path_mapping))
    for key, asset in manifest.candidates.items():
        expected = candidate_refs.get(key)
        if expected is None:
            errors.append(f"unexpected candidate asset {key}")
        else:
            errors.extend(_verify_asset(key, asset, expected, "candidate", path_mapping))

    all_assets = [*manifest.sources.values(), *manifest.candidates.values()]
    frame_paths = [frame.path for asset in all_assets for frame in asset.frames]
    contact_paths = [asset.contact_sheet.path for asset in all_assets]
    if len(frame_paths) != 960 or len(set(frame_paths)) != 960:
        errors.append("60 assets must reference 960 unique frame files")
    if len(contact_paths) != 60 or len(set(contact_paths)) != 60:
        errors.append("60 assets must reference 60 unique contact sheets")

    mask_paths: List[str] = []
    metadata_paths: List[str] = []
    packet_checksums: List[str] = []
    for pair_id, packet in manifest.pairs.items():
        pair = pair_by_id.get(pair_id)
        if pair is None:
            continue
        missing_assets = [
            asset_id
            for asset_id in (
                pair.sample_id,
                pair.candidate_a.candidate_id,
                pair.candidate_b.candidate_id,
            )
            if asset_id not in manifest.sources and asset_id not in manifest.candidates
        ]
        if missing_assets:
            errors.append(
                f"packet {pair_id} references missing manifest assets: {missing_assets}"
            )
            continue
        expected_ids = (
            pair.sample_id,
            pair.candidate_a.candidate_id,
            pair.candidate_b.candidate_id,
        )
        actual_ids = (
            packet.source_asset_id,
            packet.candidate_a_asset_id,
            packet.candidate_b_asset_id,
        )
        if actual_ids != expected_ids:
            errors.append(f"packet {pair_id} source/A/B asset references are incorrect")
        if packet.mask_overlay is None:
            errors.append(f"packet {pair_id} is missing the production mask overlay")
        else:
            mask_paths.append(packet.mask_overlay.path)
            mask_path = (
                path_mapping.physical_path(packet.mask_overlay.path)
                if path_mapping
                else Path(packet.mask_overlay.path)
            )
            if not mask_path.is_file():
                errors.append(f"packet {pair_id} mask overlay is missing: {mask_path}")
            elif sha256_file(mask_path) != packet.mask_overlay.sha256:
                errors.append(f"packet {pair_id} mask overlay SHA mismatch")
        metadata_paths.append(packet.metadata_path)
        metadata_path = (
            path_mapping.physical_path(packet.metadata_path)
            if path_mapping
            else Path(packet.metadata_path)
        )
        identity = {
            "schema_version": "2",
            "pair_id": pair_id,
            "source": manifest.sources[pair.sample_id].model_dump(mode="json"),
            "candidate_a": manifest.candidates[pair.candidate_a.candidate_id].model_dump(mode="json"),
            "candidate_b": manifest.candidates[pair.candidate_b.candidate_id].model_dump(mode="json"),
            "mask_overlay": packet.mask_overlay.model_dump(mode="json")
            if packet.mask_overlay
            else None,
        }
        expected_checksum = canonical_sha256(identity)
        packet_checksums.append(packet.packet_checksum)
        if packet.packet_checksum != expected_checksum:
            errors.append(f"packet {pair_id} checksum cannot be recomputed from manifest identity")
        if not metadata_path.is_file():
            errors.append(f"packet {pair_id} metadata is missing: {metadata_path}")
        else:
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"packet {pair_id} metadata is invalid JSON: {exc}")
            else:
                expected_metadata = {**identity, "packet_checksum": expected_checksum}
                if metadata != expected_metadata:
                    errors.append(f"packet {pair_id} metadata identity/checksum does not match manifest")

    if len(mask_paths) != 100 or len(set(mask_paths)) != 100:
        errors.append(f"formal production preparation requires 100 unique mask overlays, got {len(set(mask_paths))}")
    if len(metadata_paths) != 100 or len(set(metadata_paths)) != 100:
        errors.append("100 packets must reference 100 unique metadata files")
    if len(packet_checksums) != 100 or len(set(packet_checksums)) != 100:
        errors.append("100 packet checksums must be unique")
    counts = {
        "source_assets": len(manifest.sources),
        "candidate_assets": len(manifest.candidates),
        "pair_packets": len(manifest.pairs),
        "asset_frames": len(frame_paths),
        "contact_sheets": len(contact_paths),
        "mask_overlays": len(mask_paths),
        "packet_metadata_files": len(metadata_paths),
    }
    return counts, errors


def _verify_dirty_snapshot(snapshot: str, config_path: Path) -> Tuple[List[str], Optional[str]]:
    errors: List[str] = []
    warning = None
    if not HEX40.fullmatch(snapshot):
        errors.append(
            f"code_snapshot must be a 40-hex commit with optional +dirty, got {snapshot!r}"
        )
        return errors, warning
    if not snapshot.endswith("+dirty"):
        return errors, warning
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=config_path.parent,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"cannot audit +dirty code snapshot against Git status: {exc}")
        return errors, warning
    paths = {line[3:].replace("\\", "/") for line in status if line.strip()}
    if paths != {"DEVLOG.md"}:
        errors.append(
            "+dirty development snapshot is allowed only for DEVLOG.md; "
            f"current dirty paths are {sorted(paths)}"
        )
    else:
        warning = "code_snapshot is +dirty; current Git status was explicitly verified as DEVLOG.md-only"
    return errors, warning


def _verify_plan(
    requests: List[JudgeRequestV2],
    pairs: List[PairRecordV2],
    manifest: MediaManifestV2,
    runtime: RuntimeConfigV2,
    prompts: Dict[str, Tuple[Any, str]],
    config_path: Path,
) -> Tuple[dict, Optional[str], List[str], Optional[str]]:
    errors: List[str] = []
    pair_by_id = {pair.pair_id: pair for pair in pairs}
    candidate_context: Dict[str, PairRecordV2] = {}
    sample_packet = {}
    for pair in pairs:
        for candidate in (pair.candidate_a, pair.candidate_b):
            candidate_context.setdefault(candidate.candidate_id, pair)
        sample_packet.setdefault(pair.sample_id, manifest.pairs[pair.pair_id])

    request_ids = [request.request_id for request in requests]
    judge_keys = [request.judge_key for request in requests]
    if len(requests) != 550:
        errors.append(f"expected 550 requests, got {len(requests)}")
    if len(request_ids) != len(set(request_ids)):
        errors.append("request IDs are not unique")
    if len(judge_keys) != len(set(judge_keys)):
        errors.append("judge keys are not unique")

    runtime_sha = runtime_fingerprint(runtime)
    method_counts = Counter(request.method for request in requests)
    split_counts = Counter(request.split for request in requests)
    method_split = {
        method: {
            split: sum(request.method == method and request.split == split for request in requests)
            for split in ("dev", "frozen-eval")
        }
        for method in EXPECTED_METHODS
    }
    if dict(method_counts) != {method: data["requests"] for method, data in EXPECTED_METHODS.items()}:
        errors.append(f"method counts drifted: {dict(method_counts)}")
    if dict(split_counts) != {"dev": 165, "frozen-eval": 385}:
        errors.append(f"request split counts must be 165/385, got {dict(split_counts)}")
    if method_split != EXPECTED_METHOD_SPLIT_COUNTS:
        errors.append(f"method/split counts drifted: {method_split}")

    absolute_seen = Counter()
    pair_method_directions: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    snapshot_values = {request.code_snapshot for request in requests}
    for request in requests:
        prompt_item = prompts.get(request.method)
        if prompt_item is None:
            errors.append(f"request {request.request_id} uses unavailable prompt method {request.method}")
            continue
        prompt_spec, prompt_sha = prompt_item
        if request.backend != runtime.backend:
            errors.append(f"request {request.request_id} backend differs from runtime")
        if (
            request.model_name != runtime.model.name
            or request.model_revision != runtime.model.revision
            or request.model_manifest_sha256 != runtime.model.manifest_sha256
        ):
            errors.append(f"request {request.request_id} model identity differs from runtime")
        if request.runtime_fingerprint != runtime_sha:
            errors.append(f"request {request.request_id} runtime fingerprint differs from runtime file")
        if request.frozen_protocol_fingerprint is not None:
            errors.append(f"development request {request.request_id} unexpectedly has a frozen fingerprint")
        if (
            request.prompt_version != prompt_spec.prompt_version
            or request.prompt_checksum != prompt_sha
            or request.parser_version != prompt_spec.parser_version
            or request.generation_parameters != prompt_spec.generation_parameters
        ):
            errors.append(f"request {request.request_id} prompt/parser/generation identity drifted")
        expected_rendered = render_prompt(prompt_spec, request.instruction, request.target_caption)
        if request.rendered_prompt != expected_rendered:
            errors.append(f"request {request.request_id} rendered prompt does not match current prompt")
        if request.judge_key != judge_key(request.model_dump(mode="json")):
            errors.append(f"request {request.request_id} judge_key cannot be recomputed")

        if request.method == "absolute-v1":
            candidate_id = request.candidate_id
            if candidate_id is None or candidate_id not in candidate_context:
                errors.append(f"absolute request {request.request_id} has an unknown candidate")
                continue
            absolute_seen[candidate_id] += 1
            pair = candidate_context[candidate_id]
            source_asset = manifest.sources[pair.sample_id]
            candidate_asset = manifest.candidates[candidate_id]
            packet = sample_packet[pair.sample_id]
            expected_mask = packet.mask_overlay.model_dump(mode="json") if packet.mask_overlay else None
            expected_packet_sha = canonical_sha256(
                {
                    "source": source_asset.original_sha256,
                    "candidate": candidate_asset.original_sha256,
                    "mask": expected_mask,
                }
            )
            if request.request_id != f"absolute-v1:{candidate_id}:absolute":
                errors.append(f"absolute request ID is not canonical: {request.request_id}")
            if (
                request.sample_id != pair.sample_id
                or request.split != pair.split
                or request.task_type != pair.task_type
                or request.instruction != pair.instruction
                or request.target_caption != pair.target_caption
            ):
                errors.append(f"absolute request {request.request_id} pair context is inconsistent")
            if request.source.model_dump(mode="json") != _request_media(source_asset):
                errors.append(f"absolute request {request.request_id} source media identity is inconsistent")
            if request.candidate_a.model_dump(mode="json") != _request_media(candidate_asset):
                errors.append(f"absolute request {request.request_id} candidate media identity is inconsistent")
            actual_mask = request.mask_overlay.model_dump(mode="json") if request.mask_overlay else None
            if actual_mask != expected_mask:
                errors.append(f"absolute request {request.request_id} mask identity is inconsistent")
            if request.media_packet_checksum != expected_packet_sha:
                errors.append(f"absolute request {request.request_id} media checksum is inconsistent")
            continue

        pair_id = request.pair_id
        if pair_id is None or pair_id not in pair_by_id:
            errors.append(f"pairwise request {request.request_id} has an unknown pair")
            continue
        pair = pair_by_id[pair_id]
        packet = manifest.pairs[pair_id]
        pair_method_directions[(request.method, pair_id)].append(request.comparison_direction)
        canonical_assets = [
            (pair.candidate_a.candidate_id, manifest.candidates[pair.candidate_a.candidate_id]),
            (pair.candidate_b.candidate_id, manifest.candidates[pair.candidate_b.candidate_id]),
        ]
        screen_assets = (
            canonical_assets
            if request.comparison_direction == "a_vs_b"
            else list(reversed(canonical_assets))
        )
        if request.request_id != f"{request.method}:{pair_id}:{request.comparison_direction}":
            errors.append(f"pairwise request ID is not canonical: {request.request_id}")
        if (
            request.sample_id != pair.sample_id
            or request.split != pair.split
            or request.task_type != pair.task_type
            or request.instruction != pair.instruction
            or request.target_caption != pair.target_caption
        ):
            errors.append(f"pairwise request {request.request_id} pair context is inconsistent")
        if request.source.model_dump(mode="json") != _request_media(manifest.sources[pair.sample_id]):
            errors.append(f"pairwise request {request.request_id} source media identity is inconsistent")
        if request.candidate_a_id != screen_assets[0][0] or request.candidate_b_id != screen_assets[1][0]:
            errors.append(f"pairwise request {request.request_id} screen-side candidate identity is inconsistent")
        if request.candidate_a.model_dump(mode="json") != _request_media(screen_assets[0][1]):
            errors.append(f"pairwise request {request.request_id} candidate A media is inconsistent")
        if request.candidate_b is None or request.candidate_b.model_dump(mode="json") != _request_media(screen_assets[1][1]):
            errors.append(f"pairwise request {request.request_id} candidate B media is inconsistent")
        expected_mask = packet.mask_overlay.model_dump(mode="json") if packet.mask_overlay else None
        actual_mask = request.mask_overlay.model_dump(mode="json") if request.mask_overlay else None
        if actual_mask != expected_mask:
            errors.append(f"pairwise request {request.request_id} mask identity is inconsistent")
        if request.media_packet_checksum != packet.packet_checksum:
            errors.append(f"pairwise request {request.request_id} packet checksum is inconsistent")

    if set(absolute_seen) != set(candidate_context) or any(count != 1 for count in absolute_seen.values()):
        errors.append("absolute method must contain exactly one request for each of 50 candidates")
    for pair_id in pair_by_id:
        if pair_method_directions.get(("pairwise-single-v1", pair_id)) != ["a_vs_b"]:
            errors.append(f"pair {pair_id} pairwise-single directions must be exactly [a_vs_b]")
        for method in ("pairwise-swap-v1", "rubric-swap-v1"):
            directions = pair_method_directions.get((method, pair_id), [])
            if Counter(directions) != Counter({"a_vs_b": 1, "b_vs_a": 1}):
                errors.append(f"pair {pair_id} {method} must contain both swap directions exactly once")

    warning = None
    snapshot = next(iter(snapshot_values)) if len(snapshot_values) == 1 else None
    if len(snapshot_values) != 1:
        errors.append(f"plan mixes code snapshots: {sorted(snapshot_values)}")
    elif snapshot is not None:
        snapshot_errors, warning = _verify_dirty_snapshot(snapshot, config_path)
        errors.extend(snapshot_errors)

    uniform_fields = (
        "runtime_fingerprint",
        "model_name",
        "model_revision",
        "model_manifest_sha256",
        "backend",
    )
    for field in uniform_fields:
        values = {getattr(request, field) for request in requests}
        if len(values) != 1:
            errors.append(f"plan mixes {field}: {sorted(values)}")
    for method in EXPECTED_METHODS:
        method_requests = [request for request in requests if request.method == method]
        identities = {
            (
                request.prompt_checksum,
                request.parser_version,
                canonical_sha256(request.generation_parameters),
                request.runtime_fingerprint,
                request.model_name,
                request.model_revision,
                request.model_manifest_sha256,
            )
            for request in method_requests
        }
        if len(identities) != 1:
            errors.append(f"plan mixes prompt/parser/generation/runtime/model identity within {method}")

    counts = {
        "requests": len(requests),
        "unique_request_ids": len(set(request_ids)),
        "unique_judge_keys": len(set(judge_keys)),
        "request_split_counts": dict(sorted(split_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "method_split_counts": method_split,
    }
    return counts, snapshot, errors, warning


def verify_preparation(
    pairs: Path,
    packets: Path,
    plan: Path,
    config: Path,
    runtime: Path,
    output: Optional[Path] = None,
    *,
    path_mapping: Optional[PreparationPathMapping] = None,
) -> dict:
    """Verify the phase-3 preparation bundle without changing any input."""
    pairs = Path(pairs).resolve()
    packets = Path(packets).resolve()
    plan = Path(plan).resolve()
    config = Path(config).resolve()
    runtime = Path(runtime).resolve()
    output = Path(output).resolve() if output is not None else None
    if output is not None and output.exists():
        raise FileExistsError(f"verification output already exists: {output}")

    manifest_path = packets / "media-manifest.json" if packets.is_dir() else packets
    collector = _Collector()
    input_errors: List[str] = []
    for label, path in {
        "pairs": pairs,
        "packets_manifest": manifest_path,
        "plan": plan,
        "config": config,
        "runtime": runtime,
    }.items():
        if not path.is_file():
            input_errors.append(f"{label} input is missing or not a file: {path}")
    collector.record(
        "inputs.paths-and-sha256",
        input_errors,
        "all five input identities are readable and hashed",
    )
    inputs = {
        label: _input_descriptor(path, path_mapping)
        for label, path in {
            "pairs": pairs,
            "packets_manifest": manifest_path,
            "plan": plan,
            "config": config,
            "runtime": runtime,
        }.items()
    }

    cfg, runtime_model, prompts = _verify_config_runtime(config, runtime, collector)

    pair_records: Optional[List[PairRecordV2]] = None
    pairs_ready = False
    pair_counts: dict = {}
    source_refs: dict = {}
    candidate_refs: dict = {}
    try:
        pair_records = _jsonl_models(pairs, PairRecordV2)
    except Exception as exc:
        collector.failed("pairs.schema-v2", exc)
    else:
        collector.record(
            "pairs.schema-v2",
            [],
            f"all {len(pair_records)} pair rows validate as strict schema v2",
        )
        if cfg is None:
            collector.skipped("pairs.identities-and-counts", "pilot config could not be loaded")
        else:
            pair_counts, source_refs, candidate_refs, errors = _verify_pairs(pair_records, cfg)
            pairs_ready = not errors
            collector.record(
                "pairs.identities-and-counts",
                errors,
                "100 unique pairs, 30/70 split, 10 samples, 50 candidates, and MP4 source identities are valid",
                pair_counts,
            )

    manifest: Optional[MediaManifestV2] = None
    manifest_ready = False
    manifest_counts: dict = {}
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = MediaManifestV2.model_validate(manifest_payload)
    except Exception as exc:
        collector.failed("media.schema-v2", exc)
    else:
        collector.record(
            "media.schema-v2",
            [],
            "media manifest validates as strict schema v2",
        )
        if not pairs_ready or pair_records is None or not source_refs or not candidate_refs:
            collector.skipped("media.assets-packets-and-masks", "validated pair identities are unavailable")
        else:
            try:
                manifest_counts, errors = _verify_manifest(
                    manifest, pair_records, source_refs, candidate_refs, path_mapping
                )
            except Exception as exc:
                collector.failed("media.assets-packets-and-masks", exc)
            else:
                manifest_ready = not errors
                collector.record(
                    "media.assets-packets-and-masks",
                    errors,
                    "10 sources, 50 candidates, 960 frames, 60 contact sheets, and 100 packet masks/metadata/checksums are valid",
                    manifest_counts,
                )

    request_records: Optional[List[JudgeRequestV2]] = None
    plan_counts: dict = {}
    snapshot = None
    try:
        request_records = _jsonl_models(plan, JudgeRequestV2)
    except Exception as exc:
        collector.failed("plan.schema-v2", exc)
    else:
        collector.record(
            "plan.schema-v2",
            [],
            f"all {len(request_records)} request rows validate as strict schema v2",
        )
        dependencies_ready = (
            pairs_ready
            and manifest_ready
            and pair_records is not None
            and manifest is not None
            and runtime_model is not None
            and len(prompts) == 4
        )
        if not dependencies_ready:
            collector.skipped("plan.identities-counts-and-swap", "pair/media/runtime/prompt dependencies are unavailable")
        else:
            plan_counts, snapshot, errors, warning = _verify_plan(
                request_records,
                pair_records,
                manifest,
                runtime_model,
                prompts,
                config,
            )
            if warning:
                collector.warnings.append(warning)
            collector.record(
                "plan.identities-counts-and-swap",
                errors,
                "550 unique requests have exact method/split/swap/media/prompt/runtime/model/code identities",
                plan_counts,
            )

    status = "failed" if collector.failures else "passed"
    counts = {**pair_counts, **manifest_counts, **plan_counts}
    report = {
        "report_schema_version": "1",
        "status": status,
        "generated_at": _utc_now(),
        "verification_context": {
            "mode": "prepublish-staging" if path_mapping else "direct",
            "declared_root": str(path_mapping.declared_root) if path_mapping else None,
            "physical_root_recorded_in": "phase3-preparation-v01.json"
            if path_mapping
            else None,
        },
        "inputs": inputs,
        "counts": counts,
        "method_counts": plan_counts.get("method_counts", {}),
        "split_counts": {
            "pairs": pair_counts.get("pair_split_counts", {}),
            "requests": plan_counts.get("request_split_counts", {}),
        },
        "method_split_counts": plan_counts.get("method_split_counts", {}),
        "runtime": {
            "backend": runtime_model.backend,
            "fingerprint": runtime_fingerprint(runtime_model),
            "adapter": runtime_model.adapter.model_dump(mode="json"),
        }
        if runtime_model is not None
        else None,
        "model_identity": runtime_model.model.model_dump(mode="json")
        if runtime_model is not None
        else None,
        "prompt_checksums": {method: item[1] for method, item in prompts.items()},
        "code_snapshot": snapshot,
        "checks": collector.checks,
        "warnings": collector.warnings,
        "failures": collector.failures,
        "ready_for_smoke": status == "passed",
    }
    if output is not None:
        _atomic_write_new_json(output, report)
    if collector.failures:
        raise PreparationVerificationError(report)
    return report
