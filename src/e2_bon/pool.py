"""E2 generation-extension planning and immutable 80-candidate pool assembly."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from w1_pipeline.hashing import canonical_sha256, sha256_file
from w1_pipeline.models import CandidateRecord, GenerationConfig, InputRecord
from w1_pipeline.planning import generation_key

from .config import config_sha256, load_config
from .io import atomic_write_new_json, read_json
from .models import CandidatePoolV1, PoolCandidateV1


def _task_seed(task: Dict[str, Any]) -> int:
    return int(task["config"]["seed"])


def _semantic_generation(config: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in config.items() if key != "seed"}


def _candidate_id(sample_id: str, seed: int) -> str:
    return f"{sample_id}-s{seed}"


def _load_plan(path: Path) -> Tuple[List[dict], List[dict]]:
    value = read_json(path)
    if not isinstance(value, dict) or set(value) != {"inversions", "candidates"}:
        raise ValueError("generation plan must contain exactly inversions and candidates")
    if not isinstance(value["inversions"], list) or not isinstance(value["candidates"], list):
        raise ValueError("generation plan entries must be lists")
    return value["inversions"], value["candidates"]


def plan_generation_extension(
    e0_plan: Path,
    config: Path,
    output: Path,
    snapshot: str,
) -> Dict[str, List[dict]]:
    """Create a W1-runner-compatible plan for exactly 30 new seed tasks."""
    if not snapshot.strip():
        raise ValueError("snapshot must be non-empty")
    cfg = load_config(config)
    inversions, tasks = _load_plan(e0_plan)
    if len(inversions) != 10 or len(tasks) != 50:
        raise ValueError("E0 plan must contain 10 inversions and 50 candidate tasks")
    by_sample: Dict[str, List[dict]] = defaultdict(list)
    for task in tasks:
        by_sample[str(task["sample_id"])].append(task)
    if set(by_sample) != set(cfg.sample_ids):
        raise ValueError("E0 plan sample IDs do not match E2 config")

    extension: List[dict] = []
    for sample_id in cfg.sample_ids:
        base = sorted(by_sample[sample_id], key=_task_seed)
        if [_task_seed(item) for item in base] != cfg.base_seeds:
            raise ValueError(f"sample {sample_id} does not contain the fixed five E0 seeds")
        semantic = _semantic_generation(base[0]["config"])
        first_input = base[0]["input"]
        for task in base[1:]:
            if _semantic_generation(task["config"]) != semantic or task["input"] != first_input:
                raise ValueError(f"sample {sample_id} has generation or input drift in E0 plan")
        input_record = InputRecord.model_validate(first_input)
        for seed in cfg.extension_seeds:
            generation = GenerationConfig.model_validate({**semantic, "seed": seed})
            extension.append({
                "candidate_id": _candidate_id(sample_id, seed),
                "sample_id": sample_id,
                "generation_key": generation_key(input_record, generation, snapshot),
                "input": input_record.model_dump(mode="json"),
                "config": generation.model_dump(mode="json"),
                "artifact_dir": f"candidates/{sample_id}/seed-{seed}",
                "code_snapshot": snapshot,
            })
    if len(extension) != 30 or len({item["candidate_id"] for item in extension}) != 30:
        raise ValueError("extension plan must contain 30 unique candidate tasks")
    payload = {"inversions": inversions, "candidates": extension}
    atomic_write_new_json(output, payload)
    return payload


def _load_audit(path: Path, expected: int, field: str) -> Dict[str, dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != expected or len({row.get("candidate_id") for row in rows}) != expected:
        raise ValueError(f"audit must contain {expected} unique candidate rows")
    if any(row.get(field) != "yes" for row in rows):
        raise ValueError(f"all audit rows must have {field}=yes")
    return {str(row["candidate_id"]): row for row in rows}


def _validate_media(candidate: CandidateRecord, verify_files: bool) -> None:
    if candidate.status.value != "succeeded":
        raise ValueError(f"candidate {candidate.candidate_id} is not succeeded")
    if not candidate.video_path or not candidate.video_checksum:
        raise ValueError(f"candidate {candidate.candidate_id} is missing video identity")
    if len(candidate.frame_paths) != 16 or len(candidate.frame_checksums) != 16:
        raise ValueError(f"candidate {candidate.candidate_id} must contain 16 frame identities")
    if verify_files:
        video = Path(candidate.video_path)
        frames = [Path(item) for item in candidate.frame_paths]
        if not video.is_file() or sha256_file(video) != candidate.video_checksum:
            raise ValueError(f"candidate {candidate.candidate_id} video checksum mismatch")
        if not all(path.is_file() for path in frames):
            raise ValueError(f"candidate {candidate.candidate_id} frame is missing")
        if [sha256_file(path) for path in frames] != candidate.frame_checksums:
            raise ValueError(f"candidate {candidate.candidate_id} frame checksum mismatch")


def _records(path: Path, expected: int) -> Dict[str, CandidateRecord]:
    values = read_json(path)
    if not isinstance(values, list) or len(values) != expected:
        raise ValueError(f"candidate manifest must contain {expected} records")
    records = [CandidateRecord.model_validate(item) for item in values]
    if len({item.candidate_id for item in records}) != expected:
        raise ValueError("candidate manifest IDs must be unique")
    return {item.candidate_id: item for item in records}


def _pool_record(task: dict, candidate: CandidateRecord, origin: str) -> PoolCandidateV1:
    return PoolCandidateV1(
        candidate_id=candidate.candidate_id,
        sample_id=candidate.sample_id,
        seed=int(candidate.config.seed),
        origin=origin,
        generation_key=candidate.generation_key,
        generation_config=candidate.config.model_dump(mode="json"),
        input=task["input"],
        artifact_dir=candidate.artifact_dir,
        video_path=str(candidate.video_path),
        video_sha256=str(candidate.video_checksum),
        frame_paths=list(candidate.frame_paths),
        frame_sha256=list(candidate.frame_checksums),
        code_snapshot=candidate.code_snapshot,
        runtime_seconds=candidate.runtime_seconds,
        peak_vram_mb=candidate.peak_vram_mb,
    )


def build_candidate_pool(
    e0_plan: Path,
    e0_candidates: Path,
    e0_audit: Path,
    extension_plan: Path,
    extension_candidates: Path,
    extension_audit: Path,
    config: Path,
    output: Path,
    verify_files: bool = True,
) -> Dict[str, Any]:
    cfg = load_config(config)
    _, base_tasks = _load_plan(e0_plan)
    _, extension_tasks = _load_plan(extension_plan)
    if len(base_tasks) != 50 or len(extension_tasks) != 30:
        raise ValueError("E2 pool requires 50 base and 30 extension tasks")
    task_groups = (("e0", base_tasks, cfg.base_seeds), ("extension", extension_tasks, cfg.extension_seeds))
    task_by_id: Dict[str, Tuple[str, dict]] = {}
    for origin, tasks, _ in task_groups:
        for task in tasks:
            candidate_id = str(task["candidate_id"])
            if candidate_id in task_by_id:
                raise ValueError(f"duplicate task candidate ID: {candidate_id}")
            task_by_id[candidate_id] = (origin, task)

    records = {**_records(e0_candidates, 50), **_records(extension_candidates, 30)}
    if len(records) != 80 or set(records) != set(task_by_id):
        raise ValueError("plan and candidate manifest IDs must match exactly")
    base_audit = _load_audit(e0_audit, 50, "usable_for_e1")
    extension_audit_rows = _load_audit(extension_audit, 30, "usable_for_e2")
    if set(base_audit) | set(extension_audit_rows) != set(records):
        raise ValueError("audit and candidate IDs must match exactly")

    pool_records: List[PoolCandidateV1] = []
    by_sample: Dict[str, List[PoolCandidateV1]] = defaultdict(list)
    for candidate_id in sorted(records):
        origin, task = task_by_id[candidate_id]
        record = records[candidate_id]
        if record.sample_id != task["sample_id"] or record.generation_key != task["generation_key"]:
            raise ValueError(f"candidate {candidate_id} task identity mismatch")
        if record.config.model_dump(mode="json") != task["config"]:
            raise ValueError(f"candidate {candidate_id} generation config mismatch")
        _validate_media(record, verify_files)
        pooled = _pool_record(task, record, origin)
        by_sample[pooled.sample_id].append(pooled)
        pool_records.append(pooled)

    if set(by_sample) != set(cfg.sample_ids):
        raise ValueError("candidate pool sample IDs do not match E2 config")
    for sample_id, items in by_sample.items():
        ordered = sorted(items, key=lambda item: item.seed)
        if [item.seed for item in ordered] != cfg.all_seeds:
            raise ValueError(f"sample {sample_id} does not contain the fixed eight seeds")
        semantic = _semantic_generation(ordered[0].generation_config)
        reference_input = ordered[0].input
        for item in ordered[1:]:
            if _semantic_generation(item.generation_config) != semantic or item.input != reference_input:
                raise ValueError(f"sample {sample_id} generation/input drift across the eight-candidate pool")

    serialized = [item.model_dump(mode="json") for item in sorted(pool_records, key=lambda item: item.candidate_id)]
    fingerprint = canonical_sha256({
        "schema_version": "1",
        "experiment_id": cfg.experiment_id,
        "config_sha256": config_sha256(config),
        "candidates": serialized,
    })
    payload = CandidatePoolV1(
        experiment_id=cfg.experiment_id,
        config_sha256=config_sha256(config),
        e0_plan_sha256=sha256_file(e0_plan),
        e0_candidates_sha256=sha256_file(e0_candidates),
        e0_audit_sha256=sha256_file(e0_audit),
        extension_plan_sha256=sha256_file(extension_plan),
        extension_candidates_sha256=sha256_file(extension_candidates),
        extension_audit_sha256=sha256_file(extension_audit),
        pool_fingerprint=fingerprint,
        candidate_count=80,
        sample_count=10,
        candidates=serialized,
    ).model_dump(mode="json")
    atomic_write_new_json(output, payload)
    return payload
