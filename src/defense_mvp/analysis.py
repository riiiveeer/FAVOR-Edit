"""Deterministic D4 agreement, rates, Bradley-Terry, bootstrap, and costs."""

from __future__ import annotations

import csv
import json
import math
import os
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .aggregation import load_aggregate
from .analysis_models import CATEGORIES, FAMILIES, FIELDS, NODES, AnalysisConfig, load_analysis_config
from .annotation_bundle import now, read_json, source_evidence, stage, verify_sums, write_sums
from .io import rename_noreplace, write_json


def _defined(value: float) -> dict:
    if not math.isfinite(value):
        return {"status": "undefined", "value": None, "reason": "non_finite"}
    return {"status": "defined", "value": float(value), "reason": None}


def _undefined(reason: str) -> dict:
    return {"status": "undefined", "value": None, "reason": reason}


def cohen_kappa(values_a: Sequence[str], values_b: Sequence[str]) -> dict:
    if len(values_a) != len(values_b):
        raise ValueError("kappa inputs must have equal length")
    if not values_a:
        return {
            "status": "undefined", "value": None, "reason": "no_samples",
            "observed_agreement": None, "expected_agreement": None,
        }
    if any(value not in CATEGORIES for value in [*values_a, *values_b]):
        raise ValueError("kappa input category invalid")
    count = len(values_a)
    observed = sum(a == b for a, b in zip(values_a, values_b)) / count
    margin_a, margin_b = Counter(values_a), Counter(values_b)
    expected = sum((margin_a[c] / count) * (margin_b[c] / count) for c in CATEGORIES)
    if not math.isfinite(observed) or not math.isfinite(expected):
        return {
            "status": "undefined", "value": None, "reason": "non_finite",
            "observed_agreement": None, "expected_agreement": None,
        }
    if math.isclose(expected, 1.0, rel_tol=0.0, abs_tol=1.0e-15):
        return {
            "status": "undefined", "value": None, "reason": "expected_agreement_is_one",
            "observed_agreement": observed, "expected_agreement": expected,
        }
    return {
        "status": "defined",
        "value": (observed - expected) / (1.0 - expected),
        "reason": None,
        "observed_agreement": observed,
        "expected_agreement": expected,
    }


def agreement_statistics(records: Sequence[dict]) -> dict:
    manual = [record for record in records if record["source"] == "human_pair"]
    fields = {}
    for field in FIELDS:
        values_a = [record["human"]["annotator-a"]["canonical"][field] for record in manual]
        values_b = [record["human"]["annotator-b"]["canonical"][field] for record in manual]
        matrix = [[0 for _ in CATEGORIES] for _ in CATEGORIES]
        for left, right in zip(values_a, values_b):
            matrix[CATEGORIES.index(left)][CATEGORIES.index(right)] += 1
        kappa = cohen_kappa(values_a, values_b)
        fields[field] = {
            "n": len(manual),
            "categories": list(CATEGORIES),
            "confusion_matrix_rows_a_columns_b": matrix,
            "diagonal": sum(matrix[index][index] for index in range(len(CATEGORIES))),
            "observed_agreement": kappa["observed_agreement"],
            "marginal_a": {category: values_a.count(category) for category in CATEGORIES},
            "marginal_b": {category: values_b.count(category) for category in CATEGORIES},
            "cohen_kappa": {
                "status": kappa["status"], "value": kappa["value"], "reason": kappa["reason"],
                "expected_agreement": kappa["expected_agreement"],
            },
        }
    exact_numerator = sum(
        all(
            record["human"]["annotator-a"]["canonical"][field]
            == record["human"]["annotator-b"]["canonical"][field]
            for field in FIELDS
        )
        for record in manual
    )
    return {
        "scope": "manual-only",
        "n": len(manual),
        "fields": fields,
        "exact_five_field_agreement": {
            "numerator": exact_numerator,
            "denominator": len(manual),
            "rate": _defined(exact_numerator / len(manual)) if manual else _undefined("no_samples"),
        },
    }


def proposed_outcome(record: dict, field: str) -> str:
    value = record["aggregate"][field]
    if value == "tie":
        return "tie"
    if value == "uncertain":
        return "uncertain"
    return "win" if value == record["proposed_side"] else "loss"


