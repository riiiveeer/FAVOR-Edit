"""Independent frozen-label qualification for auxiliary rubric signals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import yaml

from e1_judge.metrics import evaluate_method
from e1_judge.models import AdjudicatedLabelV2, FrozenProtocolV2, JudgeResultV2, PairRecordV2
from w1_pipeline.hashing import sha256_file

from .io import atomic_write_new_json


def _jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def qualify_auxiliary_rubric(
    pairs_path: Path, human_path: Path, results_path: Path, dev_metrics_path: Path,
    e1_config_path: Path, frozen_protocol_path: Path, output: Path,
) -> dict:
    pairs = [PairRecordV2.model_validate(item) for item in _jsonl(pairs_path)]
    pairs = [pair for pair in pairs if pair.split == "frozen-eval"]
    labels = {item.pair_id: item for item in [AdjudicatedLabelV2.model_validate(value) for value in _jsonl(human_path)]}
    results = [JudgeResultV2.model_validate(item) for item in _jsonl(results_path)]
    results = [item for item in results if item.split == "frozen-eval" and item.method == "rubric-swap-v1"]
    if len(pairs) != 70 or len(labels) != 100 or len(results) != 140:
        raise ValueError("auxiliary rubric qualification requires 70 frozen pairs, 100 labels, and 140 rubric results")
    dev_metrics = json.loads(Path(dev_metrics_path).read_text(encoding="utf-8"))
    rubric_dev = dev_metrics.get("methods", {}).get("rubric-swap-v1")
    if not rubric_dev or rubric_dev.get("confidence_threshold") is None:
        raise ValueError("dev metrics do not contain a frozen rubric confidence threshold")
    threshold = float(rubric_dev["confidence_threshold"])
    config = yaml.safe_load(Path(e1_config_path).read_text(encoding="utf-8"))
    protocol = FrozenProtocolV2.model_validate(json.loads(Path(frozen_protocol_path).read_text(encoding="utf-8")))
    metrics = evaluate_method(
        pairs, labels, results, "rubric-swap-v1", threshold, 0.0,
        int(config["bootstrap_seed"]), int(config["bootstrap_iterations"]),
    )
    categories = [item["decisive_accuracy"] for item in metrics["categories"].values()]
    gates = {
        "accuracy": metrics["decisive_accuracy"] >= float(config["thresholds"]["accuracy"]),
        "swap_consistency": (metrics["swap_consistency"] or 0.0) >= float(config["thresholds"]["swap_consistency"]),
        "coverage": metrics["coverage"] >= float(config["thresholds"]["high_confidence_coverage"]),
        "categories": min(categories, default=0.0) >= float(config["thresholds"]["min_category_accuracy"]),
    }
    decision = "PASS_AUXILIARY_RUBRIC" if all(gates.values()) else "FAIL_AUXILIARY_RUBRIC"
    payload = {
        "schema_version": "1", "decision": decision, "method": "rubric-swap-v1",
        "confidence_threshold": threshold, "gates": gates, "metrics": metrics,
        "e1_protocol_fingerprint": protocol.protocol_fingerprint,
        "inputs": {
            "pairs_sha256": sha256_file(pairs_path), "human_sha256": sha256_file(human_path),
            "results_sha256": sha256_file(results_path), "dev_metrics_sha256": sha256_file(dev_metrics_path),
            "config_sha256": sha256_file(e1_config_path), "protocol_sha256": sha256_file(frozen_protocol_path),
        },
        "does_not_replace_reward_v0": True,
    }
    atomic_write_new_json(output, payload)
    return payload
