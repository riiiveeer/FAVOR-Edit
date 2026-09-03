"""Deterministic random, equal-linear, and constrained Pareto selection."""

from __future__ import annotations

import json
import math
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .config import load_config
from .design import load_metric_rows
from .io import rename_noreplace, write_json


DIMENSIONS = ("F", "P", "T", "Q")
METHODS = ("random", "equal-linear", "constrained-pareto")


def rank_percentiles(
    candidate_ids: Sequence[str], score_by_id: Dict[str, Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    candidates = list(candidate_ids)
    if not candidates or len(candidates) != len(set(candidates)):
        raise ValueError("rank percentiles require non-empty unique candidates")
    utilities = {candidate: {} for candidate in candidates}
    for dimension in DIMENSIONS:
        if any(dimension not in score_by_id.get(candidate, {}) for candidate in candidates):
            raise ValueError(f"one or more candidates lack dimension {dimension}")
        ordered = sorted(candidates, key=lambda candidate: (
            score_by_id[candidate][dimension], candidate,
        ))
        denominator = len(ordered) - 1
        for index, candidate in enumerate(ordered):
            utilities[candidate][dimension] = 1.0 if denominator == 0 else index / denominator
    return utilities


def _pareto_front(
    candidate_ids: Sequence[str], utilities: Dict[str, Dict[str, float]]
) -> List[str]:
    frontier = []
    for candidate in candidate_ids:
        vector = utilities[candidate]
        dominated = any(
            other != candidate
            and all(utilities[other][dimension] >= vector[dimension] for dimension in DIMENSIONS)
            and any(utilities[other][dimension] > vector[dimension] for dimension in DIMENSIONS)
            for other in candidate_ids
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier)


def constrained_pareto_choice(
    candidate_ids: Sequence[str], utilities: Dict[str, Dict[str, float]]
) -> Tuple[str, Dict[str, Any]]:
    candidates = sorted(candidate_ids)
    if not candidates:
        raise ValueError("constrained Pareto selection requires candidates")
    f_threshold = float(np.quantile(
        [utilities[candidate]["F"] for candidate in candidates], 0.5, method="linear"
    ))
    p_threshold = float(np.quantile(
        [utilities[candidate]["P"] for candidate in candidates], 0.25, method="linear"
    ))
    feasible = [
        candidate for candidate in candidates
        if utilities[candidate]["F"] >= f_threshold
        and utilities[candidate]["P"] >= p_threshold
    ]
    fallback = not feasible
    if fallback:
        chosen = sorted(candidates, key=lambda candidate: (
            -min(utilities[candidate]["F"], utilities[candidate]["P"]),
            -utilities[candidate]["T"], -utilities[candidate]["Q"], candidate,
        ))[0]
        frontier: List[str] = []
    else:
        frontier = _pareto_front(feasible, utilities)
        chosen = sorted(frontier, key=lambda candidate: (
            -min(utilities[candidate].values()),
            -math.prod(utilities[candidate][dimension] for dimension in DIMENSIONS) ** 0.25,
            candidate,
        ))[0]
    return chosen, {
        "f_threshold": f_threshold, "p_threshold": p_threshold,
        "feasible_candidate_ids": feasible, "pareto_frontier_candidate_ids": frontier,
        "fallback": fallback,
    }


def _random_choice(subset: Sequence[str], seed: int, trial_id: str, n: int) -> str:
    digest = canonical_sha256({
        "seed": seed, "trial_id": trial_id, "n": n, "method": "random",
    })
    return list(subset)[int(digest, 16) % len(subset)]


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_sums(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    rows = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "SELECTION_SHA256SUMS").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )


def select_design(
    design_path: Path, metrics_path: Path, config_path: Path, output: Path
) -> Dict[str, Any]:
    design_path, metrics_path, config_path, output = (
        Path(design_path).resolve(), Path(metrics_path).resolve(),
        Path(config_path).resolve(), Path(output).resolve(),
    )
    if os.path.lexists(output):
        raise FileExistsError(f"selection output already exists: {output}")
    cfg = load_config(config_path)
    rows = load_metric_rows(metrics_path, config_path)
    scored = {row["candidate_id"]: row for row in rows if row["measurement_status"] == "scored"}
    design = json.loads(design_path.read_text(encoding="utf-8"))
    if design.get("metrics_sha256") != sha256_file(metrics_path):
        raise ValueError("design/metrics identity mismatch")
    trials = design.get("trials")
    if not isinstance(trials, list) or len(trials) != 35:
        raise ValueError("selection requires exactly 35 design trials")
    sample_metadata = {item["sample_id"]: item for item in design.get("samples", [])}
    selections = []
    lookup: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
    for trial in trials:
        order = trial["candidate_order"]
        if len(order) != 5 or len(set(order)) != 5:
            raise ValueError(f"trial order invalid: {trial.get('trial_id')}")
        for n in cfg.n_values:
            subset = trial["subsets"].get(str(n))
            if subset != order[:n]:
                raise ValueError(f"trial prefix invalid: {trial['trial_id']} N={n}")
            raw_scores = {candidate: scored[candidate]["scores"] for candidate in subset}
            utilities = rank_percentiles(subset, raw_scores)
            random_candidate = _random_choice(
                subset, cfg.randomization_seed, trial["trial_id"], n
            )
            linear_candidate = sorted(subset, key=lambda candidate: (
                -sum(utilities[candidate].values()) / len(DIMENSIONS), candidate,
            ))[0]
            pareto_candidate, pareto_audit = constrained_pareto_choice(subset, utilities)
            choices = {
                "random": (random_candidate, {}),
                "equal-linear": (linear_candidate, {
                    "linear_score": sum(utilities[linear_candidate].values()) / len(DIMENSIONS),
                }),
                "constrained-pareto": (pareto_candidate, pareto_audit),
            }
            for method in METHODS:
                candidate, audit = choices[method]
                record = {
                    "schema_version": "1", "trial_id": trial["trial_id"],
                    "sample_id": trial["sample_id"], "replicate": trial["replicate"],
                    "n": n, "method": method, "subset_candidate_ids": subset,
                    "candidate_id": candidate,
                    "candidate_video_sha256": scored[candidate]["candidate_video_sha256"],
                    "raw_scores": raw_scores[candidate],
                    "rank_percentiles": utilities[candidate],
                    "audit": audit,
                }
                selections.append(record)
                lookup[(trial["trial_id"], n, method)] = record
    if len(selections) != 315:
        raise ValueError("selection must contain exactly 315 records")

    comparisons = []
    for trial in trials:
        sample = sample_metadata[trial["sample_id"]]
        media = {item["candidate_id"]: item["video"] for item in sample["candidates"]}
        specs = []
        if trial["replicate"] <= cfg.n4_vs_n1_replicates:
            specs.append((
                "proposed-n4-vs-n1", 4, "constrained-pareto", 1, "constrained-pareto",
            ))
        if trial["replicate"] <= cfg.pareto_vs_linear_replicates:
            specs.append((
                "proposed-vs-linear-n4", 4, "constrained-pareto", 4, "equal-linear",
            ))
        for family, n_x, method_x, n_y, method_y in specs:
            x = lookup[(trial["trial_id"], n_x, method_x)]
            y = lookup[(trial["trial_id"], n_y, method_y)]
            comparisons.append({
                "schema_version": "1",
                "comparison_id": f"defense:{family}:{trial['sample_id']}:r{trial['replicate']}",
                "family": family, "trial_id": trial["trial_id"],
                "sample_id": trial["sample_id"], "replicate": trial["replicate"],
                "instruction": sample["instruction"], "target_caption": sample["target_caption"],
                "source_video": sample["source_video"],
                "candidate_x": {
                    "role": f"{method_x}-n{n_x}", "candidate_id": x["candidate_id"],
                    "video": media[x["candidate_id"]],
                },
                "candidate_y": {
                    "role": f"{method_y}-n{n_y}", "candidate_id": y["candidate_id"],
                    "video": media[y["candidate_id"]],
                },
                "identical_selection": x["candidate_video_sha256"] == y["candidate_video_sha256"],
            })
    if len(comparisons) != 42 or len({item["comparison_id"] for item in comparisons}) != 42:
        raise ValueError("blind comparison plan must contain exactly 42 unique comparisons")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.select-{uuid.uuid4().hex}.staging"
    failed = output.parent / f".{output.name}.select-{uuid.uuid4().hex}.failed"
    staging.mkdir()
    try:
        selections_path = staging / "selections.jsonl"
        comparisons_path = staging / "comparisons.json"
        _write_jsonl(selections_path, selections)
        write_json(comparisons_path, {
            "schema_version": "1", "experiment_id": "DEFENSE-MVP-v01",
            "delivery_root": design["delivery_root"], "comparisons": comparisons,
        })
        summary = {
            "schema_version": "1", "status": "passed", "ready_for_annotation": True,
            "selection_records": 315, "comparisons": 42,
            "n4_vs_n1_comparisons": sum(
                item["family"] == "proposed-n4-vs-n1" for item in comparisons
            ),
            "pareto_vs_linear_comparisons": sum(
                item["family"] == "proposed-vs-linear-n4" for item in comparisons
            ),
            "automatic_ties": sum(item["identical_selection"] for item in comparisons),
            "pareto_fallbacks": sum(
                item["method"] == "constrained-pareto" and item["audit"].get("fallback") is True
                for item in selections
            ),
            "selections_sha256": sha256_file(selections_path),
            "comparisons_sha256": sha256_file(comparisons_path),
        }
        write_json(staging / "selection-summary.json", summary)
        write_json(staging / "selection-lock.json", {
            "schema_version": "1", "config_sha256": sha256_file(config_path),
            "metrics_sha256": sha256_file(metrics_path),
            "design_sha256": sha256_file(design_path),
            "selections_sha256": summary["selections_sha256"],
            "comparisons_sha256": summary["comparisons_sha256"],
        })
        _write_sums(staging)
        rename_noreplace(staging, output)
        return summary
    except Exception as exc:
        if staging.exists():
            write_json(staging / "SELECTION_FAILED.json", {
                "status": "failed", "error": str(exc),
            })
            rename_noreplace(staging, failed)
        raise
