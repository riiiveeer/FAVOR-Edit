"""Four-method, split-aware E1 reliability analysis and frozen decision gate."""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

from w1_pipeline.hashing import sha256_file

from .models import (
    AdjudicatedLabelV2, FrozenProtocolV2, JudgeResultV2, PairRecordV2,
)
from .ranking import fit_utilities, kendall_tau, spearman

METHODS = ("absolute-v1", "pairwise-single-v1", "pairwise-swap-v1", "rubric-swap-v1")
DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")


def _load_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _canonical_preference(pair: PairRecordV2, result: JudgeResultV2, preference: str) -> str:
    if preference not in {"a", "b"}:
        return preference if preference in {"tie", "uncertain"} else "uncertain"
    chosen = result.candidate_a_id if preference == "a" else result.candidate_b_id
    if chosen == pair.candidate_a.candidate_id:
        return "a"
    if chosen == pair.candidate_b.candidate_id:
        return "b"
    return "uncertain"


def _pairwise_value(pair: PairRecordV2, result: JudgeResultV2, dimension: Optional[str] = None) -> Tuple[str, float]:
    if result.status != "succeeded" or not result.parsed:
        return "uncertain", 0.0
    if dimension:
        payload = result.parsed.get(dimension) or {}
        preference = payload.get("preference", "uncertain")
        confidence = float(payload.get("confidence", 0))
    else:
        preference = result.parsed.get("overall_preference", "uncertain")
        confidence = float(result.parsed.get("overall_confidence", result.parsed.get("confidence", 0)))
    return _canonical_preference(pair, result, preference), confidence


def _merge_swap(pair: PairRecordV2, records: Sequence[JudgeResultV2]) -> dict:
    by_direction = {record.comparison_direction: record for record in records if record.status == "succeeded"}
    required = {"a_vs_b", "b_vs_a"}
    if set(by_direction) != required:
        return {"preference": "uncertain", "confidence": 0.0, "consistent": False, "dimensions": {}}
    overall = [_pairwise_value(pair, by_direction[direction]) for direction in ("a_vs_b", "b_vs_a")]
    consistent = overall[0][0] == overall[1][0]
    prediction = {
        "preference": overall[0][0] if consistent else "uncertain",
        "confidence": min(overall[0][1], overall[1][1]) if consistent else 0.0,
        "consistent": consistent,
        "dimensions": {},
    }
    if records[0].method == "rubric-swap-v1":
        for dimension in DIMENSIONS:
            values = [_pairwise_value(pair, by_direction[direction], dimension) for direction in ("a_vs_b", "b_vs_a")]
            dimension_consistent = values[0][0] == values[1][0]
            prediction["dimensions"][dimension] = {
                "preference": values[0][0] if dimension_consistent else "uncertain",
                "confidence": min(values[0][1], values[1][1]) if dimension_consistent else 0.0,
                "consistent": dimension_consistent,
            }
    return prediction


def build_predictions(
    pairs: Sequence[PairRecordV2],
    results: Sequence[JudgeResultV2],
    method: str,
    absolute_delta: float = 0.0,
) -> Dict[str, dict]:
    predictions: Dict[str, dict] = {}
    if method == "absolute-v1":
        by_candidate = {
            result.candidate_id: result for result in results
            if result.method == method and result.status == "succeeded" and result.candidate_id
        }
        for pair in pairs:
            a = by_candidate.get(pair.candidate_a.candidate_id)
            b = by_candidate.get(pair.candidate_b.candidate_id)
            if not a or not b or not a.parsed or not b.parsed:
                predictions[pair.pair_id] = {"preference": "uncertain", "confidence": 0.0, "dimensions": {}}
                continue
            diff = float(a.parsed["overall_score"]) - float(b.parsed["overall_score"])
            preference = "tie" if abs(diff) <= absolute_delta else ("a" if diff > 0 else "b")
            confidence = min(float(a.parsed["confidence"]), float(b.parsed["confidence"]))
            dimensions = {}
            for dimension in DIMENSIONS:
                dimension_diff = float(a.parsed["scores"][dimension]) - float(b.parsed["scores"][dimension])
                dimension_preference = "tie" if abs(dimension_diff) <= absolute_delta else ("a" if dimension_diff > 0 else "b")
                dimensions[dimension] = {"preference": dimension_preference, "confidence": confidence}
            predictions[pair.pair_id] = {
                "preference": preference, "confidence": confidence,
                "consistent": None, "dimensions": dimensions,
            }
        return predictions

    grouped: Dict[str, List[JudgeResultV2]] = defaultdict(list)
    for result in results:
        if result.method == method and result.pair_id:
            grouped[result.pair_id].append(result)
    pair_map = {pair.pair_id: pair for pair in pairs}
    for pair_id, pair in pair_map.items():
        records = grouped.get(pair_id, [])
        if method in {"pairwise-swap-v1", "rubric-swap-v1"}:
            predictions[pair_id] = _merge_swap(pair, records)
        elif len(records) == 1:
            preference, confidence = _pairwise_value(pair, records[0])
            predictions[pair_id] = {
                "preference": preference, "confidence": confidence,
                "consistent": None, "dimensions": {},
            }
        else:
            predictions[pair_id] = {"preference": "uncertain", "confidence": 0.0, "consistent": None, "dimensions": {}}
    return predictions


