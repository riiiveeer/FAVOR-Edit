"""Tests for E1 metrics (§18.6)."""

import json

from e1_judge.metrics import (
    analyze,
    cluster_bootstrap_ci,
    pairwise_accuracy,
    position_bias,
    swap_consistency,
)
from e1_judge.ranking import fit_utilities, kendall_tau, spearman


def _pair(pair_id, sample_id, task_type="attribute"):
    return dict(
        pair_id=pair_id,
        sample_id=sample_id,
        task_type=task_type,
        candidate_left_id=f"{sample_id}-s101",
        candidate_right_id=f"{sample_id}-s202",
    )


def _labels(pair_ids, preference="a"):
    return {
        pid: {"pair_id": pid, "overall_preference": preference}
        for pid in pair_ids
    }


def test_accuracy_100_percent():
    pairs = [_pair("p1", "s1")]
    labels = _labels(["p1"], "a")
    results = {"p1": {"pair_id": "p1", "overall_preference": "a"}}
    metrics = pairwise_accuracy(pairs, labels, results)
    assert metrics["decisive_accuracy"] == 1.0


def test_accuracy_0_percent_when_reversed():
    pairs = [_pair("p1", "s1")]
    labels = _labels(["p1"], "a")
    results = {"p1": {"pair_id": "p1", "overall_preference": "b"}}
    metrics = pairwise_accuracy(pairs, labels, results)
    assert metrics["decisive_accuracy"] == 0.0


def test_tie_and_uncertain_not_counted_as_correct():
    pairs = [_pair("p1", "s1")]
    labels = _labels(["p1"], "a")
    results = {"p1": {"pair_id": "p1", "overall_preference": "tie"}}
    metrics = pairwise_accuracy(pairs, labels, results)
    assert metrics["decisive_accuracy"] == 0.0
    assert metrics["coverage"] == 0.0


def test_swap_consistency():
    # a_vs_b prefers screen A (=s101); b_vs_a prefers screen B (=s101, since A/B swapped).
    results = {
        "r1": {"pair_id": "p1", "comparison_direction": "a_vs_b", "overall_preference": "a",
               "candidate_a_id": "s101", "candidate_b_id": "s202"},
        "r2": {"pair_id": "p1", "comparison_direction": "b_vs_a", "overall_preference": "b",
               "candidate_a_id": "s202", "candidate_b_id": "s101"},
    }
    assert swap_consistency(results) == 1.0


def test_swap_consistency_inconsistent():
    results = {
        "r1": {"pair_id": "p1", "comparison_direction": "a_vs_b", "overall_preference": "a",
               "candidate_a_id": "s101", "candidate_b_id": "s202"},
        "r2": {"pair_id": "p1", "comparison_direction": "b_vs_a", "overall_preference": "a",
               "candidate_a_id": "s202", "candidate_b_id": "s101"},
    }
    assert swap_consistency(results) == 0.0


def test_position_bias_flip():
    results = {
        "r1": {"comparison_direction": "a_vs_b", "overall_preference": "a"},
        "r2": {"comparison_direction": "a_vs_b", "overall_preference": "b"},
    }
    bias = position_bias(results)
    assert bias["left_rate"] == 0.5
    assert bias["right_rate"] == 0.5


def test_cluster_bootstrap_reproducible():
    pairs = [_pair(f"p{i}", "s1") for i in range(4)]
    labels = _labels([f"p{i}" for i in range(4)], "a")
    results = {f"p{i}": {"pair_id": f"p{i}", "overall_preference": "a"} for i in range(4)}
    ci1 = cluster_bootstrap_ci(pairs, labels, results, seed=42, iterations=200)
    ci2 = cluster_bootstrap_ci(pairs, labels, results, seed=42, iterations=200)
    assert ci1 == ci2


def test_fit_utilities_known_order():
    prefs = [
        {"a": "x", "b": "y", "choice": "a"},
        {"a": "x", "b": "y", "choice": "a"},
        {"a": "x", "b": "z", "choice": "a"},
    ]
    utilities = fit_utilities(prefs)
    assert utilities["x"] > utilities["y"]
    assert utilities["x"] >= utilities["z"]


def test_kendall_tau_known():
    a = {"x": 1.0, "y": 0.5, "z": 0.0}
    b = {"x": 1.0, "y": 0.5, "z": 0.0}
    assert kendall_tau(a, b) == 1.0


def test_spearman_known():
    a = {"x": 1.0, "y": 0.5, "z": 0.0}
    b = {"x": 1.0, "y": 0.5, "z": 0.0}
    assert spearman(a, b) == 1.0


def test_analyze_writes_metrics(tmp_path):
    pairs_path = tmp_path / "pairs.jsonl"
    human_path = tmp_path / "human.jsonl"
    results_path = tmp_path / "results.jsonl"
    config_path = tmp_path / "pilot.yaml"
    pairs = [_pair(f"p{i}", "s1") for i in range(4)]
    pairs_path.write_text("\n".join(json.dumps(p) for p in pairs) + "\n", encoding="utf-8")
    human_path.write_text(
        "\n".join(json.dumps({"pair_id": f"p{i}", "overall_preference": "a"}) for i in range(4)) + "\n",
        encoding="utf-8",
    )
    results_path.write_text(
        "\n".join(json.dumps({"pair_id": f"p{i}", "overall_preference": "a"}) for i in range(4)) + "\n",
        encoding="utf-8",
    )
    config_path.write_text("bootstrap_seed: 42\nbootstrap_iterations: 50\n", encoding="utf-8")
    output = tmp_path / "analysis"
    metrics = analyze(pairs_path, human_path, results_path, config_path, output)
    assert (output / "metrics.json").is_file()
    assert metrics["pairwise"]["decisive_accuracy"] == 1.0
