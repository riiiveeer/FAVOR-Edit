"""Atomic preparation of the complete E2 Best-of-N judge bundle."""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from PIL import Image

from e1_judge.hashing import canonical_sha256
from e1_judge.models import (
    FrozenProtocolV2, MediaAssetV2, MediaFileV2, MediaManifestV2, PairPacketV2,
    RequestMediaV2, load_runtime_config, validate_config,
)
from e1_judge.phase3 import _rename_noreplace
from e1_judge.prompts import load_prompt, render_prompt
from e1_judge.runner import code_snapshot, frozen_protocol_fingerprint, runtime_fingerprint
from w1_pipeline.hashing import sha256_file

from .config import load_config
from .io import read_json
from .models import (
    BonTrialV1, CandidatePoolV1, CandidateRefV1, E2JudgeRequestV1, E2PairV1,
    PoolCandidateV1,
)

PREPARE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
RELIABILITY_GATES = {"accuracy", "swap_consistency", "coverage", "categories"}


class E2PreparationError(RuntimeError):
    def __init__(self, stage: str, message: str, staging_root: Optional[Path] = None, failure_root: Optional[Path] = None):
        super().__init__(message)
        self.stage = stage
        self.staging_root = staging_root
        self.failure_root = failure_root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _declared(physical: Path, physical_root: Path, final_root: Path) -> Path:
    return final_root / physical.relative_to(physical_root)


