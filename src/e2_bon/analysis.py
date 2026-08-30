"""Tie-aware E2 human analysis, sample-cluster bootstrap, and cost accounting."""

from __future__ import annotations

import json
import math
import os
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from e1_judge.phase3 import _rename_noreplace
from w1_pipeline.hashing import sha256_file

from .config import load_config
from .io import read_json
from .models import (
    CandidatePoolV1,
    E2AdjudicatedComparisonV1,
    E2JudgeResultV1,
    E2SelectionBundleV1,
)

DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")
SCORES = {"n4": 1.0, "n1": 0.0, "tie": 0.5, "uncertain": 0.5}


def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cluster_bootstrap(
    records: Sequence[E2AdjudicatedComparisonV1], field: str, seed: int, iterations: int,
) -> dict:
    by_sample: Dict[str, List[E2AdjudicatedComparisonV1]] = defaultdict(list)
    for record in records:
        by_sample[record.sample_id].append(record)
    samples = sorted(by_sample)
    if len(samples) != 10 or any(len(by_sample[sample]) != 8 for sample in samples):
        raise ValueError("E2 cluster bootstrap requires 10 samples with eight balanced rounds each")
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        selected_clusters = [rng.choice(samples) for _ in samples]
        outcomes = [
            getattr(record, field)
            for sample in selected_clusters
            for record in by_sample[sample]
        ]
        estimates.append(sum(SCORES[outcome] for outcome in outcomes) / len(outcomes))
    lower, upper = np.quantile(np.asarray(estimates, dtype=float), [0.025, 0.975])
    return {
        "method": "sample-cluster-percentile", "clusters": 10, "rounds_per_cluster": 8,
        "seed": seed, "iterations": iterations, "lower": float(lower), "upper": float(upper),
    }


def _outcome_metrics(
    records: Sequence[E2AdjudicatedComparisonV1], field: str, seed: int, iterations: int,
) -> dict:
    values = [getattr(record, field) for record in records]
    counts = Counter(values)
    decisive = counts["n4"] + counts["n1"]
    return {
        "items": len(values), "n4_wins": counts["n4"], "n1_wins": counts["n1"],
        "ties": counts["tie"], "uncertain": counts["uncertain"],
        "tie_aware_win_rate": sum(SCORES[value] for value in values) / len(values),
        "decisive_win_rate": counts["n4"] / decisive if decisive else None,
        "tie_rate": counts["tie"] / len(values), "uncertain_rate": counts["uncertain"] / len(values),
        "bootstrap_95_ci": cluster_bootstrap(records, field, seed, iterations),
        "neutral_imputation": {"tie": 0.5, "uncertain": 0.5},
    }


def _costs(
    pool: CandidatePoolV1, primary: Sequence[E2JudgeResultV1],
    rubric: Sequence[E2JudgeResultV1], n_values: Sequence[int],
) -> dict:
    generation_seconds = sum(float(item.runtime_seconds or 0.0) for item in pool.candidates)
    primary_seconds = sum(item.runtime_seconds for item in primary)
    rubric_seconds = sum(item.runtime_seconds for item in rubric)
    mean_generation = generation_seconds / len(pool.candidates)
    mean_primary = primary_seconds / len(primary)
    theoretical = []
    for n in n_values:
        generated = 10 * 8 * n
        judge_requests = 10 * 8 * math.comb(n, 2) * 2
        theoretical.append({
            "n": n, "generated_candidates": generated, "primary_judge_requests": judge_requests,
            "estimated_generation_seconds": mean_generation * generated,
            "estimated_primary_judge_seconds": mean_primary * judge_requests,
        })
    actual_total = generation_seconds + primary_seconds + rubric_seconds
    return {
        "schema_version": "1", "theoretical_independent_trials": theoretical,
        "actual_shared_eight_candidate_pool": {
            "generated_candidates": len(pool.candidates), "primary_judge_requests": len(primary),
            "auxiliary_rubric_requests": len(rubric), "generation_seconds": generation_seconds,
            "primary_judge_seconds": primary_seconds, "auxiliary_rubric_seconds": rubric_seconds,
            "total_seconds": actual_total, "amortized_seconds_per_balanced_trial": actual_total / 80,
        },
        "notes": [
            "theoretical counts treat each N/trial independently",
            "actual counts reuse one 8-candidate pool and one 28-pair/56-direction cache per sample",
        ],
    }