def outcome_metrics(records: Sequence[dict], field: str) -> dict:
    outcomes = [proposed_outcome(record, field) for record in records]
    counts = {name: outcomes.count(name) for name in ("win", "loss", "tie", "uncertain")}
    total = len(outcomes)
    decisive = counts["win"] + counts["loss"]
    return {
        "wins": counts["win"],
        "losses": counts["loss"],
        "ties": counts["tie"],
        "uncertain": counts["uncertain"],
        "total": total,
        "tie_aware_win_rate": _defined(
            (counts["win"] + 0.5 * counts["tie"] + 0.5 * counts["uncertain"]) / total
        ) if total else _undefined("no_samples"),
        "decisive_win_rate": _defined(counts["win"] / decisive) if decisive else _undefined("no_decisive"),
        "tie_rate": _defined(counts["tie"] / total) if total else _undefined("no_samples"),
        "uncertain_rate": _defined(counts["uncertain"] / total) if total else _undefined("no_samples"),
    }


def rate_statistics(records: Sequence[dict], cfg: AnalysisConfig) -> dict:
    result = {}
    for scope, selected in (
        (cfg.primary_scope, list(records)),
        (cfg.diagnostic_scope, [record for record in records if record["source"] == "human_pair"]),
    ):
        result[scope] = {}
        for family in FAMILIES:
            family_records = [record for record in selected if record["family"] == family]
            if scope == cfg.primary_scope and len(family_records) != cfg.families[family].total:
                raise ValueError(f"formal family denominator drifted: {family}")
            result[scope][family] = {field: outcome_metrics(family_records, field) for field in FIELDS}
            for field, metrics in result[scope][family].items():
                if metrics["wins"] + metrics["losses"] + metrics["ties"] + metrics["uncertain"] != metrics["total"]:
                    raise ValueError(f"outcome count conservation failed: {scope}/{family}/{field}")
    return result


def _reachable(adjacency: dict[str, set[str]], start: str) -> set[str]:
    seen, pending = set(), [start]
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        pending.extend(adjacency[node] - seen)
    return seen


def _log_likelihood(abilities: np.ndarray, edges: Sequence[tuple[int, int]]) -> float:
    total = 0.0
    for winner, loser in edges:
        difference = float(abilities[winner] - abilities[loser])
        total += -float(np.logaddexp(0.0, -difference))
    return total