def _human_preference(label: AdjudicatedLabelV2, dimension: Optional[str]) -> str:
    return getattr(label, f"{dimension}_preference") if dimension else label.overall_preference


def _prediction_value(prediction: dict, dimension: Optional[str]) -> Tuple[str, float]:
    if dimension:
        value = prediction.get("dimensions", {}).get(dimension, {})
        return value.get("preference", "uncertain"), float(value.get("confidence", 0))
    return prediction.get("preference", "uncertain"), float(prediction.get("confidence", 0))


def _core_metrics(
    pairs: Sequence[PairRecordV2],
    labels: Dict[str, AdjudicatedLabelV2],
    predictions: Dict[str, dict],
    confidence_threshold: float,
    dimension: Optional[str] = None,
) -> dict:
    eligible = covered = correct = 0
    for pair in pairs:
        if pair.excluded_reason:
            continue
        label = labels.get(pair.pair_id)
        if label is None:
            continue
        human = _human_preference(label, dimension)
        if human not in {"a", "b"}:
            continue
        eligible += 1
        preference, confidence = _prediction_value(predictions.get(pair.pair_id, {}), dimension)
        if preference in {"a", "b"} and confidence >= confidence_threshold:
            covered += 1
            correct += preference == human
    return {
        "eligible_pairs": eligible,
        "covered_pairs": covered,
        "correct_pairs": correct,
        "decisive_accuracy": correct / covered if covered else 0.0,
        "effective_accuracy": correct / eligible if eligible else 0.0,
        "coverage": covered / eligible if eligible else 0.0,
    }


def _bootstrap_ci(
    pairs: Sequence[PairRecordV2], labels: Dict[str, AdjudicatedLabelV2], predictions: Dict[str, dict],
    threshold: float, seed: int, iterations: int,
) -> dict:
    by_sample: Dict[str, List[PairRecordV2]] = defaultdict(list)
    for pair in pairs:
        by_sample[pair.sample_id].append(pair)
    samples = sorted(by_sample)
    if not samples or iterations <= 0:
        return {"effective_accuracy": [0.0, 0.0], "decisive_accuracy": [0.0, 0.0]}
    rng = random.Random(seed)
    effective, decisive = [], []
    for _ in range(iterations):
        resampled = []
        for _ in samples:
            resampled.extend(by_sample[rng.choice(samples)])
        metric = _core_metrics(resampled, labels, predictions, threshold)
        effective.append(metric["effective_accuracy"])
        decisive.append(metric["decisive_accuracy"])
    effective.sort()
    decisive.sort()
    lower = max(0, int(0.025 * iterations))
    upper = min(iterations - 1, int(0.975 * iterations))
    return {
        "effective_accuracy": [effective[lower], effective[upper]],
        "decisive_accuracy": [decisive[lower], decisive[upper]],
    }


def _position_bias(results: Sequence[JudgeResultV2], method: str) -> dict:
    choices = []
    for result in results:
        if result.method != method or result.status != "succeeded" or not result.parsed:
            continue
        preference = result.parsed.get("overall_preference")
        if preference in {"a", "b"}:
            choices.append(preference)
    return {
        "decisive_requests": len(choices),
        "left_rate": choices.count("a") / len(choices) if choices else 0.0,
        "right_rate": choices.count("b") / len(choices) if choices else 0.0,
    }


