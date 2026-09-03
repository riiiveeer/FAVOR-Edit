"""Balanced cyclic N=1/2/4 design for the Defense MVP."""

from __future__ import annotations

import json
import math
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Sequence

from w1_pipeline.hashing import sha256_file

from .config import load_config
from .io import rename_noreplace, write_json
from .models import PackageCandidateV1, PackageSampleV1


def load_metric_rows(metrics_path: Path, config_path: Path) -> List[Dict[str, Any]]:
    cfg = load_config(config_path)
    rows = [
        json.loads(line) for line in Path(metrics_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 50 or len({row.get("candidate_id") for row in rows}) != 50:
        raise ValueError("metrics must contain exactly 50 unique candidates")
    expected = [
        (sample_id, seed) for sample_id in cfg.sample_ids for seed in cfg.seeds
    ]
    if [(row.get("sample_id"), row.get("seed")) for row in rows] != expected:
        raise ValueError("metrics candidate matrix/order drifted")
    for row in rows:
        primary = row["sample_id"] in cfg.primary_sample_ids
        expected_status = "scored" if primary else "qualitative_only"
        if row.get("measurement_status") != expected_status:
            raise ValueError(f"metric status drifted: {row.get('candidate_id')}")
        if primary:
            scores = row.get("scores")
            if not isinstance(scores, dict) or set(scores) != {"F", "P", "T", "Q"}:
                raise ValueError(f"metric dimensions incomplete: {row['candidate_id']}")
            if any(
                not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1
                for value in scores.values()
            ):
                raise ValueError(f"metric value invalid: {row['candidate_id']}")
    return rows


def cyclic_trials(sample_id: str, candidate_ids: Sequence[str]) -> List[Dict[str, Any]]:
    if len(candidate_ids) != 5 or len(set(candidate_ids)) != 5:
        raise ValueError("cyclic design requires exactly five unique candidates")
    base = list(candidate_ids)
    trials = []
    for index in range(5):
        order = base[index:] + base[:index]
        trials.append({
            "trial_id": f"defense:{sample_id}:r{index + 1}",
            "sample_id": sample_id,
            "replicate": index + 1,
            "candidate_order": order,
            "subsets": {"1": order[:1], "2": order[:2], "4": order[:4]},
        })
    return trials


def _write_sums(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    rows = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "DESIGN_SHA256SUMS").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )


def create_design(
    metrics_path: Path, ingest_manifest: Path, config_path: Path, output: Path
) -> Dict[str, Any]:
    metrics_path, ingest_manifest, config_path, output = (
        Path(metrics_path).resolve(), Path(ingest_manifest).resolve(),
        Path(config_path).resolve(), Path(output).resolve(),
    )
    if os.path.lexists(output):
        raise FileExistsError(f"design output already exists: {output}")
    cfg = load_config(config_path)
    rows = load_metric_rows(metrics_path, config_path)
    metric_by_id = {row["candidate_id"]: row for row in rows}
    ingest = json.loads(ingest_manifest.read_text(encoding="utf-8"))
    samples = [PackageSampleV1.model_validate(item) for item in ingest.get("samples", [])]
    candidates = [PackageCandidateV1.model_validate(item) for item in ingest.get("candidates", [])]
    if [item.sample_id for item in samples] != cfg.sample_ids or len(candidates) != 50:
        raise ValueError("ingest identity is incomplete for design")
    for candidate in candidates:
        metric = metric_by_id.get(candidate.candidate_id)
        if metric is None or metric["candidate_video_sha256"] != candidate.video.sha256:
            raise ValueError(f"metrics/ingest candidate identity mismatch: {candidate.candidate_id}")

    candidate_by_sample: Dict[str, List[PackageCandidateV1]] = {}
    for candidate in candidates:
        candidate_by_sample.setdefault(candidate.sample_id, []).append(candidate)
    trials = []
    for sample_id in cfg.primary_sample_ids:
        sample_candidates = candidate_by_sample[sample_id]
        if [item.seed for item in sample_candidates] != cfg.seeds:
            raise ValueError(f"candidate seed order drifted: {sample_id}")
        trials.extend(cyclic_trials(sample_id, [item.candidate_id for item in sample_candidates]))
    if len(trials) != 35:
        raise ValueError("design must contain exactly 35 trials")

    sample_by_id = {item.sample_id: item for item in samples}
    sample_metadata = []
    for sample_id in cfg.primary_sample_ids:
        sample = sample_by_id[sample_id]
        sample_metadata.append({
            "sample_id": sample_id, "instruction": sample.instruction,
            "target_caption": sample.target_caption,
            "source_video": sample.source_video.model_dump(mode="json"),
            "candidates": [
                {
                    "candidate_id": item.candidate_id, "seed": item.seed,
                    "video": item.video.model_dump(mode="json"),
                }
                for item in candidate_by_sample[sample_id]
            ],
        })
    payload = {
        "schema_version": "1", "experiment_id": "DEFENSE-MVP-v01",
        "design": "five-cyclic-prefix-v1", "randomization_seed": cfg.randomization_seed,
        "n_values": cfg.n_values, "replicates": cfg.replicates,
        "metrics_sha256": sha256_file(metrics_path),
        "ingest_manifest_sha256": sha256_file(ingest_manifest),
        "delivery_root": ingest["delivery_root"],
        "samples": sample_metadata, "trials": trials,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.design-{uuid.uuid4().hex}.staging"
    failed = output.parent / f".{output.name}.design-{uuid.uuid4().hex}.failed"
    staging.mkdir()
    try:
        design_path = staging / "design.json"
        write_json(design_path, payload)
        lock = {
            "schema_version": "1", "experiment_id": "DEFENSE-MVP-v01",
            "config_sha256": sha256_file(config_path),
            "metrics_sha256": sha256_file(metrics_path),
            "ingest_manifest_sha256": sha256_file(ingest_manifest),
            "design_sha256": sha256_file(design_path),
        }
        write_json(staging / "design-lock.json", lock)
        receipt = {
            "schema_version": "1", "status": "passed", "ready_for_selection": True,
            "samples": 7, "trials": 35, "subsets": 105,
            "design_sha256": lock["design_sha256"],
        }
        write_json(staging / "design-receipt.json", receipt)
        _write_sums(staging)
        rename_noreplace(staging, output)
        return receipt
    except Exception as exc:
        if staging.exists():
            write_json(staging / "DESIGN_FAILED.json", {"status": "failed", "error": str(exc)})
            rename_noreplace(staging, failed)
        raise
