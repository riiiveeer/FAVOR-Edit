"""E1 reliability metrics (§16)."""

import json
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def _load_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _decisive(pairs: List[dict], labels: Dict[str, dict]) -> List[dict]:
    out = []
    for pair in pairs:
        label = labels.get(pair["pair_id"])
        if label is None:
            continue
        if label["overall_preference"] in ("a", "b"):
            out.append(pair)
    return out


def pairwise_accuracy(pairs: List[dict], labels: Dict[str, dict], results: Dict[str, dict]) -> Dict[str, float]:
    """Compute decisive-only and effective accuracy plus coverage."""
    correct = 0
    decisive = 0
    all_pairs = 0
    covered = 0
    for pair in pairs:
        label = labels.get(pair["pair_id"])
        if label is None or label["overall_preference"] not in ("a", "b"):
            continue
        human = label["overall_preference"]
        human_candidate = pair["candidate_left_id"] if human == "a" else pair["candidate_right_id"]
        # Judge result is per request; fall back to a representative result.
        judge = results.get(pair["pair_id"])
        decisive += 1
        all_pairs += 1
        if judge is not None and judge.get("overall_preference") in ("a", "b"):
            covered += 1
            judge_candidate = pair["candidate_left_id"] if judge["overall_preference"] == "a" else pair["candidate_right_id"]
            if judge_candidate == human_candidate:
                correct += 1

    decisive_accuracy = correct / decisive if decisive else 0.0
    effective_accuracy = correct / max(1, all_pairs)
    coverage = covered / decisive if decisive else 0.0
    return {"decisive_accuracy": decisive_accuracy, "effective_accuracy": effective_accuracy, "coverage": coverage}


def swap_consistency(results: Dict[str, dict]) -> float:
    """Fraction of pairs where both directions map to the same canonical candidate.

    Each result must carry ``candidate_a_id``/``candidate_b_id`` (screen-side
    identities) so the screen preference can be mapped back to the canonical
    (lexicographic) candidate identity. Two tie directions are consistent; two
    uncertain directions are consistent; a decisive vs tie/uncertain mismatch is
    inconsistent.
    """
    by_pair: Dict[str, List[dict]] = {}
    for result in results.values():
        by_pair.setdefault(result.get("pair_id", ""), []).append(result)

    consistent = 0
    total = 0
    for pair_id, records in by_pair.items():
        directions = [r for r in records if r.get("comparison_direction") in ("a_vs_b", "b_vs_a")]
        if len(directions) < 2:
            continue
        mapped = [_map_to_canonical(r) for r in directions]
        total += 1
        if mapped[0] == mapped[1]:
            consistent += 1
        elif set(mapped) <= {"tie", "uncertain"}:
            consistent += 1
    return consistent / total if total else 0.0


def _map_to_canonical(result: dict) -> str:
    pref = result.get("overall_preference")
    if pref not in ("a", "b"):
        return pref if pref in ("tie", "uncertain") else "uncertain"
    a_id = result.get("candidate_a_id")
    b_id = result.get("candidate_b_id")
    if not a_id or not b_id:
        return "uncertain"
    canonical_a = min(a_id, b_id)
    screen_choice = a_id if pref == "a" else b_id
    return "a" if screen_choice == canonical_a else "b"


def position_bias(results: Dict[str, dict]) -> Dict[str, float]:
    left = 0
    right = 0
    decisive = 0
    for result in results.values():
        pref = result.get("overall_preference")
        direction = result.get("comparison_direction")
        if pref not in ("a", "b"):
            continue
        decisive += 1
        if pref == "a":
            left += 1
        else:
            right += 1
    return {
        "left_rate": left / decisive if decisive else 0.0,
        "right_rate": right / decisive if decisive else 0.0,
    }


def cluster_bootstrap_ci(pairs: List[dict], labels: Dict[str, dict], results: Dict[str, dict], seed: int, iterations: int) -> Dict[str, List[float]]:
    """Cluster bootstrap 95% CI over sample_id for decisive accuracy."""
    by_sample: Dict[str, List[dict]] = {}
    for pair in pairs:
        label = labels.get(pair["pair_id"])
        if label is not None and label["overall_preference"] in ("a", "b"):
            by_sample.setdefault(pair["sample_id"], []).append(pair)
    samples = list(by_sample.keys())
    rng = random.Random(seed)
    values = []
    for _ in range(iterations):
        resampled = []
        for _ in range(len(samples)):
            sample = rng.choice(samples)
            resampled.extend(by_sample[sample])
        values.append(pairwise_accuracy(resampled, labels, results)["decisive_accuracy"])
    values.sort()
    lower = values[int(0.025 * len(values))]
    upper = values[int(0.975 * len(values))]
    return {"lower": lower, "upper": upper}


def category_metrics(pairs: List[dict], labels: Dict[str, dict], results: Dict[str, dict]) -> Dict[str, dict]:
    out = {}
    for task_type in ("attribute", "object", "local"):
        subset = [p for p in pairs if p["task_type"] == task_type]
        acc = pairwise_accuracy(subset, labels, results)
        out[task_type] = {"pairs": len(subset), **acc}
    return out


def analyze(pairs: Path, human: Path, results: Path, config: Path, output_dir: Path) -> Dict[str, dict]:
    pair_records = _load_jsonl(pairs)
    labels = {label["pair_id"]: label for label in _load_jsonl(human)}
    result_records = _load_jsonl(results)
    results_by_pair = {}
    for record in result_records:
        results_by_pair.setdefault(record.get("pair_id", ""), record)

    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    seed = int(cfg.get("bootstrap_seed", 20260820))
    iterations = int(cfg.get("bootstrap_iterations", 2000))

    metrics = {
        "pairwise": pairwise_accuracy(pair_records, labels, results_by_pair),
        "swap_consistency": swap_consistency(results_by_pair),
        "position_bias": position_bias(results_by_pair),
        "categories": category_metrics(pair_records, labels, results_by_pair),
        "ci": cluster_bootstrap_ci(pair_records, labels, results_by_pair, seed, iterations),
    }

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics
