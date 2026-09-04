"""Independent recomputation and integrity verification for D4 artifacts."""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
from pathlib import Path

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .aggregation import load_aggregate, validate_formal_sources
from .analysis import (
    agreement_statistics,
    annotation_descriptives,
    bradley_terry_statistics,
    build_agreement_rows,
    build_failure_cases,
    build_main_rows,
    build_summary,
    cluster_bootstrap,
    cost_statistics,
    rate_statistics,
)
from .analysis_models import FAMILIES, load_analysis_config
from .annotation_bundle import read_json, source_evidence, verify_sums
from .io import rename_noreplace, write_json


ANALYSIS_FILES = {
    "summary.json",
    "main-table.csv",
    "agreement.csv",
    "confusion-matrices.json",
    "bootstrap.jsonl",
    "bt.json",
    "costs.json",
    "failure-cases.json",
    "analysis-receipt.json",
    "input-manifest.json",
}


def _csv_text(rows: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_analysis_artifacts(
    bundle: Path,
    left: Path,
    right: Path,
    dual_verification: Path,
    aggregate: Path,
    analysis: Path,
    selection: Path,
    metrics: Path,
    design: Path,
    ingest: Path,
    config_path: Path,
    output: Path,
) -> dict:
    paths = [bundle, left, right, dual_verification, aggregate, analysis, selection,
             metrics, design, ingest, config_path, output]
    (bundle, left, right, dual_verification, aggregate, analysis, selection,
     metrics, design, ingest, config_path, output) = [Path(path).resolve() for path in paths]
    if os.path.lexists(output):
        raise FileExistsError("verification output already exists")
    cfg = load_analysis_config(config_path)

    _, expected_rows, _ = validate_formal_sources(
        bundle, left, right, dual_verification, selection, metrics, design, ingest, cfg
    )
    rows = load_aggregate(aggregate, cfg)
    if rows != expected_rows:
        raise ValueError("aggregate does not reproduce from frozen formal sources")
    inventory = verify_sums(analysis)
    if set(inventory) != ANALYSIS_FILES:
        raise ValueError("unexpected analysis inventory")

    agreement = agreement_statistics(rows)
    rates = rate_statistics(rows, cfg)
    bt = bradley_terry_statistics(rows, cfg)
    bootstrap_rows, bootstrap = cluster_bootstrap(
        rows, cfg.bootstrap.fields, FAMILIES, cfg.bootstrap.seed, cfg.bootstrap.iterations,
        cfg.bootstrap.expected_clusters, cfg.bootstrap.quantiles, cfg.bootstrap.quantile_method,
    )
    annotations = annotation_descriptives(rows)
    failure_cases = build_failure_cases(rows, cfg)
    summary = build_summary(
        rows, agreement, rates, bootstrap, bt, annotations, failure_cases["count"], cfg
    )
    if read_json(analysis / "summary.json") != summary:
        raise ValueError("analysis summary recomputation mismatch")
    if read_json(analysis / "confusion-matrices.json") != agreement:
        raise ValueError("agreement artifact mismatch")
    if read_json(analysis / "bt.json") != bt:
        raise ValueError("Bradley-Terry artifact mismatch")
    if read_json(analysis / "failure-cases.json") != failure_cases:
        raise ValueError("failure-case artifact mismatch")
    if _read_jsonl(analysis / "bootstrap.jsonl") != bootstrap_rows:
        raise ValueError("bootstrap draw artifact mismatch")
    if (analysis / "main-table.csv").read_text(encoding="utf-8") != _csv_text(build_main_rows(rates, bootstrap, cfg)):
        raise ValueError("main table mismatch")
    if (analysis / "agreement.csv").read_text(encoding="utf-8") != _csv_text(build_agreement_rows(agreement)):
        raise ValueError("agreement table mismatch")

    costs = read_json(analysis / "costs.json")
    elapsed = costs.get("entries", {}).get("d4_analysis_compute_elapsed", {}).get("value")
    if type(elapsed) not in (int, float):
        raise ValueError("D4 compute elapsed missing")
    expected_costs = cost_statistics(rows, selection, metrics, design, ingest, float(elapsed), aggregate)
    if costs != expected_costs:
        raise ValueError("cost/provenance artifact mismatch")

    expected_inputs = {
        "schema_version": "1", "protocol": cfg.protocol,
        "inputs": {
            "aggregate_inventory": {"sha256": sha256_file(aggregate / "SHA256SUMS")},
            "analysis_config": {"sha256": sha256_file(config_path)},
            "comparisons": {"sha256": sha256_file(selection / "comparisons.json")},
            "selection_lock": {"sha256": sha256_file(selection / "selection-lock.json")},
            "selection_inventory": {"sha256": sha256_file(selection / "SELECTION_SHA256SUMS")},
            "metrics": {"sha256": sha256_file(metrics / "metrics.jsonl")},
            "metrics_lock": {"sha256": sha256_file(metrics / "metrics-config-lock.json")},
            "metrics_inventory": {"sha256": sha256_file(metrics / "METRICS_SHA256SUMS")},
            "design": {"sha256": sha256_file(design / "design.json")},
            "design_lock": {"sha256": sha256_file(design / "design-lock.json")},
            "design_inventory": {"sha256": sha256_file(design / "DESIGN_SHA256SUMS")},
            "ingest": {"sha256": sha256_file(ingest)},
            "ingest_inventory": {"sha256": sha256_file(ingest.parent / "INGEST_SHA256SUMS")},
        },
    }
    if read_json(analysis / "input-manifest.json") != expected_inputs:
        raise ValueError("analysis input manifest mismatch")
    receipt = read_json(analysis / "analysis-receipt.json")
    expected_receipt = {
        "status": "passed", "protocol": cfg.protocol, "records": 42,
        "sample_clusters": 7, "bootstrap_iterations": 2000,
        "summary_canonical_sha256": canonical_sha256(summary),
    }
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise ValueError("analysis receipt mismatch")
    current_environment = source_evidence()
    recorded_environment = receipt.get("environment", {})
    for key in ("code_files", "dependencies", "python", "platform"):
        if recorded_environment.get(key) != current_environment[key]:
            raise ValueError(f"analysis source environment drift: {key}")

    for family in FAMILIES:
        for field in cfg.fields:
            metric = rates[cfg.primary_scope][family][field]
            if metric["wins"] + metric["losses"] + metric["ties"] + metric["uncertain"] != cfg.families[family].total:
                raise ValueError("formal rate count conservation failed")
            boot = bootstrap["metrics"][family][field]
            if boot["valid_replicates"] + boot["invalid_replicates"] != cfg.bootstrap.iterations:
                raise ValueError("bootstrap replicate conservation failed")
    if bt["diagnostics"]["edge_count"] != sum(
        record["aggregate"][cfg.bradley_terry.field] in ("X", "Y") for record in rows
    ):
        raise ValueError("Bradley-Terry edge count mismatch")

    verification = {
        "schema_version": "1", "status": "passed", "protocol": cfg.protocol,
        "aggregate_records": len(rows),
        "human_pairs": sum(record["source"] == "human_pair" for record in rows),
        "automatic_ties": sum(record["source"] == "automatic_tie" for record in rows),
        "families": {family: cfg.families[family].total for family in FAMILIES},
        "sample_clusters": bootstrap["cluster_count"],
        "agreement_n": agreement["n"],
        "bootstrap_iterations": cfg.bootstrap.iterations,
        "bt_status": bt["status"],
        "aggregate_inventory_sha256": sha256_file(aggregate / "SHA256SUMS"),
        "analysis_inventory_sha256": sha256_file(analysis / "SHA256SUMS"),
        "summary_sha256": sha256_file(analysis / "summary.json"),
    }
    temporary = output.with_name(f".{output.name}-{uuid.uuid4().hex}.staging")
    try:
        write_json(temporary, verification)
        rename_noreplace(temporary, output)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return verification