def fit_bradley_terry(
    nodes: Sequence[str],
    edge_rows: Sequence[dict],
    tolerance: float,
    max_iterations: int,
    max_step_halvings: int,
    required_families: Sequence[str] = FAMILIES,
) -> dict:
    nodes = list(nodes)
    if len(nodes) != len(set(nodes)) or not nodes:
        raise ValueError("Bradley-Terry nodes must be unique and non-empty")
    node_index = {node: index for index, node in enumerate(nodes)}
    for row in edge_rows:
        if row.get("winner") not in node_index or row.get("loser") not in node_index:
            raise ValueError("Bradley-Terry edge references unknown node")
        if row["winner"] == row["loser"]:
            raise ValueError("Bradley-Terry self edge invalid")
    family_counts = {family: sum(row.get("family") == family for row in edge_rows) for family in required_families}
    diagnostics = {
        "edge_count": len(edge_rows),
        "family_edge_counts": family_counts,
        "direction_counts": dict(sorted(Counter(f"{row['winner']}>{row['loser']}" for row in edge_rows).items())),
    }
    empty = {"nodes": nodes, "abilities": None, "iterations": 0, "max_abs_gradient": None,
             "log_likelihood": None, "diagnostics": diagnostics}
    if not edge_rows:
        return {"status": "no_decisive", "reason": "no decisive overall comparisons", **empty}
    if any(count == 0 for count in family_counts.values()):
        return {"status": "family_no_decisive", "reason": "a fixed comparison family has no decisive edge", **empty}

    undirected = {node: set() for node in nodes}
    directed = {node: set() for node in nodes}
    for row in edge_rows:
        winner, loser = row["winner"], row["loser"]
        undirected[winner].add(loser)
        undirected[loser].add(winner)
        directed[winner].add(loser)
    diagnostics["undirected_components"] = [
        sorted(component)
        for component in _components(undirected)
    ]
    if len(diagnostics["undirected_components"]) != 1:
        return {"status": "insufficient_connectivity", "reason": "undirected method graph is disconnected", **empty}
    strongly_connected = all(len(_reachable(directed, node)) == len(nodes) for node in nodes)
    diagnostics["directed_strongly_connected"] = strongly_connected
    if not strongly_connected:
        return {"status": "separation", "reason": "directed win graph is not strongly connected", **empty}

    edges = [(node_index[row["winner"]], node_index[row["loser"]]) for row in edge_rows]
    abilities = np.zeros(len(nodes), dtype=np.float64)
    converged, max_gradient, iterations = False, None, 0
    for iteration in range(max_iterations + 1):
        gradient = np.zeros(len(nodes), dtype=np.float64)
        hessian = np.zeros((len(nodes), len(nodes)), dtype=np.float64)
        for winner, loser in edges:
            difference = abilities[winner] - abilities[loser]
            probability = 1.0 / (1.0 + math.exp(-float(difference)))
            residual = 1.0 - probability
            weight = probability * (1.0 - probability)
            gradient[winner] += residual
            gradient[loser] -= residual
            hessian[winner, winner] -= weight
            hessian[loser, loser] -= weight
            hessian[winner, loser] += weight
            hessian[loser, winner] += weight
        max_gradient = float(np.max(np.abs(gradient)))
        if not np.all(np.isfinite(abilities)) or not np.all(np.isfinite(gradient)) or not np.all(np.isfinite(hessian)):
            return {"status": "non_finite", "reason": "non-finite Newton state", **empty,
                    "iterations": iteration, "max_abs_gradient": None}
        if max_gradient <= tolerance:
            converged, iterations = True, iteration
            break
        if iteration == max_iterations:
            iterations = iteration
            break
        try:
            delta_reduced = np.linalg.solve(hessian[:-1, :-1], -gradient[:-1])
        except np.linalg.LinAlgError:
            return {"status": "not_converged", "reason": "singular Newton system", **empty,
                    "iterations": iteration, "max_abs_gradient": max_gradient}
        delta = np.concatenate([delta_reduced, np.array([0.0])])
        delta -= delta.mean()
        old_likelihood = _log_likelihood(abilities, edges)
        accepted = False
        for halving in range(max_step_halvings + 1):
            candidate = abilities + delta * (0.5 ** halving)
            candidate -= candidate.mean()
            if np.all(np.isfinite(candidate)) and _log_likelihood(candidate, edges) >= old_likelihood - 1.0e-14:
                abilities = candidate
                accepted = True
                break
        if not accepted:
            return {"status": "not_converged", "reason": "Newton step-halving failed", **empty,
                    "iterations": iteration, "max_abs_gradient": max_gradient}
    if not converged:
        return {"status": "not_converged", "reason": "iteration limit reached", **empty,
                "iterations": iterations, "max_abs_gradient": max_gradient}
    return {
        "status": "ok",
        "reason": None,
        "nodes": nodes,
        "abilities": {node: float(abilities[index]) for index, node in enumerate(nodes)},
        "iterations": iterations,
        "max_abs_gradient": max_gradient,
        "log_likelihood": _log_likelihood(abilities, edges),
        "diagnostics": diagnostics,
    }


def _components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    remaining, result = set(adjacency), []
    while remaining:
        component = _reachable(adjacency, min(remaining))
        result.append(component)
        remaining -= component
    return result


def bradley_terry_statistics(records: Sequence[dict], cfg: AnalysisConfig) -> dict:
    edges = []
    for record in records:
        choice = record["aggregate"][cfg.bradley_terry.field]
        if choice not in ("X", "Y"):
            continue
        winner = record["candidate_x" if choice == "X" else "candidate_y"]["role"]
        loser = record["candidate_y" if choice == "X" else "candidate_x"]["role"]
        edges.append({"winner": winner, "loser": loser, "family": record["family"],
                      "comparison_id": record["comparison_id"]})
    return fit_bradley_terry(
        cfg.bradley_terry.nodes,
        edges,
        cfg.bradley_terry.tolerance,
        cfg.bradley_terry.max_iterations,
        cfg.bradley_terry.max_step_halvings,
    )


