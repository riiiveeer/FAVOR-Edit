"""Fail-closed verification for E2 preparation, selection, human, analysis, and report artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from w1_pipeline.hashing import sha256_file

from .io import atomic_write_new_json, read_json
from .models import E2AdjudicatedComparisonV1, E2SelectionBundleV1


def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _verify_preparation_checksums(root: Path) -> List[str]:
    failures = []
    sums = Path(root) / "PREPARATION_SHA256SUMS"
    if not sums.is_file():
        return ["missing_preparation_checksums"]
    seen = set()
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip() or "  " not in line:
            failures.append("malformed_preparation_checksum_row")
            continue
        expected, relative = line.split("  ", 1)
        if relative in seen or relative.startswith("/") or ".." in Path(relative).parts:
            failures.append(f"invalid_preparation_checksum_path:{relative}")
            continue
        seen.add(relative)
        target = Path(root) / relative
        if not target.is_file():
            failures.append(f"missing_preparation_file:{relative}")
        elif sha256_file(target) != expected:
            failures.append(f"preparation_checksum_mismatch:{relative}")
    return failures


def verify_e2(
    preparation_root: Path, selection_path: Path, adjudicated_path: Path,
    analysis_dir: Path, report_dir: Path, primary_results_path: Path,
    reward_path: Path, output: Path, rubric_results_path: Optional[Path] = None,
    auxiliary_rubric_path: Optional[Path] = None,
) -> dict:
    failures = _verify_preparation_checksums(preparation_root)
    selection = E2SelectionBundleV1.model_validate(read_json(selection_path))
    adjudicated = [
        E2AdjudicatedComparisonV1.model_validate(item) for item in _read_jsonl(adjudicated_path)
    ]
    metrics = read_json(Path(analysis_dir) / "metrics.json")
    costs = read_json(Path(analysis_dir) / "costs.json")
    report_manifest = read_json(Path(report_dir) / "report-manifest.json")
    preparation_receipt_path = Path(preparation_root) / "e2-preparation-v01.json"
    preparation_report_path = Path(preparation_root) / "preparation-verification-v01.json"
    if not preparation_receipt_path.is_file() or read_json(preparation_receipt_path).get("status") != "passed":
        failures.append("preparation_receipt_not_passed")
    if not preparation_report_path.is_file() or read_json(preparation_report_path).get("status") != "passed":
        failures.append("preparation_verification_not_passed")
    dependencies = selection.dependencies
    preparation_files = {
        "design_sha256": Path(preparation_root) / "bon-design.json",
        "pairs_sha256": Path(preparation_root) / "inputs" / "pairs.jsonl",
    }
    for key, path in preparation_files.items():
        if not path.is_file() or dependencies.get(key) != sha256_file(path):
            failures.append(f"selection_{key}_mismatch")
    external_files = {
        "primary_results_sha256": primary_results_path,
        "reward_v0_sha256": reward_path,
        "rubric_results_sha256": rubric_results_path,
        "auxiliary_rubric_sha256": auxiliary_rubric_path,
    }
    for key, path in external_files.items():
        actual = sha256_file(path) if path else None
        if dependencies.get(key) != actual:
            failures.append(f"selection_{key}_mismatch")
    if len(adjudicated) != 80 or len({item.comparison_id for item in adjudicated}) != 80:
        failures.append("adjudicated_count_or_identity")
    if {item.comparison_id for item in adjudicated} != {
        item.comparison_id for item in selection.human_comparisons
    }:
        failures.append("adjudicated_selection_plan_mismatch")
    expected_selection_count = 1280 if selection.method_status["equal-linear"] == "AVAILABLE" else 640
    if len(selection.selections) != expected_selection_count:
        failures.append("selection_count")
    if metrics.get("human_comparisons") != 80 or metrics.get("inputs", {}).get("selection_sha256") != sha256_file(selection_path):
        failures.append("analysis_selection_identity")
    if metrics.get("inputs", {}).get("adjudicated_sha256") != sha256_file(adjudicated_path):
        failures.append("analysis_adjudicated_identity")
    if metrics.get("overall", {}).get("bootstrap_95_ci", {}).get("iterations") != 2000:
        failures.append("analysis_bootstrap_iterations")
    if metrics.get("overall", {}).get("bootstrap_95_ci", {}).get("clusters") != 10:
        failures.append("analysis_bootstrap_clusters")
    if costs.get("actual_shared_eight_candidate_pool", {}).get("generated_candidates") != 80:
        failures.append("cost_pool_count")
    if costs.get("actual_shared_eight_candidate_pool", {}).get("primary_judge_requests") != 560:
        failures.append("cost_primary_request_count")
    if report_manifest.get("analysis_metrics_sha256") != sha256_file(Path(analysis_dir) / "metrics.json"):
        failures.append("report_metrics_identity")
    if report_manifest.get("analysis_costs_sha256") != sha256_file(Path(analysis_dir) / "costs.json"):
        failures.append("report_costs_identity")
    for name, expected in report_manifest.get("artifacts", {}).items():
        artifact = Path(report_dir) / name
        if not artifact.is_file() or sha256_file(artifact) != expected:
            failures.append(f"report_artifact_identity:{name}")
    if selection.measurement_mode != "formal-command" and (
        selection.research_measurements != 0
        or metrics.get("research_measurements") != 0
        or costs.get("research_measurements") != 0
        or report_manifest.get("research_measurements") != 0
    ):
        failures.append("mock_replay_research_measurements_nonzero")
    payload = {
        "schema_version": "1", "status": "passed" if not failures else "failed",
        "ready_for_research_interpretation": not failures and selection.measurement_mode == "formal-command",
        "measurement_mode": selection.measurement_mode,
        "research_measurements": selection.research_measurements,
        "counts": {
            "selections": len(selection.selections), "human_comparisons": len(selection.human_comparisons),
            "adjudicated": len(adjudicated), "preparation_checksum_failures": len([
                item for item in failures if item.startswith(("missing_preparation", "malformed_preparation", "invalid_preparation", "preparation_checksum"))
            ]),
        },
        "failures": failures,
    }
    atomic_write_new_json(output, payload)
    return payload