def _ranking(
    pairs: Sequence[PairRecordV2], labels: Dict[str, AdjudicatedLabelV2],
    predictions: Dict[str, dict], threshold: float,
) -> dict:
    taus, rhos = [], []
    for sample_id in sorted({pair.sample_id for pair in pairs}):
        human_entries, judge_entries = [], []
        for pair in pairs:
            if pair.sample_id != sample_id or pair.excluded_reason:
                continue
            label = labels.get(pair.pair_id)
            if not label or label.overall_preference not in {"a", "b"}:
                continue
            entry = {"a": pair.candidate_a.candidate_id, "b": pair.candidate_b.candidate_id}
            human_entries.append({**entry, "choice": label.overall_preference})
            preference, confidence = _prediction_value(predictions.get(pair.pair_id, {}), None)
            if preference in {"a", "b"} and confidence >= threshold:
                judge_entries.append({**entry, "choice": preference})
        human_utilities = fit_utilities(human_entries)
        judge_utilities = fit_utilities(judge_entries)
        if len(set(human_utilities) & set(judge_utilities)) >= 2:
            taus.append(kendall_tau(human_utilities, judge_utilities))
            rhos.append(spearman(human_utilities, judge_utilities))
    return {
        "samples": len(taus),
        "kendall_tau": mean(taus) if taus else 0.0,
        "spearman": mean(rhos) if rhos else 0.0,
    }


def evaluate_method(
    pairs: Sequence[PairRecordV2], labels: Dict[str, AdjudicatedLabelV2],
    results: Sequence[JudgeResultV2], method: str, confidence_threshold: float,
    absolute_delta: float, bootstrap_seed: int, bootstrap_iterations: int,
) -> dict:
    predictions = build_predictions(pairs, results, method, absolute_delta)
    overall = _core_metrics(pairs, labels, predictions, confidence_threshold)
    categories = {
        task_type: _core_metrics(
            [pair for pair in pairs if pair.task_type == task_type], labels, predictions, confidence_threshold
        )
        for task_type in ("attribute", "object", "local")
    }
    dimensions = {
        dimension: _core_metrics(pairs, labels, predictions, confidence_threshold, dimension)
        for dimension in DIMENSIONS
    }
    consistent_values = [
        prediction.get("consistent") for prediction in predictions.values()
        if prediction.get("consistent") is not None
    ]
    swap = sum(value is True for value in consistent_values) / len(consistent_values) if consistent_values else None
    return {
        **overall,
        "confidence_threshold": confidence_threshold,
        "absolute_delta_threshold": absolute_delta if method == "absolute-v1" else None,
        "swap_consistency": swap,
        "position_bias": _position_bias(results, method),
        "categories": categories,
        "dimensions": dimensions,
        "ranking": _ranking(pairs, labels, predictions, confidence_threshold),
        "bootstrap_95_ci": _bootstrap_ci(
            pairs, labels, predictions, confidence_threshold, bootstrap_seed, bootstrap_iterations
        ),
    }


def _best_setting(candidates: List[dict], minimum_coverage: float) -> dict:
    feasible = [candidate for candidate in candidates if candidate["metrics"]["coverage"] >= minimum_coverage]
    pool = feasible or candidates
    return max(
        pool,
        key=lambda candidate: (
            candidate["metrics"]["effective_accuracy"], candidate["metrics"]["coverage"],
            -candidate["confidence_threshold"], -(candidate.get("absolute_delta_threshold") or 0),
        ),
    )