def cluster_bootstrap(
    records: Sequence[dict],
    fields: Sequence[str],
    families: Sequence[str],
    seed: int,
    iterations: int,
    expected_clusters: int,
    quantiles: Sequence[float] = (0.025, 0.975),
    quantile_method: str = "linear",
) -> tuple[list[dict], dict]:
    clusters = sorted({record["sample_id"] for record in records})
    if len(clusters) != expected_clusters:
        raise ValueError("bootstrap sample cluster cardinality mismatch")
    by_cluster = {cluster: [record for record in records if record["sample_id"] == cluster] for cluster in clusters}
    rng = np.random.Generator(np.random.PCG64(seed))
    draws = rng.integers(0, len(clusters), size=(iterations, len(clusters)))
    raw, values = [], {(family, field): [] for family in families for field in fields}
    invalid = {(family, field): Counter() for family in families for field in fields}
    for index, draw in enumerate(draws, start=1):
        selected_clusters = [clusters[int(value)] for value in draw]
        sampled = [record for cluster in selected_clusters for record in by_cluster[cluster]]
        statistics = {}
        for family in families:
            family_records = [record for record in sampled if record["family"] == family]
            statistics[family] = {}
            for field in fields:
                metric = outcome_metrics(family_records, field)["tie_aware_win_rate"]
                statistics[family][field] = metric
                if metric["status"] == "defined":
                    values[(family, field)].append(metric["value"])
                else:
                    invalid[(family, field)][metric["reason"]] += 1
        raw.append({"replicate": index, "draw": selected_clusters, "statistics": statistics})
    summary = {}
    for family in families:
        summary[family] = {}
        for field in fields:
            valid = values[(family, field)]
            if valid:
                lower, upper = np.quantile(valid, quantiles, method=quantile_method)
                interval = {"status": "defined", "lower": float(lower), "upper": float(upper), "reason": None}
            else:
                interval = {"status": "undefined", "lower": None, "upper": None, "reason": "no_valid_replicates"}
            summary[family][field] = {
                "iterations": iterations,
                "valid_replicates": len(valid),
                "invalid_replicates": iterations - len(valid),
                "invalid_reasons": dict(sorted(invalid[(family, field)].items())),
                "percentile_95_ci": interval,
            }
    return raw, {
        "cluster": "sample_id", "clusters": clusters, "cluster_count": len(clusters),
        "rng": "numpy.Generator(PCG64)", "seed": seed, "iterations": iterations,
        "quantiles": list(quantiles), "quantile_method": quantile_method, "metrics": summary,
    }


def _descriptive(values: Sequence[float]) -> dict:
    if not values:
        return {"status": "unavailable", "reason": "no_values", "count": 0}
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("descriptive values must be finite")
    q1, median, q3 = np.quantile(array, [0.25, 0.5, 0.75], method="linear")
    return {
        "status": "available", "reason": None, "count": len(values),
        "sum": float(array.sum()), "mean": float(array.mean()), "median": float(median),
        "q1": float(q1), "q3": float(q3), "min": float(array.min()), "max": float(array.max()),
    }


def annotation_descriptives(records: Sequence[dict]) -> dict:
    confidence, elapsed = {}, {}
    pooled_confidence = []
    for annotator in ("annotator-a", "annotator-b"):
        human = [record["human"][annotator] for record in records if record["source"] == "human_pair"]
        values = [item["confidence"] for item in human]
        pooled_confidence.extend(values)
        confidence[annotator] = {
            **_descriptive(values),
            "frequencies": {str(code): values.count(code) for code in (0.0, 0.25, 0.5, 0.75, 1.0)},
            "weighted_answers": False,
        }
        elapsed[annotator] = {
            **_descriptive([item["current_view_elapsed_seconds"] for item in human]),
            "unit": "seconds",
            "semantics": "current-view-server-elapsed-not-active-labor",
        }
    confidence["pooled"] = {
        **_descriptive(pooled_confidence),
        "frequencies": {str(code): pooled_confidence.count(code) for code in (0.0, 0.25, 0.5, 0.75, 1.0)},
        "weighted_answers": False,
    }
    return {"confidence": confidence, "elapsed": elapsed}


def _cost(value, unit: str, path: Path, semantics: str) -> dict:
    return {
        "status": "available", "value": value, "unit": unit,
        "source_path": path.as_posix(), "source_sha256": sha256_file(path), "semantics": semantics,
    }


def cost_statistics(
    records: Sequence[dict], selection: Path, metrics: Path, design: Path, ingest: Path,
    analysis_compute_seconds: float, aggregate: Path,
) -> dict:
    manifest = read_json(ingest)
    candidates = manifest.get("candidates", [])
    generation_runtimes = [float(item["runtime_seconds"]) for item in candidates]
    generation_vram = [float(item["peak_vram_mb"]) for item in candidates if item.get("peak_vram_mb") is not None]
    scoring = read_json(metrics / "scoring-runtime.json")
    design_data = read_json(design / "design.json")
    selections = [json.loads(line) for line in (selection / "selections.jsonl").read_text(encoding="utf-8").splitlines()]
    elapsed = annotation_descriptives(records)["elapsed"]
    entries = {
        "e0_generation_runtime_sum": _cost(sum(generation_runtimes), "seconds", ingest,
            "sum of audited historical per-candidate generation runtime; not rerun by Defense MVP"),
        "e0_generation_peak_vram_max": _cost(max(generation_vram), "MB", ingest,
            "maximum reported historical per-candidate peak VRAM") if generation_vram else {
                "status": "unavailable", "value": None, "unit": "MB", "source_path": ingest.as_posix(),
                "source_sha256": sha256_file(ingest), "semantics": "historical peak VRAM", "reason": "missing_values",
            },
        "d2_scoring_total_elapsed": _cost(float(scoring["total_cpu_seconds"]), "seconds",
            metrics / "scoring-runtime.json", "CPU-only pipeline elapsed perf_counter; not process CPU time"),
        "d2_scoring_per_candidate_elapsed": _cost(float(scoring["total_cpu_seconds"]) / len(candidates),
            "seconds/candidate", metrics / "scoring-runtime.json", "total elapsed divided by 50 validated candidates"),
        "d2_selection_elapsed": {
            "status": "unavailable", "value": None, "unit": "seconds", "source_path": None,
            "source_sha256": None, "semantics": "selection algorithm elapsed", "reason": "no trusted timer in D2 receipt",
        },
        "d2_n1_candidate_exposures": _cost(sum(len(trial["subsets"]["1"]) for trial in design_data["trials"]),
            "candidate-exposures", design / "design.json", "35 trial nested N=1 subsets"),
        "d2_n2_candidate_exposures": _cost(sum(len(trial["subsets"]["2"]) for trial in design_data["trials"]),
            "candidate-exposures", design / "design.json", "35 trial nested N=2 subsets"),
        "d2_n4_candidate_exposures": _cost(sum(len(trial["subsets"]["4"]) for trial in design_data["trials"]),
            "candidate-exposures", design / "design.json", "35 trial nested N=4 subsets"),
        "d2_selection_records": _cost(len(selections), "records", selection / "selections.jsonl",
            "three methods x N=1/2/4 x 35 trials"),
        "d4_analysis_compute_elapsed": {
            "status": "available", "value": analysis_compute_seconds, "unit": "seconds",
            "source_path": None, "source_sha256": None,
            "semantics": "current D4 analysis perf_counter before artifact publication",
        },
    }
    for annotator in ("annotator-a", "annotator-b"):
        entries[f"d3_{annotator}_current_view_elapsed_sum"] = {
            "status": "available", "value": elapsed[annotator]["sum"], "unit": "seconds",
            "source_path": (aggregate / "aggregate.jsonl").as_posix(),
            "source_sha256": sha256_file(aggregate / "aggregate.jsonl"),
            "semantics": "current-view server elapsed including pauses/background/resume; not active labor",
        }
    return {"entries": entries, "limitations": [
        "annotation elapsed is not precise active viewing time or labor",
        "historical E0 runtime/VRAM came from the audited handoff and was not rerun locally",
        "D2 selection elapsed is unavailable because no trusted timer was recorded",
    ]}


def build_failure_cases(records: Sequence[dict], cfg: AnalysisConfig) -> dict:
    cases = []
    for record in records:
        outcome = proposed_outcome(record, cfg.failure_cases.field)
        if outcome in cfg.failure_cases.proposed_outcomes:
            family_cfg = cfg.families[record["family"]]
            cases.append({
                "comparison_id": record["comparison_id"], "family": record["family"],
                "sample_id": record["sample_id"], "trial_id": record["trial_id"],
                "replicate": record["replicate"], "source": record["source"],
                "proposed_side": record["proposed_side"], "proposed_role": family_cfg.proposed_role,
                "comparator_role": family_cfg.comparator_role, "overall_outcome": outcome,
            })
    cases.sort(key=lambda item: tuple(item[key] for key in cfg.failure_cases.sort))
    return {
        "schema_version": "1", "protocol": cfg.protocol,
        "rule": {"field": cfg.failure_cases.field, "outcomes": cfg.failure_cases.proposed_outcomes,
                 "sort": cfg.failure_cases.sort},
        "count": len(cases), "cases": cases,
    }


def build_main_rows(rates: dict, bootstrap: dict, cfg: AnalysisConfig) -> list[dict]:
    rows = []
    for scope in (cfg.primary_scope, cfg.diagnostic_scope):
        for family in FAMILIES:
            for field in FIELDS:
                metric = rates[scope][family][field]
                ci = bootstrap["metrics"][family][field]["percentile_95_ci"] if scope == cfg.primary_scope else {
                    "status": "not_applicable", "lower": None, "upper": None,
                }
                rows.append({
                    "scope": scope, "family": family, "field": field,
                    "wins": metric["wins"], "losses": metric["losses"], "ties": metric["ties"],
                    "uncertain": metric["uncertain"], "total": metric["total"],
                    "tie_aware_status": metric["tie_aware_win_rate"]["status"],
                    "tie_aware_win_rate": metric["tie_aware_win_rate"]["value"],
                    "decisive_status": metric["decisive_win_rate"]["status"],
                    "decisive_win_rate": metric["decisive_win_rate"]["value"],
                    "tie_rate": metric["tie_rate"]["value"],
                    "uncertain_rate": metric["uncertain_rate"]["value"],
                    "bootstrap_status": ci["status"], "bootstrap_lower": ci.get("lower"),
                    "bootstrap_upper": ci.get("upper"),
                })
    return rows


def build_agreement_rows(agreement: dict) -> list[dict]:
    rows = []
    for field in FIELDS:
        item = agreement["fields"][field]
        rows.append({
            "field": field, "n": item["n"], "diagonal": item["diagonal"],
            "observed_agreement": item["observed_agreement"],
            "kappa_status": item["cohen_kappa"]["status"],
            "cohen_kappa": item["cohen_kappa"]["value"],
            "kappa_reason": item["cohen_kappa"]["reason"],
        })
    return rows


def build_summary(
    records: Sequence[dict], agreement: dict, rates: dict, bootstrap: dict, bt: dict,
    annotations: dict, failure_case_count: int, cfg: AnalysisConfig,
) -> dict:
    return {
        "schema_version": "1", "protocol": cfg.protocol, "scope": cfg.primary_scope,
        "records": len(records), "human_pairs": agreement["n"],
        "automatic_ties": sum(record["source"] == "automatic_tie" for record in records),
        "sample_clusters": bootstrap["cluster_count"],
        "agreement": agreement,
        "rates": rates,
        "bootstrap": bootstrap,
        "bradley_terry": bt,
        "annotations": annotations,
        "failure_case_count": failure_case_count,
        "limitations": [
            "two annotators, including one developer participant",
            "seven sample clusters yield descriptive small-sample uncertainty only",
            "annotation elapsed is current-view server time, not active labor",
            "Bradley-Terry abilities are reported only when finite MLE identification checks pass",
        ],
    }


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())


def _preserve_failed(staging: Path, output: Path, exc: Exception) -> None:
    if not staging.exists():
        return
    try:
        write_json(staging / "ANALYSIS_FAILED.json", {"status": "failed", "error": str(exc), "at": now()})
    finally:
        rename_noreplace(staging, output.with_name(f".{output.name}-{uuid.uuid4().hex}.failed"))


def analyze_aggregate(
    aggregate: Path,
    selection: Path,
    metrics: Path,
    design: Path,
    ingest: Path,
    config_path: Path,
    output: Path,
) -> dict:
    started = time.perf_counter()
    aggregate, selection, metrics, design, ingest, config_path, output = [
        Path(path).resolve() for path in (aggregate, selection, metrics, design, ingest, config_path, output)
    ]
    cfg = load_analysis_config(config_path)
    staging = stage(output)
    try:
        rows = load_aggregate(aggregate, cfg)
        verify_sums(selection, "SELECTION_SHA256SUMS")
        verify_sums(metrics, "METRICS_SHA256SUMS")
        verify_sums(design, "DESIGN_SHA256SUMS")
        verify_sums(ingest.parent, "INGEST_SHA256SUMS")
        aggregate_inputs = read_json(aggregate / "input-manifest.json")["inputs"]
        current = {
            "analysis_config": config_path,
            "comparisons": selection / "comparisons.json",
            "selection_lock": selection / "selection-lock.json",
            "selection_inventory": selection / "SELECTION_SHA256SUMS",
            "metrics": metrics / "metrics.jsonl",
            "metrics_lock": metrics / "metrics-config-lock.json",
            "metrics_inventory": metrics / "METRICS_SHA256SUMS",
            "design": design / "design.json",
            "design_lock": design / "design-lock.json",
            "design_inventory": design / "DESIGN_SHA256SUMS",
            "ingest": ingest,
            "ingest_inventory": ingest.parent / "INGEST_SHA256SUMS",
        }
        for name, path in current.items():
            if aggregate_inputs.get(name, {}).get("sha256") != sha256_file(path):
                raise ValueError(f"aggregate/analysis input identity mismatch: {name}")

        agreement = agreement_statistics(rows)
        if agreement["n"] != cfg.agreement.expected_comparisons:
            raise ValueError("manual agreement denominator drifted")
        rates = rate_statistics(rows, cfg)
        bt = bradley_terry_statistics(rows, cfg)
        bootstrap_rows, bootstrap = cluster_bootstrap(
            rows, cfg.bootstrap.fields, FAMILIES, cfg.bootstrap.seed, cfg.bootstrap.iterations,
            cfg.bootstrap.expected_clusters, cfg.bootstrap.quantiles, cfg.bootstrap.quantile_method,
        )
        annotations = annotation_descriptives(rows)
        compute_elapsed = time.perf_counter() - started
        costs = cost_statistics(rows, selection, metrics, design, ingest, compute_elapsed, aggregate)

        failure_cases = build_failure_cases(rows, cfg)

        write_json(staging / "confusion-matrices.json", agreement)
        _write_jsonl(staging / "bootstrap.jsonl", bootstrap_rows)
        write_json(staging / "bt.json", bt)
        write_json(staging / "costs.json", costs)
        write_json(staging / "failure-cases.json", failure_cases)
        write_json(staging / "input-manifest.json", {
            "schema_version": "1", "protocol": cfg.protocol,
            "inputs": {
                "aggregate_inventory": {"sha256": sha256_file(aggregate / "SHA256SUMS")},
                **{name: {"sha256": sha256_file(path)} for name, path in current.items()},
            },
        })
        main_rows = build_main_rows(rates, bootstrap, cfg)
        _write_csv(staging / "main-table.csv", list(main_rows[0]), main_rows)
        agreement_rows = build_agreement_rows(agreement)
        _write_csv(staging / "agreement.csv", list(agreement_rows[0]), agreement_rows)
        summary = build_summary(
            rows, agreement, rates, bootstrap, bt, annotations, failure_cases["count"], cfg
        )
        write_json(staging / "summary.json", summary)
        receipt = {
            "schema_version": "1", "status": "passed", "protocol": cfg.protocol,
            "created_at": now(), "analysis_elapsed_seconds": time.perf_counter() - started,
            "records": len(rows), "sample_clusters": bootstrap["cluster_count"],
            "bootstrap_iterations": cfg.bootstrap.iterations,
            "summary_canonical_sha256": canonical_sha256(summary),
            "environment": source_evidence(),
        }
        write_json(staging / "analysis-receipt.json", receipt)
        write_sums(staging)
        rename_noreplace(staging, output)
        return receipt
    except Exception as exc:
        _preserve_failed(staging, output, exc)
        raise
