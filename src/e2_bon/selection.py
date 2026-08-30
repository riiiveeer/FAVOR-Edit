"""Deterministic E2 Best-of-N selection from frozen, swap-consistent Judge results."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import yaml

from e1_judge.hashing import canonical_sha256
from w1_pipeline.hashing import sha256_file

from .config import load_config
from .io import atomic_write_new_json, read_json
from .models import (
    BonTrialV1,
    E2HumanComparisonV1,
    E2JudgeResultV1,
    E2PairV1,
    E2SelectionBundleV1,
    E2SelectionV1,
)

DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")
RELIABILITY_GATES = {"accuracy", "swap_consistency", "coverage", "categories"}


def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def fit_bradley_terry(
    candidate_ids: Sequence[str], decisive_wins: Sequence[Tuple[str, str]],
    ridge: float = 1e-3, max_iterations: int = 200, tolerance: float = 1e-10,
) -> Dict[str, float]:
    """Fit centered Bradley-Terry log abilities using a ridge-stabilized Newton solver."""
    candidates = sorted(set(candidate_ids))
    if len(candidates) != len(candidate_ids):
        raise ValueError("Bradley-Terry candidate IDs must be unique")
    if not candidates:
        raise ValueError("Bradley-Terry requires candidates")
    index = {candidate: position for position, candidate in enumerate(candidates)}
    for winner, loser in decisive_wins:
        if winner == loser or winner not in index or loser not in index:
            raise ValueError("Bradley-Terry win references invalid candidates")
    ability = np.zeros(len(candidates), dtype=float)
    for _ in range(max_iterations):
        gradient = -ridge * ability
        information = np.eye(len(candidates), dtype=float) * ridge
        for winner, loser in decisive_wins:
            wi, li = index[winner], index[loser]
            difference = float(np.clip(ability[wi] - ability[li], -40.0, 40.0))
            probability = 1.0 / (1.0 + math.exp(-difference))
            residual = 1.0 - probability
            weight = probability * (1.0 - probability)
            gradient[wi] += residual
            gradient[li] -= residual
            information[wi, wi] += weight
            information[li, li] += weight
            information[wi, li] -= weight
            information[li, wi] -= weight
        step = np.linalg.solve(information, gradient)
        ability += step
        ability -= float(np.mean(ability))
        if float(np.max(np.abs(step))) < tolerance:
            break
    return {candidate: float(ability[index[candidate]]) for candidate in candidates}


def _canonical_value(pair: E2PairV1, result: E2JudgeResultV1, dimension: Optional[str]) -> Tuple[str, float]:
    if result.status != "succeeded" or not result.parsed:
        return "uncertain", 0.0
    if dimension is None:
        preference = result.parsed.get("overall_preference", "uncertain")
        confidence = float(result.parsed.get("overall_confidence", result.parsed.get("confidence", 0.0)))
    else:
        payload = result.parsed.get(dimension) or {}
        preference = payload.get("preference", "uncertain")
        confidence = float(payload.get("confidence", 0.0))
    if preference not in {"a", "b"}:
        return preference if preference in {"tie", "uncertain"} else "uncertain", confidence
    selected_id = result.candidate_a_id if preference == "a" else result.candidate_b_id
    if selected_id == pair.candidate_a.candidate_id:
        return "a", confidence
    if selected_id == pair.candidate_b.candidate_id:
        return "b", confidence
    return "uncertain", 0.0


def swap_predictions(
    pairs: Sequence[E2PairV1], results: Sequence[E2JudgeResultV1],
    threshold: float, dimension: Optional[str] = None,
) -> Tuple[Dict[str, dict], dict]:
    """Canonicalize two directions and expose only consistent high-confidence decisions."""
    grouped: Dict[str, List[E2JudgeResultV1]] = defaultdict(list)
    for result in results:
        grouped[result.pair_id].append(result)
    predictions: Dict[str, dict] = {}
    audit = {"pairs": len(pairs), "consistent": 0, "inconsistent": 0, "decisive_high_confidence": 0,
             "tie": 0, "uncertain_or_low_confidence": 0}
    for pair in pairs:
        records = grouped.get(pair.pair_id, [])
        by_direction = {record.comparison_direction: record for record in records}
        if len(records) != 2 or set(by_direction) != {"a_vs_b", "b_vs_a"}:
            raise ValueError(f"pair {pair.pair_id} requires exactly two E2 swap directions")
        values = [_canonical_value(pair, by_direction[direction], dimension) for direction in ("a_vs_b", "b_vs_a")]
        consistent = values[0][0] == values[1][0]
        if not consistent:
            audit["inconsistent"] += 1
            predictions[pair.pair_id] = {"preference": "uncertain", "confidence": 0.0, "consistent": False}
            continue
        audit["consistent"] += 1
        preference = values[0][0]
        confidence = min(values[0][1], values[1][1])
        if preference in {"a", "b"} and confidence >= threshold:
            audit["decisive_high_confidence"] += 1
            predictions[pair.pair_id] = {"preference": preference, "confidence": confidence, "consistent": True}
        elif preference == "tie" and confidence >= threshold:
            audit["tie"] += 1
            predictions[pair.pair_id] = {"preference": "tie", "confidence": confidence, "consistent": True}
        else:
            audit["uncertain_or_low_confidence"] += 1
            predictions[pair.pair_id] = {"preference": "uncertain", "confidence": confidence, "consistent": True}
    return predictions, audit


def _validate_results(
    pairs: Sequence[E2PairV1], results: Sequence[E2JudgeResultV1], method: str,
    stage: str, artifact_sha256: str, protocol_fingerprint: Optional[str] = None,
) -> dict:
    if (
        len(results) != 560
        or len({item.request_id for item in results}) != 560
        or len({item.judge_key for item in results}) != 560
    ):
        raise ValueError(f"E2 {stage} selection requires 560 unique results")
    pair_map = {pair.pair_id: pair for pair in pairs}
    fingerprints = {item.e1_protocol_fingerprint for item in results}
    if len(fingerprints) != 1:
        raise ValueError("E2 results mix E1 protocol fingerprints")
    fingerprint = next(iter(fingerprints))
    if protocol_fingerprint is not None and fingerprint != protocol_fingerprint:
        raise ValueError("primary and rubric results use different E1 protocol fingerprints")
    execution_identities = {
        (
            item.backend, item.model_name, item.model_revision, item.model_manifest_sha256,
            item.runtime_fingerprint, item.prompt_version, item.prompt_checksum, item.parser_version,
        )
        for item in results
    }
    if len(execution_identities) != 1:
        raise ValueError(f"E2 {stage} results mix backend/model/runtime/prompt identities")
    execution_identity = next(iter(execution_identities))
    grouped: Dict[str, List[E2JudgeResultV1]] = defaultdict(list)
    for result in results:
        if result.method != method or result.stage != stage or result.split != "e2-pilot":
            raise ValueError(f"E2 {stage} result method/stage/split mismatch")
        if result.status != "succeeded":
            raise ValueError(f"E2 {stage} contains failed Judge results")
        if result.reward_artifact_sha256 != artifact_sha256:
            raise ValueError(f"E2 {stage} reward artifact identity mismatch")
        pair = pair_map.get(result.pair_id)
        if pair is None or result.sample_id != pair.sample_id:
            raise ValueError(f"E2 {stage} result references unknown pair/sample")
        expected = {pair.candidate_a.candidate_id, pair.candidate_b.candidate_id}
        if {result.candidate_a_id, result.candidate_b_id} != expected:
            raise ValueError(f"E2 {stage} result candidate identity mismatch")
        grouped[result.pair_id].append(result)
    if set(grouped) != set(pair_map):
        raise ValueError(f"E2 {stage} results do not cover all 280 pairs")
    for pair_id, records in grouped.items():
        if len(records) != 2 or {item.comparison_direction for item in records} != {"a_vs_b", "b_vs_a"}:
            raise ValueError(f"E2 {stage} pair {pair_id} does not have both directions")
    return {
        "protocol_fingerprint": fingerprint,
        "backend": execution_identity[0], "model_name": execution_identity[1],
        "model_revision": execution_identity[2], "model_manifest_sha256": execution_identity[3],
        "runtime_fingerprint": execution_identity[4], "prompt_version": execution_identity[5],
        "prompt_checksum": execution_identity[6], "parser_version": execution_identity[7],
    }


def _abilities_by_sample(
    pairs: Sequence[E2PairV1], predictions: Dict[str, dict], dimension_probability: bool = False,
) -> Dict[str, Dict[str, float]]:
    by_sample: Dict[str, List[E2PairV1]] = defaultdict(list)
    for pair in pairs:
        by_sample[pair.sample_id].append(pair)
    output: Dict[str, Dict[str, float]] = {}
    for sample_id, sample_pairs in by_sample.items():
        candidates = sorted({
            candidate
            for pair in sample_pairs
            for candidate in (pair.candidate_a.candidate_id, pair.candidate_b.candidate_id)
        })
        wins: List[Tuple[str, str]] = []
        for pair in sample_pairs:
            preference = predictions[pair.pair_id]["preference"]
            if preference == "a":
                wins.append((pair.candidate_a.candidate_id, pair.candidate_b.candidate_id))
            elif preference == "b":
                wins.append((pair.candidate_b.candidate_id, pair.candidate_a.candidate_id))
        abilities = fit_bradley_terry(candidates, wins)
        if dimension_probability:
            abilities = {candidate: 1.0 / (1.0 + math.exp(-score)) for candidate, score in abilities.items()}
        output[sample_id] = abilities
    return output


def pareto_maxmin_choice(candidate_ids: Sequence[str], utilities: Dict[str, Dict[str, float]]) -> str:
    """Choose Pareto layer, then max-min, geometric mean, and ascending candidate ID."""
    candidates = sorted(candidate_ids)
    if not candidates:
        raise ValueError("Pareto selection requires candidates")
    for candidate in candidates:
        if set(utilities.get(candidate, {})) != set(DIMENSIONS):
            raise ValueError(f"candidate {candidate} lacks four-dimensional utilities")
    frontier = []
    for candidate in candidates:
        vector = utilities[candidate]
        dominated = False
        for other in candidates:
            if other == candidate:
                continue
            other_vector = utilities[other]
            if all(other_vector[d] >= vector[d] for d in DIMENSIONS) and any(
                other_vector[d] > vector[d] for d in DIMENSIONS
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return sorted(
        frontier,
        key=lambda candidate: (
            -min(utilities[candidate].values()),
            -math.prod(max(0.0, utilities[candidate][dimension]) for dimension in DIMENSIONS) ** 0.25,
            candidate,
        ),
    )[0]


def _random_choice(subset: Sequence[str], seed: int, trial_id: str, n: int) -> str:
    digest = canonical_sha256({"seed": seed, "trial_id": trial_id, "n": n, "method": "random"})
    return list(subset)[int(digest, 16) % len(subset)]


def select_candidates(
    config_path: Path, design_path: Path, pairs_path: Path, primary_results_path: Path,
    reward_path: Path, output: Path, measurement_mode: str = "mock",
    rubric_results_path: Optional[Path] = None, auxiliary_rubric_path: Optional[Path] = None,
) -> dict:
    cfg = load_config(config_path)
    if measurement_mode not in {"mock", "replay", "formal-command"}:
        raise ValueError("measurement mode must be mock, replay, or formal-command")
    design_payload = read_json(design_path)
    trials = [BonTrialV1.model_validate(item) for item in design_payload.get("trials", [])]
    pairs = [E2PairV1.model_validate(item) for item in _read_jsonl(pairs_path)]
    primary_results = [E2JudgeResultV1.model_validate(item) for item in _read_jsonl(primary_results_path)]
    reward = yaml.safe_load(Path(reward_path).read_text(encoding="utf-8"))
    if len(trials) != 80 or len({item.trial_id for item in trials}) != 80:
        raise ValueError("E2 selection requires 80 unique balanced trials")
    if len(pairs) != 280 or len({item.pair_id for item in pairs}) != 280:
        raise ValueError("E2 selection requires 280 unique pairs")
    primary_method = reward.get("method")
    if reward.get("provisional") is not True or primary_method not in {"pairwise-swap-v1", "rubric-swap-v1"}:
        raise ValueError("E2 selection requires a provisional frozen swap reward-v0")
    threshold = float(reward["confidence_threshold"])
    primary_identity = _validate_results(
        pairs, primary_results, primary_method, "primary", sha256_file(reward_path),
    )
    primary_fingerprint = primary_identity["protocol_fingerprint"]
    expected_backend = {"mock": "mock", "replay": "replay", "formal-command": "command"}[measurement_mode]
    if primary_identity["backend"] != expected_backend:
        raise ValueError("E2 measurement mode does not match primary result backend provenance")
    reward_identity = {
        "model_revision": reward.get("model_revision"),
        "prompt_version": reward.get("prompt_version"),
        "prompt_checksum": reward.get("prompt_checksum"),
        "parser_version": reward.get("parser_version"),
    }
    if any(reward_identity[key] != primary_identity[key] for key in reward_identity):
        raise ValueError("E2 primary results do not match reward-v0 model/prompt identity")
    primary_predictions, primary_audit = swap_predictions(pairs, primary_results, threshold)
    primary_abilities = _abilities_by_sample(pairs, primary_predictions)

    rubric_results: Optional[List[E2JudgeResultV1]] = None
    rubric_threshold: Optional[float] = None
    rubric_source = "NOT_APPLICABLE"
    if primary_method == "rubric-swap-v1":
        if rubric_results_path is not None or auxiliary_rubric_path is not None:
            raise ValueError("rubric primary must use its primary results without an auxiliary artifact")
        rubric_results = primary_results
        rubric_threshold = threshold
        rubric_source = "primary"
    elif (rubric_results_path is None) != (auxiliary_rubric_path is None):
        raise ValueError("auxiliary rubric results and qualification artifact must be supplied together")
    elif rubric_results_path is not None and auxiliary_rubric_path is not None:
        auxiliary = read_json(auxiliary_rubric_path)
        gates = auxiliary.get("gates")
        if (
            auxiliary.get("decision") != "PASS_AUXILIARY_RUBRIC"
            or auxiliary.get("method") != "rubric-swap-v1"
            or auxiliary.get("e1_protocol_fingerprint") != primary_fingerprint
            or not isinstance(gates, dict)
            or set(gates) != RELIABILITY_GATES
            or any(gates[name] is not True for name in RELIABILITY_GATES)
        ):
            raise ValueError("auxiliary rubric is not qualified for this E1 protocol")
        rubric_results = [E2JudgeResultV1.model_validate(item) for item in _read_jsonl(rubric_results_path)]
        rubric_identity = _validate_results(
            pairs, rubric_results, "rubric-swap-v1", "auxiliary-rubric",
            sha256_file(auxiliary_rubric_path), primary_fingerprint,
        )
        if rubric_identity["backend"] != expected_backend:
            raise ValueError("E2 measurement mode does not match rubric result backend provenance")
        for key in ("model_name", "model_revision", "model_manifest_sha256", "runtime_fingerprint"):
            if rubric_identity[key] != primary_identity[key]:
                raise ValueError("E2 primary and rubric results use different model/runtime identities")
        rubric_threshold = float(auxiliary["confidence_threshold"])
        rubric_source = "qualified-auxiliary"

    dimension_abilities: Dict[str, Dict[str, Dict[str, float]]] = {}
    dimension_audit = {}
    if rubric_results is not None and rubric_threshold is not None:
        for dimension in DIMENSIONS:
            predictions, audit = swap_predictions(pairs, rubric_results, rubric_threshold, dimension)
            dimension_abilities[dimension] = _abilities_by_sample(pairs, predictions, dimension_probability=True)
            dimension_audit[dimension] = audit

    candidate_sha: Dict[str, str] = {}
    pair_input: Dict[str, E2PairV1] = {}
    for pair in pairs:
        pair_input.setdefault(pair.sample_id, pair)
        candidate_sha[pair.candidate_a.candidate_id] = pair.candidate_a.video_sha256
        candidate_sha[pair.candidate_b.candidate_id] = pair.candidate_b.video_sha256
    method_status = {
        "random": "AVAILABLE", "primary-bradley-terry": "AVAILABLE",
        "equal-linear": "AVAILABLE" if dimension_abilities else "NOT_APPLICABLE",
        "pareto-maxmin": "AVAILABLE" if dimension_abilities else "NOT_APPLICABLE",
    }
    selections: List[E2SelectionV1] = []
    primary_lookup: Dict[Tuple[str, int], E2SelectionV1] = {}
    for trial in sorted(trials, key=lambda item: item.trial_id):
        if trial.sample_id not in primary_abilities:
            raise ValueError(f"trial {trial.trial_id} references unknown sample")
        if len(set(trial.candidate_order)) != 8:
            raise ValueError(f"trial {trial.trial_id} candidate order is not unique")
        for n in cfg.n_values:
            subset = trial.subsets.get(str(n))
            if subset != trial.candidate_order[:n] or len(set(subset)) != n:
                raise ValueError(f"trial {trial.trial_id} N={n} subset violates balanced prefix design")
            random_candidate = _random_choice(subset, cfg.randomization_seed, trial.trial_id, n)
            selections.append(E2SelectionV1(
                trial_id=trial.trial_id, sample_id=trial.sample_id, replicate=trial.replicate,
                n=n, method="random", candidate_id=random_candidate,
                candidate_video_sha256=candidate_sha[random_candidate],
            ))
            primary_candidate = sorted(
                subset, key=lambda candidate: (-primary_abilities[trial.sample_id][candidate], candidate),
            )[0]
            primary_record = E2SelectionV1(
                trial_id=trial.trial_id, sample_id=trial.sample_id, replicate=trial.replicate,
                n=n, method="primary-bradley-terry", candidate_id=primary_candidate,
                candidate_video_sha256=candidate_sha[primary_candidate],
                utility=primary_abilities[trial.sample_id][primary_candidate],
            )
            selections.append(primary_record)
            primary_lookup[(trial.trial_id, n)] = primary_record
            if dimension_abilities:
                vectors = {
                    candidate: {
                        dimension: dimension_abilities[dimension][trial.sample_id][candidate]
                        for dimension in DIMENSIONS
                    }
                    for candidate in subset
                }
                linear_candidate = sorted(
                    subset,
                    key=lambda candidate: (-sum(vectors[candidate].values()) / len(DIMENSIONS), candidate),
                )[0]
                selections.append(E2SelectionV1(
                    trial_id=trial.trial_id, sample_id=trial.sample_id, replicate=trial.replicate,
                    n=n, method="equal-linear", candidate_id=linear_candidate,
                    candidate_video_sha256=candidate_sha[linear_candidate],
                    utility=sum(vectors[linear_candidate].values()) / len(DIMENSIONS),
                    dimension_utilities=vectors[linear_candidate],
                ))
                pareto_candidate = pareto_maxmin_choice(subset, vectors)
                selections.append(E2SelectionV1(
                    trial_id=trial.trial_id, sample_id=trial.sample_id, replicate=trial.replicate,
                    n=n, method="pareto-maxmin", candidate_id=pareto_candidate,
                    candidate_video_sha256=candidate_sha[pareto_candidate],
                    utility=min(vectors[pareto_candidate].values()),
                    dimension_utilities=vectors[pareto_candidate],
                ))

    human_comparisons: List[E2HumanComparisonV1] = []
    for trial in sorted(trials, key=lambda item: item.trial_id):
        n4 = primary_lookup[(trial.trial_id, 4)]
        n1 = primary_lookup[(trial.trial_id, 1)]
        pair = pair_input[trial.sample_id]
        randomization_seed = int(canonical_sha256({
            "seed": cfg.randomization_seed, "trial_id": trial.trial_id, "purpose": "human-n4-vs-n1",
        })[:16], 16)
        human_comparisons.append(E2HumanComparisonV1(
            comparison_id=f"e2-human:{trial.trial_id}", trial_id=trial.trial_id,
            sample_id=trial.sample_id, replicate=trial.replicate,
            instruction=pair.instruction, target_caption=pair.target_caption,
            n4_candidate_id=n4.candidate_id, n4_video_sha256=n4.candidate_video_sha256,
            n1_candidate_id=n1.candidate_id, n1_video_sha256=n1.candidate_video_sha256,
            identical_selection=n4.candidate_video_sha256 == n1.candidate_video_sha256,
            randomization_seed=randomization_seed,
        ))

    dependencies = {
        "config_sha256": sha256_file(config_path), "design_sha256": sha256_file(design_path),
        "pairs_sha256": sha256_file(pairs_path), "primary_results_sha256": sha256_file(primary_results_path),
        "reward_v0_sha256": sha256_file(reward_path), "e1_protocol_fingerprint": primary_fingerprint,
        "rubric_results_sha256": sha256_file(rubric_results_path) if rubric_results_path else None,
        "auxiliary_rubric_sha256": sha256_file(auxiliary_rubric_path) if auxiliary_rubric_path else None,
        "rubric_source": rubric_source,
    }
    research_measurements = (len(primary_results) + (len(rubric_results) if rubric_source == "qualified-auxiliary" else 0)) if measurement_mode == "formal-command" else 0
    bundle = E2SelectionBundleV1(
        experiment_id=cfg.experiment_id, measurement_mode=measurement_mode,
        method_status=method_status, selections=selections, human_comparisons=human_comparisons,
        primary_method=primary_method, confidence_threshold=threshold, dependencies=dependencies,
        comparison_audit={"primary": primary_audit, "dimensions": dimension_audit},
        research_measurements=research_measurements,
    ).model_dump(mode="json")
    atomic_write_new_json(output, bundle)
    return bundle