def _write_tables(output_dir: Path, method_metrics: Dict[str, dict], split: str) -> None:
    with (output_dir / "judge-reliability.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "split", "method", "decisive_accuracy", "effective_accuracy", "coverage",
            "swap_consistency", "confidence_threshold", "absolute_delta_threshold",
        ])
        writer.writeheader()
        for method, metrics in method_metrics.items():
            writer.writerow({"split": split, "method": method, **{key: metrics.get(key) for key in writer.fieldnames[2:]}})
    with (output_dir / "position-bias.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "method", "decisive_requests", "left_rate", "right_rate"])
        writer.writeheader()
        for method, metrics in method_metrics.items():
            writer.writerow({"split": split, "method": method, **metrics["position_bias"]})
    with (output_dir / "category-metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "method", "task_type", "eligible_pairs", "coverage", "decisive_accuracy", "effective_accuracy"])
        writer.writeheader()
        for method, metrics in method_metrics.items():
            for task_type, values in metrics["categories"].items():
                writer.writerow({"split": split, "method": method, "task_type": task_type, **{key: values[key] for key in writer.fieldnames[3:]}})
    with (output_dir / "ranking-correlations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "method", "samples", "kendall_tau", "spearman"])
        writer.writeheader()
        for method, metrics in method_metrics.items():
            writer.writerow({"split": split, "method": method, **metrics["ranking"]})


def _case_candidates(results: Sequence[JudgeResultV2], method: str) -> dict:
    cases = {"under_edit": [], "over_edit": []}
    seen = set()
    for result in results:
        if result.method != method or result.status != "succeeded" or not result.parsed:
            continue
        if result.comparison_direction not in {"a_vs_b", "absolute"}:
            continue
        for side, candidate_id in (("a", result.candidate_a_id), ("b", result.candidate_b_id)):
            if not candidate_id:
                continue
            for tag in result.parsed.get(f"failure_tags_{side}", []):
                if tag in cases and (result.pair_id, candidate_id, tag) not in seen:
                    cases[tag].append({"pair_id": result.pair_id, "candidate_id": candidate_id})
                    seen.add((result.pair_id, candidate_id, tag))
    return {key: values[:10] for key, values in cases.items()}


def analyze(
    pairs: Path,
    human: Path,
    results: Path,
    config: Path,
    output_dir: Path,
    mode: str = "dev",
    frozen_protocol: Optional[Path] = None,
) -> Dict[str, dict]:
    if mode not in {"dev", "final"}:
        raise ValueError("analysis mode must be dev or final")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"analysis output already exists: {output_dir}")
    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    pair_records = [PairRecordV2.model_validate(record) for record in _load_jsonl(pairs)]
    label_records = [AdjudicatedLabelV2.model_validate(record) for record in _load_jsonl(human)]
    labels = {record.pair_id: record for record in label_records}
    if len(labels) != 100:
        raise ValueError("analysis requires 100 unique adjudicated human labels")
    result_records = [JudgeResultV2.model_validate(record) for record in _load_jsonl(results)]
    split = "dev" if mode == "dev" else "frozen-eval"
    selected_pairs = [pair for pair in pair_records if pair.split == split]
    selected_results = [result for result in result_records if result.split == split]
    seed = int(cfg.get("bootstrap_seed", 20260820))
    iterations = int(cfg.get("bootstrap_iterations", 2000))
    confidence_grid = [float(value) for value in cfg["threshold_grids"]["confidence"]]
    delta_grid = [float(value) for value in cfg["threshold_grids"]["absolute_delta"]]
    minimum_coverage = float(cfg["thresholds"]["high_confidence_coverage"])

    method_metrics: Dict[str, dict] = {}
    selection_payload = None
    if mode == "dev":
        method_counts = {
            method: sum(result.method == method for result in selected_results) for method in METHODS
        }
        expected_counts = {
            "absolute-v1": 15, "pairwise-single-v1": 30,
            "pairwise-swap-v1": 60, "rubric-swap-v1": 60,
        }
        if method_counts != expected_counts:
            raise ValueError(f"dev analysis requires exact method counts {expected_counts}, got {method_counts}")
        best_settings = {}
        for method in METHODS:
            settings = []
            method_deltas = delta_grid if method == "absolute-v1" else [0.0]
            for delta in method_deltas:
                for threshold in confidence_grid:
                    metrics = evaluate_method(
                        selected_pairs, labels, selected_results, method, threshold, delta, seed, iterations
                    )
                    settings.append({
                        "confidence_threshold": threshold,
                        "absolute_delta_threshold": delta if method == "absolute-v1" else None,
                        "metrics": metrics,
                    })
            best = _best_setting(settings, minimum_coverage)
            best_settings[method] = best
            method_metrics[method] = best["metrics"]

        candidates = []
        for method in cfg["method_selection"]["candidates"]:
            metrics = method_metrics[method]
            if metrics["coverage"] >= minimum_coverage and (metrics["swap_consistency"] or 0) >= float(cfg["thresholds"]["swap_consistency"]):
                candidates.append(method)
        selected_method = None
        if candidates:
            selected_method = max(candidates, key=lambda method: method_metrics[method]["effective_accuracy"])
            if "rubric-swap-v1" in candidates and "pairwise-swap-v1" in candidates:
                difference = abs(
                    method_metrics["rubric-swap-v1"]["effective_accuracy"]
                    - method_metrics["pairwise-swap-v1"]["effective_accuracy"]
                )
                if difference <= float(cfg["method_selection"]["rubric_tie_tolerance"]):
                    selected_method = "rubric-swap-v1"
        selection_payload = {
            "schema_version": "2",
            "selected_method": selected_method,
            "confidence_threshold": (
                best_settings[selected_method]["confidence_threshold"] if selected_method else None
            ),
            "absolute_delta_threshold": best_settings["absolute-v1"]["absolute_delta_threshold"],
            "method_settings": {
                method: {
                    "confidence_threshold": setting["confidence_threshold"],
                    "absolute_delta_threshold": setting["absolute_delta_threshold"],
                    "effective_accuracy": setting["metrics"]["effective_accuracy"],
                    "coverage": setting["metrics"]["coverage"],
                    "swap_consistency": setting["metrics"]["swap_consistency"],
                }
                for method, setting in best_settings.items()
            },
            "blocked": selected_method is None,
        }
    else:
        if frozen_protocol is None:
            raise ValueError("final analysis requires --frozen-protocol")
        protocol = FrozenProtocolV2.model_validate(json.loads(Path(frozen_protocol).read_text(encoding="utf-8")))
        if sha256_file(config) != protocol.config_checksum:
            raise ValueError("final analysis config does not match frozen protocol lock")
        gate_results = [result for result in selected_results if result.method == protocol.selected_method]
        if len(gate_results) != 140:
            raise ValueError(
                f"frozen gate requires 140 selected-method directional results, got {len(gate_results)}"
            )
        for result in gate_results:
            expected_prompt = protocol.prompt_checksums[protocol.selected_method]
            if (
                result.frozen_protocol_fingerprint != protocol.protocol_fingerprint
                or result.runtime_fingerprint != protocol.runtime_fingerprint
                or result.prompt_checksum != expected_prompt
            ):
                raise ValueError("frozen result identity does not match protocol lock")
        method_metrics[protocol.selected_method] = evaluate_method(
            selected_pairs, labels, gate_results, protocol.selected_method,
            protocol.confidence_threshold, protocol.absolute_delta_threshold, seed, iterations,
        )
        selected = method_metrics[protocol.selected_method]
        category_values = [value["decisive_accuracy"] for value in selected["categories"].values()]
        gates = {
            "accuracy": selected["decisive_accuracy"] >= float(cfg["thresholds"]["accuracy"]),
            "swap_consistency": (selected["swap_consistency"] or 0) >= float(cfg["thresholds"]["swap_consistency"]),
            "coverage": selected["coverage"] >= minimum_coverage,
            "categories": min(category_values, default=0) >= float(cfg["thresholds"]["min_category_accuracy"]),
        }
        decision = "PASS_PROVISIONAL" if all(gates.values()) else "FAIL_REVISE_JUDGE"
        decision_payload = {
            "schema_version": "2", "decision": decision,
            "selected_method": protocol.selected_method, "split": "frozen-eval",
            "gates": gates, "metrics": selected,
        }

    human_summary = {
        "labels": len(label_records),
        "agreement_rate": sum(label.agreement for label in label_records) / len(label_records),
        "third_party_labels": sum(not label.agreement for label in label_records),
        "tie_rate": sum(label.human_tie for label in label_records) / len(label_records),
        "uncertain_rate": sum(label.human_uncertain for label in label_records) / len(label_records),
    }
    metrics_payload = {
        "schema_version": "2", "mode": mode, "split": split,
        "pairs": len(selected_pairs), "methods": method_metrics, "human": human_summary,
        "case_candidates": _case_candidates(
            selected_results,
            (
                selection_payload["selected_method"]
                if mode == "dev" and selection_payload and selection_payload["selected_method"]
                else ("rubric-swap-v1" if mode == "dev" else protocol.selected_method)
            ),
        ),
    }
    output_dir.mkdir(parents=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_tables(output_dir, method_metrics, split)
    if selection_payload is not None:
        (output_dir / "dev-selection.json").write_text(
            json.dumps(selection_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        (output_dir / "decision.json").write_text(
            json.dumps(decision_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if decision_payload["decision"] == "PASS_PROVISIONAL":
            selected_results_for_method = [result for result in selected_results if result.method == protocol.selected_method]
            first_result = selected_results_for_method[0]
            reward = {
                "schema_version": "2", "provisional": True,
                "method": protocol.selected_method,
                "model_revision": first_result.model_revision,
                "prompt_version": first_result.prompt_version,
                "prompt_checksum": first_result.prompt_checksum,
                "parser_version": first_result.parser_version,
                "confidence_threshold": protocol.confidence_threshold,
                "absolute_delta_threshold": protocol.absolute_delta_threshold,
                "swap_merge_rule": "canonical agreement in both directions; inconsistent becomes uncertain",
                "tie_uncertain_rule": "excluded from decisive accuracy and high-confidence coverage",
                "data_scope": "DAVIS-2017 train, fixed 70 frozen-eval pairs",
                "metrics": decision_payload["metrics"],
            }
            (output_dir / "reward-v0.yaml").write_text(
                yaml.safe_dump(reward, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
    return metrics_payload