def _copy_or_link(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        target.symlink_to(source.resolve())
    except OSError:
        shutil.copy2(source, target)


def _contact_sheet(frames: List[Path], output: Path) -> None:
    if len(frames) != 16:
        raise ValueError("contact sheet requires 16 frames")
    canvas = Image.new("RGB", (650, 650), "black")
    opened: List[Image.Image] = []
    try:
        for index, path in enumerate(frames):
            image = Image.open(path).convert("RGB")
            opened.append(image)
            resized = image.resize((160, 160), Image.Resampling.LANCZOS)
            row, column = divmod(index, 4)
            canvas.paste(resized, (2 + column * 162, 2 + row * 162))
        canvas.save(output, format="JPEG", quality=90, optimize=False, progressive=False)
    finally:
        for image in opened:
            image.close()


def _media_ref(physical: Path, physical_root: Path, final_root: Path) -> MediaFileV2:
    return MediaFileV2(path=str(_declared(physical, physical_root, final_root)), sha256=sha256_file(physical))


def _asset(
    asset_id: str,
    video: Path,
    video_sha: str,
    frame_paths: List[Path],
    frame_sha: Optional[List[str]],
    physical_dir: Path,
    physical_root: Path,
    final_root: Path,
) -> MediaAssetV2:
    if sha256_file(video) != video_sha:
        raise ValueError(f"asset {asset_id} video checksum mismatch")
    if len(frame_paths) != 16 or not all(path.is_file() for path in frame_paths):
        raise ValueError(f"asset {asset_id} requires 16 existing frames")
    if frame_sha is not None and [sha256_file(path) for path in frame_paths] != frame_sha:
        raise ValueError(f"asset {asset_id} frame checksum mismatch")
    physical_dir.mkdir(parents=True)
    linked_video = physical_dir / "video.mp4"
    _copy_or_link(video, linked_video)
    frame_dir = physical_dir / "frames"
    frame_dir.mkdir()
    physical_frames: List[Path] = []
    for index, source in enumerate(frame_paths):
        target = frame_dir / f"frame-{index:03d}.png"
        _copy_or_link(source, target)
        physical_frames.append(target)
    contact = physical_dir / "contact-sheet.jpg"
    _contact_sheet(frame_paths, contact)
    return MediaAssetV2(
        asset_id=asset_id,
        original_path=str(video.resolve()),
        original_sha256=video_sha,
        video=_media_ref(linked_video, physical_root, final_root),
        frames=[_media_ref(path, physical_root, final_root) for path in physical_frames],
        contact_sheet=_media_ref(contact, physical_root, final_root),
    )


def _mask_overlay(mask_paths: List[str], physical: Path, physical_root: Path, final_root: Path) -> Optional[MediaFileV2]:
    if not mask_paths:
        return None
    paths = [Path(path) for path in mask_paths]
    if len(paths) != 16 or not all(path.is_file() for path in paths):
        raise ValueError("mask overlay requires 16 existing masks")
    _contact_sheet(paths, physical)
    return _media_ref(physical, physical_root, final_root)


def _build_pairs(pool: CandidatePoolV1, config_path: Path) -> List[E2PairV1]:
    cfg = load_config(config_path)
    by_sample: Dict[str, List[PoolCandidateV1]] = defaultdict(list)
    for candidate in pool.candidates:
        by_sample[candidate.sample_id].append(candidate)
    pairs: List[E2PairV1] = []
    for sample_id in cfg.sample_ids:
        candidates = sorted(by_sample[sample_id], key=lambda item: item.candidate_id)
        if len(candidates) != 8:
            raise ValueError(f"sample {sample_id} requires eight candidates")
        input_data = candidates[0].input
        for number, (left, right) in enumerate(combinations(candidates, 2), start=1):
            if left.input != input_data or right.input != input_data:
                raise ValueError(f"sample {sample_id} input identity drift")
            pairs.append(E2PairV1(
                experiment_id=cfg.experiment_id,
                pair_id=f"{sample_id}-e2-p{number:03d}",
                sample_id=sample_id,
                task_type=input_data["task_type"],
                instruction=input_data["instruction"],
                target_caption=input_data["target_caption"],
                source_video_path=input_data["source_video_path"],
                source_video_sha256=input_data["video_checksum"],
                source_frame_paths=input_data["source_frame_paths"],
                mask_frame_paths=input_data.get("mask_frame_paths", []),
                candidate_a=CandidateRefV1(
                    candidate_id=left.candidate_id, seed=left.seed,
                    video_path=left.video_path, video_sha256=left.video_sha256,
                ),
                candidate_b=CandidateRefV1(
                    candidate_id=right.candidate_id, seed=right.seed,
                    video_path=right.video_path, video_sha256=right.video_sha256,
                ),
            ))
    if len(pairs) != 280 or len({pair.pair_id for pair in pairs}) != 280:
        raise ValueError("E2 preparation requires 280 unique pairs")
    return pairs


def _build_design(pool: CandidatePoolV1, config_path: Path) -> List[BonTrialV1]:
    cfg = load_config(config_path)
    by_sample: Dict[str, List[PoolCandidateV1]] = defaultdict(list)
    for candidate in pool.candidates:
        by_sample[candidate.sample_id].append(candidate)
    trials: List[BonTrialV1] = []
    for sample_id in cfg.sample_ids:
        seed_map = {item.seed: item.candidate_id for item in by_sample[sample_id]}
        base_order = [seed_map[seed] for seed in cfg.all_seeds]
        for replicate in range(8):
            order = base_order[replicate:] + base_order[:replicate]
            trials.append(BonTrialV1(
                experiment_id=cfg.experiment_id,
                trial_id=f"{sample_id}-r{replicate + 1:02d}",
                sample_id=sample_id,
                replicate=replicate,
                candidate_order=order,
                subsets={str(n): order[:n] for n in cfg.n_values},
            ))
    if len(trials) != 80:
        raise ValueError("balanced design must contain 80 trials")
    return trials


def _build_packets(
    pairs: List[E2PairV1], pool: CandidatePoolV1, physical_dir: Path,
    physical_root: Path, final_root: Path,
) -> MediaManifestV2:
    sources: Dict[str, MediaAssetV2] = {}
    candidates: Dict[str, MediaAssetV2] = {}
    pool_by_id = {item.candidate_id: item for item in pool.candidates}
    for pair in pairs:
        if pair.sample_id not in sources:
            sources[pair.sample_id] = _asset(
                pair.sample_id, Path(pair.source_video_path), pair.source_video_sha256,
                [Path(path) for path in pair.source_frame_paths], None,
                physical_dir / "assets" / "sources" / pair.sample_id, physical_root, final_root,
            )
        for ref in (pair.candidate_a, pair.candidate_b):
            if ref.candidate_id not in candidates:
                pooled = pool_by_id[ref.candidate_id]
                candidates[ref.candidate_id] = _asset(
                    ref.candidate_id, Path(ref.video_path), ref.video_sha256,
                    [Path(path) for path in pooled.frame_paths], pooled.frame_sha256,
                    physical_dir / "assets" / "candidates" / ref.candidate_id,
                    physical_root, final_root,
                )
    packets: Dict[str, PairPacketV2] = {}
    for pair in pairs:
        pair_dir = physical_dir / "pairs" / pair.pair_id
        pair_dir.mkdir(parents=True)
        mask = _mask_overlay(pair.mask_frame_paths, pair_dir / "mask-overlay.jpg", physical_root, final_root)
        identity = {
            "schema_version": "1", "pair_id": pair.pair_id,
            "source": sources[pair.sample_id].model_dump(mode="json"),
            "candidate_a": candidates[pair.candidate_a.candidate_id].model_dump(mode="json"),
            "candidate_b": candidates[pair.candidate_b.candidate_id].model_dump(mode="json"),
            "mask_overlay": mask.model_dump(mode="json") if mask else None,
        }
        checksum = canonical_sha256(identity)
        metadata = pair_dir / "metadata.json"
        _write_json(metadata, {**identity, "packet_checksum": checksum})
        packets[pair.pair_id] = PairPacketV2(
            pair_id=pair.pair_id, source_asset_id=pair.sample_id,
            candidate_a_asset_id=pair.candidate_a.candidate_id,
            candidate_b_asset_id=pair.candidate_b.candidate_id,
            mask_overlay=mask,
            metadata_path=str(_declared(metadata, physical_root, final_root)),
            packet_checksum=checksum,
        )
    manifest = MediaManifestV2(sources=sources, candidates=candidates, pairs=packets)
    _write_json(physical_dir / "media-manifest.json", manifest.model_dump(mode="json"))
    return manifest


def _request_media(asset: MediaAssetV2) -> RequestMediaV2:
    return RequestMediaV2(
        asset_id=asset.asset_id, video_path=asset.video.path,
        video_sha256=asset.original_sha256,
        frame_paths=[frame.path for frame in asset.frames],
        frame_sha256=[frame.sha256 for frame in asset.frames],
        contact_sheet_path=asset.contact_sheet.path,
        contact_sheet_sha256=asset.contact_sheet.sha256,
    )


def _judge_key(request: dict) -> str:
    def media(value: dict) -> dict:
        return {
            "asset_id": value["asset_id"], "video_sha256": value["video_sha256"],
            "frame_sha256": value["frame_sha256"], "contact_sheet_sha256": value["contact_sheet_sha256"],
        }
    return canonical_sha256({
        "schema_version": "1", "experiment_id": request["experiment_id"], "stage": request["stage"],
        "request_id": request["request_id"], "pair_id": request["pair_id"],
        "method": request["method"], "direction": request["comparison_direction"],
        "candidate_a_id": request["candidate_a_id"], "candidate_b_id": request["candidate_b_id"],
        "source": media(request["source"]), "candidate_a": media(request["candidate_a"]),
        "candidate_b": media(request["candidate_b"]), "packet": request["media_packet_checksum"],
        "runtime": request["runtime_fingerprint"], "model": request["model_manifest_sha256"],
        "prompt": request["prompt_checksum"], "protocol": request["e1_protocol_fingerprint"],
        "reward": request["reward_artifact_sha256"],
    })


def _plan(
    pairs: List[E2PairV1], manifest: MediaManifestV2, method: str, stage: str,
    prompt_spec: Any, prompt_sha: str, runtime: Any, runtime_sha: str,
    protocol_sha: str, reward_sha: str, snapshot: str,
) -> List[dict]:
    requests: List[dict] = []
    for pair in pairs:
        packet = manifest.pairs[pair.pair_id]
        canonical_assets = [
            (pair.candidate_a.candidate_id, manifest.candidates[pair.candidate_a.candidate_id]),
            (pair.candidate_b.candidate_id, manifest.candidates[pair.candidate_b.candidate_id]),
        ]
        for direction in ("a_vs_b", "b_vs_a"):
            screen = canonical_assets if direction == "a_vs_b" else list(reversed(canonical_assets))
            request = {
                "schema_version": "1", "experiment_id": "E2-bon-pilot-v01", "stage": stage,
                "split": "e2-pilot", "request_id": f"{stage}:{method}:{pair.pair_id}:{direction}",
                "judge_key": "0" * 64, "pair_id": pair.pair_id, "sample_id": pair.sample_id,
                "task_type": pair.task_type, "instruction": pair.instruction,
                "target_caption": pair.target_caption, "method": method,
                "comparison_direction": direction, "candidate_a_id": screen[0][0],
                "candidate_b_id": screen[1][0], "source": _request_media(manifest.sources[pair.sample_id]).model_dump(mode="json"),
                "candidate_a": _request_media(screen[0][1]).model_dump(mode="json"),
                "candidate_b": _request_media(screen[1][1]).model_dump(mode="json"),
                "mask_overlay": packet.mask_overlay.model_dump(mode="json") if packet.mask_overlay else None,
                "media_packet_checksum": packet.packet_checksum, "backend": runtime.backend,
                "model_name": runtime.model.name, "model_revision": runtime.model.revision,
                "model_manifest_sha256": runtime.model.manifest_sha256,
                "prompt_version": prompt_spec.prompt_version, "prompt_checksum": prompt_sha,
                "rendered_prompt": render_prompt(prompt_spec, pair.instruction, pair.target_caption),
                "parser_version": prompt_spec.parser_version,
                "generation_parameters": prompt_spec.generation_parameters,
                "runtime_fingerprint": runtime_sha, "e1_protocol_fingerprint": protocol_sha,
                "reward_artifact_sha256": reward_sha, "code_snapshot": snapshot,
            }
            request["judge_key"] = _judge_key(request)
            requests.append(E2JudgeRequestV1.model_validate(request).model_dump(mode="json"))
    if len(requests) != 560 or len({item["judge_key"] for item in requests}) != 560:
        raise ValueError(f"E2 {stage} plan must contain 560 unique requests")
    return requests


def _dependencies(
    decision_path: Path, reward_path: Path, frozen_config: Path,
    frozen_protocol: Path, runtime_path: Path, auxiliary_path: Optional[Path],
) -> dict:
    decision = read_json(decision_path)
    reward = yaml.safe_load(Path(reward_path).read_text(encoding="utf-8"))
    protocol = FrozenProtocolV2.model_validate(read_json(frozen_protocol))
    runtime = load_runtime_config(runtime_path)
    config_data = validate_config(frozen_config)
    decision_gates = decision.get("gates")
    if (
        decision.get("decision") != "PASS_PROVISIONAL"
        or not isinstance(decision_gates, dict)
        or set(decision_gates) != RELIABILITY_GATES
        or any(decision_gates[name] is not True for name in RELIABILITY_GATES)
    ):
        raise ValueError("E2 preparation requires E1 PASS_PROVISIONAL with all gates true")
    selected = decision.get("selected_method")
    if selected not in {"pairwise-swap-v1", "rubric-swap-v1"}:
        raise ValueError("E2 primary method must be a frozen swap method")
    if reward.get("provisional") is not True or reward.get("method") != selected or protocol.selected_method != selected:
        raise ValueError("E1 decision/reward/protocol selected method mismatch")
    frozen_selection = config_data.get("frozen_selection", {})
    if frozen_selection.get("selected_method") != selected:
        raise ValueError("frozen config selection mismatch")
    if protocol.config_checksum != sha256_file(frozen_config):
        raise ValueError("frozen protocol config checksum mismatch")
    runtime_sha = runtime_fingerprint(runtime)
    if runtime_sha != protocol.runtime_fingerprint:
        raise ValueError("frozen runtime fingerprint mismatch")
    if reward.get("model_revision") != runtime.model.revision:
        raise ValueError("reward model revision mismatch")
    prompt_specs = {}
    prompt_checksums = {}
    for method, method_config in config_data["methods"].items():
        prompt_path = Path(frozen_config).parent / method_config["prompt"]
        prompt_spec, prompt_sha = load_prompt(prompt_path)
        if prompt_spec.method != method:
            raise ValueError(f"frozen prompt method mismatch for {method}")
        prompt_specs[method] = (prompt_spec, prompt_sha)
        prompt_checksums[method] = prompt_sha
    if protocol.prompt_checksums != prompt_checksums:
        raise ValueError("frozen protocol prompt checksums mismatch")
    expected_protocol_fingerprint = frozen_protocol_fingerprint(
        frozen_config, config_data, prompt_checksums, runtime_sha, protocol.code_snapshot,
    )
    if expected_protocol_fingerprint != protocol.protocol_fingerprint:
        raise ValueError("frozen protocol fingerprint mismatch")
    prompt_spec, prompt_sha = prompt_specs[selected]
    if (
        reward.get("prompt_version") != prompt_spec.prompt_version
        or reward.get("prompt_checksum") != prompt_sha
        or reward.get("parser_version") != prompt_spec.parser_version
        or protocol.prompt_checksums.get(selected) != prompt_sha
    ):
        raise ValueError("reward/frozen primary prompt identity mismatch")
    try:
        reward_thresholds = (
            float(reward["confidence_threshold"]),
            float(reward["absolute_delta_threshold"]),
        )
        config_thresholds = (
            float(frozen_selection["confidence_threshold"]),
            float(frozen_selection["absolute_delta_threshold"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("E1 frozen thresholds are missing or invalid") from exc
    protocol_thresholds = (protocol.confidence_threshold, protocol.absolute_delta_threshold)
    if reward_thresholds != protocol_thresholds or config_thresholds != protocol_thresholds:
        raise ValueError("E1 reward/config/protocol frozen threshold mismatch")
    auxiliary = None
    if auxiliary_path is not None:
        auxiliary = yaml.safe_load(Path(auxiliary_path).read_text(encoding="utf-8"))
        auxiliary_gates = auxiliary.get("gates")
        if (
            auxiliary.get("decision") != "PASS_AUXILIARY_RUBRIC"
            or auxiliary.get("method") != "rubric-swap-v1"
            or auxiliary.get("e1_protocol_fingerprint") != protocol.protocol_fingerprint
            or not isinstance(auxiliary_gates, dict)
            or set(auxiliary_gates) != RELIABILITY_GATES
            or any(auxiliary_gates[name] is not True for name in RELIABILITY_GATES)
        ):
            raise ValueError("auxiliary rubric artifact is not qualified for this E1 protocol")
    return {
        "decision": decision, "reward": reward, "protocol": protocol, "runtime": runtime,
        "runtime_sha": runtime_sha, "config_data": config_data, "primary_prompt": (prompt_spec, prompt_sha),
        "auxiliary": auxiliary,
    }


def _verify_prepublication(root: Path, final_root: Path, pairs: List[E2PairV1], trials: List[BonTrialV1], manifest: MediaManifestV2, primary: List[dict], auxiliary: Optional[List[dict]]) -> dict:
    failures: List[str] = []
    if len(pairs) != 280: failures.append("pairs_count")
    if len(trials) != 80: failures.append("trials_count")
    if len(manifest.sources) != 10 or len(manifest.candidates) != 80 or len(manifest.pairs) != 280:
        failures.append("manifest_counts")
    if len(primary) != 560: failures.append("primary_plan_count")
    if auxiliary is not None and len(auxiliary) != 560: failures.append("auxiliary_plan_count")
    declared_files: List[MediaFileV2] = []
    for asset in list(manifest.sources.values()) + list(manifest.candidates.values()):
        declared_files.extend([asset.video, asset.contact_sheet, *asset.frames])
    declared_files.extend(packet.mask_overlay for packet in manifest.pairs.values() if packet.mask_overlay)
    for item in declared_files:
        declared = Path(item.path)
        try:
            physical = root / declared.relative_to(final_root)
        except ValueError:
            failures.append(f"path_outside_final:{declared}")
            continue
        if not physical.is_file() or sha256_file(physical) != item.sha256:
            failures.append(f"media_identity:{declared}")
    return {
        "schema_version": "1", "status": "passed" if not failures else "failed",
        "ready_for_judge": not failures, "verification_context": {
            "mode": "prepublish-staging", "declared_root": str(final_root), "physical_root": str(root),
        },
        "counts": {"pairs": len(pairs), "trials": len(trials), "sources": len(manifest.sources),
                   "candidates": len(manifest.candidates), "packets": len(manifest.pairs),
                   "primary_requests": len(primary), "auxiliary_requests": len(auxiliary or [])},
        "failures": failures, "research_measurements": 0,
    }


def _write_checksums(root: Path) -> Path:
    target = root / "PREPARATION_SHA256SUMS"
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item != target):
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    target.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return target


def prepare_e2(
    pool_path: Path, config_path: Path, decision_path: Path, reward_path: Path,
    frozen_config: Path, frozen_protocol: Path, runtime_path: Path,
    output_root: Path, prepare_id: str, auxiliary_rubric: Optional[Path] = None,
) -> dict:
    if not PREPARE_ID_PATTERN.fullmatch(prepare_id):
        raise ValueError("invalid prepare ID")
    output_root = Path(output_root).resolve()
    parent = output_root.parent
    staging = parent / f".{output_root.name}.prepare-{prepare_id}.staging"
    failure = parent / f"{output_root.name}.prepare-{prepare_id}.failed"
    for path in (output_root, staging, failure):
        if os.path.lexists(path):
            raise FileExistsError(f"E2 preparation path must be absent: {path}")
    stage = "initialize"
    staging.mkdir(parents=True)
    try:
        cfg = load_config(config_path)
        pool = CandidatePoolV1.model_validate(read_json(pool_path))
        if pool.config_sha256 != sha256_file(config_path) or pool.experiment_id != cfg.experiment_id:
            raise ValueError("candidate pool does not match E2 config")
        deps = _dependencies(decision_path, reward_path, frozen_config, frozen_protocol, runtime_path, auxiliary_rubric)
        stage = "pairs-design"
        pairs = _build_pairs(pool, config_path)
        trials = _build_design(pool, config_path)
        input_dir = staging / "inputs"
        _write_jsonl(input_dir / "pairs.jsonl", [pair.model_dump(mode="json") for pair in pairs])
        _write_json(input_dir / "candidate-pool.json", pool.model_dump(mode="json"))
        _write_json(staging / "bon-design.json", {"schema_version": "1", "trials": [trial.model_dump(mode="json") for trial in trials]})
        stage = "media"
        manifest = _build_packets(pairs, pool, input_dir / "media-packets", staging, output_root)
        stage = "plans"
        snapshot = code_snapshot(Path(config_path).resolve().parents[2])
        primary_spec, primary_sha = deps["primary_prompt"]
        primary = _plan(
            pairs, manifest, deps["protocol"].selected_method, "primary", primary_spec, primary_sha,
            deps["runtime"], deps["runtime_sha"], deps["protocol"].protocol_fingerprint,
            sha256_file(reward_path), snapshot,
        )
        plans = staging / "plans"
        _write_jsonl(plans / "judge-plan-primary.jsonl", primary)
        auxiliary = None
        if deps["protocol"].selected_method == "pairwise-swap-v1" and deps["auxiliary"] is not None:
            rubric_path = Path(frozen_config).parent / deps["config_data"]["methods"]["rubric-swap-v1"]["prompt"]
            rubric_spec, rubric_sha = load_prompt(rubric_path)
            if deps["protocol"].prompt_checksums.get("rubric-swap-v1") != rubric_sha:
                raise ValueError("frozen rubric prompt checksum mismatch")
            auxiliary = _plan(
                pairs, manifest, "rubric-swap-v1", "auxiliary-rubric", rubric_spec, rubric_sha,
                deps["runtime"], deps["runtime_sha"], deps["protocol"].protocol_fingerprint,
                sha256_file(auxiliary_rubric), snapshot,
            )
            _write_jsonl(plans / "judge-plan-auxiliary-rubric.jsonl", auxiliary)
        for directory in (staging / "human", staging / "runs", staging / "logs"):
            directory.mkdir()
        shutil.copy2(runtime_path, staging / "runtime-frozen.yaml")
        stage = "verify"
        report = _verify_prepublication(staging, output_root, pairs, trials, manifest, primary, auxiliary)
        _write_json(staging / "preparation-verification-v01.json", report)
        if report["status"] != "passed":
            raise ValueError(f"E2 prepublish verification failed: {report['failures']}")
        receipt = {
            "schema_version": "1", "status": "passed", "prepare_id": prepare_id,
            "created_at": _utc_now(), "experiment_id": cfg.experiment_id,
            "code_snapshot": snapshot, "candidate_pool_sha256": sha256_file(pool_path),
            "e1_decision_sha256": sha256_file(decision_path), "reward_v0_sha256": sha256_file(reward_path),
            "frozen_protocol_sha256": sha256_file(frozen_protocol), "runtime_fingerprint": deps["runtime_sha"],
            "selected_method": deps["protocol"].selected_method,
            "auxiliary_rubric": "qualified" if auxiliary else ("primary" if deps["protocol"].selected_method == "rubric-swap-v1" else "NOT_APPLICABLE"),
            "counts": report["counts"], "research_measurements": 0,
        }
        _write_json(staging / "e2-preparation-v01.json", receipt)
        _write_checksums(staging)
        stage = "publish"
        _rename_noreplace(staging, output_root)
        return {"status": "passed", "output_root": str(output_root), **receipt}
    except Exception as exc:
        marker = {"schema_version": "1", "status": "failed", "stage": stage, "error": f"{type(exc).__name__}: {exc}", "at": _utc_now()}
        try:
            _write_json(staging / "PREPARATION_FAILED.json", marker)
            _rename_noreplace(staging, failure)
            raise E2PreparationError(stage, str(exc), failure_root=failure) from exc
        except E2PreparationError:
            raise
        except Exception as preserve_exc:
            raise E2PreparationError(stage, f"{exc}; failed to preserve staging: {preserve_exc}", staging_root=staging) from exc