def analyze_e2(
    config_path: Path, selection_path: Path, adjudicated_path: Path, agreement_report_path: Path,
    pool_path: Path, primary_results_path: Path, output_dir: Path,
    rubric_results_path: Optional[Path] = None,
) -> dict:
    cfg = load_config(config_path)
    selection = E2SelectionBundleV1.model_validate(read_json(selection_path))
    records = [E2AdjudicatedComparisonV1.model_validate(item) for item in _read_jsonl(adjudicated_path)]
    agreement = read_json(agreement_report_path)
    pool = CandidatePoolV1.model_validate(read_json(pool_path))
    primary = [E2JudgeResultV1.model_validate(item) for item in _read_jsonl(primary_results_path)]
    rubric = (
        [E2JudgeResultV1.model_validate(item) for item in _read_jsonl(rubric_results_path)]
        if rubric_results_path else []
    )
    if len(records) != 80 or len({item.comparison_id for item in records}) != 80:
        raise ValueError("E2 analysis requires 80 unique adjudicated comparisons")
    if {item.comparison_id for item in records} != {
        item.comparison_id for item in selection.human_comparisons
    }:
        raise ValueError("E2 adjudicated comparisons do not match selection human plan")
    if len(primary) != 560 or (rubric and len(rubric) != 560):
        raise ValueError("E2 cost analysis requires complete 560-result Judge files")
    if selection.dependencies.get("config_sha256") != sha256_file(config_path):
        raise ValueError("E2 analysis config identity mismatch")
    if selection.dependencies.get("primary_results_sha256") != sha256_file(primary_results_path):
        raise ValueError("E2 analysis primary results identity mismatch")
    expected_rubric_sha = selection.dependencies.get("rubric_results_sha256")
    actual_rubric_sha = sha256_file(rubric_results_path) if rubric_results_path else None
    if expected_rubric_sha != actual_rubric_sha:
        raise ValueError("E2 analysis rubric results identity mismatch")
    pool_identity = {item.candidate_id: item.video_sha256 for item in pool.candidates}
    for item in selection.selections:
        if pool_identity.get(item.candidate_id) != item.candidate_video_sha256:
            raise ValueError("E2 selection candidate/pool checksum identity mismatch")
    if selection.measurement_mode != "formal-command" and selection.research_measurements != 0:
        raise ValueError("mock/replay E2 selection cannot contain research measurements")

    overall = _outcome_metrics(records, "overall_outcome", cfg.bootstrap_seed, cfg.bootstrap_iterations)
    dimensions = {
        dimension: _outcome_metrics(
            records, f"{dimension}_outcome", cfg.bootstrap_seed, cfg.bootstrap_iterations,
        )
        for dimension in DIMENSIONS
    }
    warnings = []
    for dimension in ("faithfulness", "preservation"):
        if dimensions[dimension]["bootstrap_95_ci"]["upper"] < 0.5:
            warnings.append(f"significant_{dimension}_degradation")
    metrics = {
        "schema_version": "1", "experiment_id": cfg.experiment_id,
        "measurement_mode": selection.measurement_mode,
        "research_measurements": selection.research_measurements,
        "human_comparisons": 80,
        "identical_selection_ties": sum(item.automatic_tie for item in records),
        "overall": overall, "dimensions": dimensions,
        "annotation_agreement": agreement.get("agreement", {}),
        "primary_annotators": agreement.get("primary_annotators", []),
        "third_annotator_labels": agreement.get("third_annotator_labels", 0),
        "meets_m1_target": overall["tie_aware_win_rate"] >= 0.60,
        "m1_interpretation": "target flag only; not an automatic statistical-significance claim",
        "warnings": warnings,
        "inputs": {
            "config_sha256": sha256_file(config_path), "selection_sha256": sha256_file(selection_path),
            "adjudicated_sha256": sha256_file(adjudicated_path),
            "agreement_report_sha256": sha256_file(agreement_report_path),
            "pool_sha256": sha256_file(pool_path),
            "primary_results_sha256": sha256_file(primary_results_path),
            "rubric_results_sha256": actual_rubric_sha,
        },
    }
    costs = _costs(pool, primary, rubric, cfg.n_values)
    costs["measurement_mode"] = selection.measurement_mode
    costs["research_measurements"] = selection.research_measurements

    output_dir = Path(output_dir).resolve()
    staging = output_dir.parent / f".{output_dir.name}.analysis.staging"
    failure = output_dir.parent / f"{output_dir.name}.analysis.failed"
    for path in (output_dir, staging, failure):
        if os.path.lexists(path):
            raise FileExistsError(f"E2 analysis path must be absent: {path}")
    staging.mkdir(parents=True)
    try:
        _write_json(staging / "metrics.json", metrics)
        _write_json(staging / "costs.json", costs)
        _rename_noreplace(staging, output_dir)
    except Exception as exc:
        _write_json(staging / "ANALYSIS_FAILED.json", {
            "schema_version": "1", "status": "failed", "error": f"{type(exc).__name__}: {exc}",
        })
        _rename_noreplace(staging, failure)
        raise
    return {"status": "passed", "output_dir": str(output_dir), "metrics": metrics, "costs": costs}
