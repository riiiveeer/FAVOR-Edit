"""D4 identity-gated two-annotator aggregation without result-dependent choices."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Iterable, Sequence

from w1_pipeline.hashing import canonical_sha256, sha256_file

from .analysis_models import (
    CATEGORIES,
    FAMILIES,
    FIELDS,
    AggregateRecord,
    AnalysisConfig,
    load_analysis_config,
)
from .annotation_bundle import (
    automatic_ties,
    load_bundle,
    now,
    read_json,
    source_evidence,
    stage,
    verify_sums,
    write_sums,
)
from .annotation_export import verify_annotations, verify_export
from .annotation_store import validate_record, validate_session
from .io import rename_noreplace, write_json


def aggregate_choice(left: str, right: str) -> str:
    """Frozen symmetric 4x4 conservative aggregation table."""
    if left not in CATEGORIES or right not in CATEGORIES:
        raise ValueError("invalid canonical choice")
    if "uncertain" in (left, right):
        return "uncertain"
    if left == right:
        return left
    if "tie" in (left, right):
        return "tie"
    return "uncertain"


def _records_by_id(records: Sequence[object]) -> Dict[str, object]:
    result = {record.comparison_id: record for record in records}
    if len(result) != len(records):
        raise ValueError("duplicate manual comparison ID")
    return result


def _side(comparison: dict, name: str) -> dict:
    raw = comparison[f"candidate_{name.lower()}"]
    return {
        "role": raw["role"],
        "candidate_id": raw["candidate_id"],
        "video_sha256": raw["video"]["sha256"],
    }


def _proposed_side(comparison: dict, cfg: AnalysisConfig) -> str:
    family = cfg.families[comparison["family"]]
    roles = {"X": comparison["candidate_x"]["role"], "Y": comparison["candidate_y"]["role"]}
    proposed = [side for side, role in roles.items() if role == family.proposed_role]
    comparator = [side for side, role in roles.items() if role == family.comparator_role]
    if len(proposed) != 1 or len(comparator) != 1 or proposed[0] == comparator[0]:
        raise ValueError(f"comparison role identity invalid: {comparison['comparison_id']}")
    if set(roles.values()) != {family.proposed_role, family.comparator_role}:
        raise ValueError(f"unexpected comparison role: {comparison['comparison_id']}")
    return proposed[0]


def aggregate_verified_records(
    comparisons: Sequence[dict],
    records_a: Sequence[object],
    records_b: Sequence[object],
    automatic: Sequence[dict],
    cfg: AnalysisConfig,
) -> list[dict]:
    """Aggregate already validated records; this pure boundary is used by fixtures."""
    by_comparison = {item["comparison_id"]: item for item in comparisons}
    if len(by_comparison) != len(comparisons) or len(comparisons) != cfg.aggregation.total_comparisons:
        raise ValueError("comparison identity/cardinality mismatch")
    left, right = _records_by_id(records_a), _records_by_id(records_b)
    if set(left) != set(right):
        raise ValueError("annotators must cover the same manual comparison IDs")
    auto = {item["comparison_id"]: item for item in automatic}
    if len(auto) != len(automatic) or set(auto) & set(left):
        raise ValueError("manual and automatic comparison sets overlap")
    if set(left) | set(auto) != set(by_comparison):
        raise ValueError("manual/automatic comparison partition mismatch")
    if len(left) != cfg.aggregation.manual_comparisons or len(auto) != cfg.aggregation.automatic_comparisons:
        raise ValueError("manual/automatic cardinality mismatch")

    rows = []
    for comparison_id in sorted(by_comparison):
        comparison = by_comparison[comparison_id]
        common = {
            "schema_version": "1",
            "protocol": cfg.protocol,
            "comparison_id": comparison_id,
            "family": comparison["family"],
            "trial_id": comparison["trial_id"],
            "sample_id": comparison["sample_id"],
            "replicate": comparison["replicate"],
            "candidate_x": _side(comparison, "X"),
            "candidate_y": _side(comparison, "Y"),
            "proposed_side": _proposed_side(comparison, cfg),
        }
        if comparison_id in auto:
            item = auto[comparison_id]
            if (
                not comparison.get("identical_selection")
                or item.get("source") != "automatic_tie"
                or item.get("reason") != "media_identity"
                or item.get("outcome") != "tie"
                or item.get("media_sha256") != comparison["candidate_x"]["video"]["sha256"]
                or comparison["candidate_x"]["video"]["sha256"]
                != comparison["candidate_y"]["video"]["sha256"]
            ):
                raise ValueError(f"automatic tie identity invalid: {comparison_id}")
            row = {
                **common,
                "source": "automatic_tie",
                "reason": "media_identity",
                "aggregate": {field: "tie" for field in FIELDS},
                "human": None,
            }
        else:
            if comparison.get("identical_selection"):
                raise ValueError(f"identical media was presented to humans: {comparison_id}")
            a, b = left[comparison_id], right[comparison_id]
            if a.annotator_id != "annotator-a" or b.annotator_id != "annotator-b":
                raise ValueError("annotator identity/order mismatch")
            canonical_a = {field: a.canonical[field] for field in FIELDS}
            canonical_b = {field: b.canonical[field] for field in FIELDS}
            row = {
                **common,
                "source": "human_pair",
                "reason": None,
                "aggregate": {
                    field: aggregate_choice(canonical_a[field], canonical_b[field])
                    for field in FIELDS
                },
                "human": {
                    "annotator-a": {
                        "canonical": canonical_a,
                        "confidence": a.screen.confidence,
                        "current_view_elapsed_seconds": a.current_view_elapsed_seconds,
                    },
                    "annotator-b": {
                        "canonical": canonical_b,
                        "confidence": b.screen.confidence,
                        "current_view_elapsed_seconds": b.current_view_elapsed_seconds,
                    },
                },
            }
        rows.append(AggregateRecord.model_validate(row).model_dump(mode="json"))

    family_counts = {family: sum(row["family"] == family for row in rows) for family in FAMILIES}
    auto_counts = {
        family: sum(row["family"] == family and row["source"] == "automatic_tie" for row in rows)
        for family in FAMILIES
    }
    for family in FAMILIES:
        expected = cfg.families[family]
        if family_counts[family] != expected.total or auto_counts[family] != expected.automatic_ties:
            raise ValueError(f"family cardinality drifted: {family}")
    if len({row["sample_id"] for row in rows}) != cfg.bootstrap.expected_clusters:
        raise ValueError("sample cluster cardinality drifted")
    return rows


def _read_export_records(bundle: dict, directory: Path) -> tuple[object, list[object]]:
    verify_export(bundle, directory)
    session = validate_session(bundle, read_json(Path(directory) / "session.json"))
    lines = (Path(directory) / "answers.jsonl").read_text(encoding="utf-8").splitlines()
    return session, [validate_record(bundle, session, json.loads(line)) for line in lines]


def _logical_inputs(
    bundle_path: Path,
    left: Path,
    right: Path,
    dual_verification: Path,
    selection: Path,
    metrics: Path,
    design: Path,
    ingest: Path,
    config_path: Path,
) -> dict[str, dict[str, str]]:
    paths = {
        "bundle": bundle_path / "bundle.json",
        "annotator_a_inventory": left / "SHA256SUMS",
        "annotator_b_inventory": right / "SHA256SUMS",
        "dual_verification": dual_verification,
        "analysis_config": config_path,
        "pilot": Path("configs/defense_mvp/pilot.yaml").resolve(),
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
    return {name: {"sha256": sha256_file(path)} for name, path in paths.items()}


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_aggregate(directory: Path, cfg: AnalysisConfig) -> list[dict]:
    directory = Path(directory)
    inventory = verify_sums(directory)
    expected = {"aggregate.jsonl", "agreement-input.json", "aggregation-receipt.json", "input-manifest.json"}
    if set(inventory) != expected:
        raise ValueError("unexpected aggregate inventory")
    rows = [
        AggregateRecord.model_validate(json.loads(line)).model_dump(mode="json")
        for line in (directory / "aggregate.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if [row["comparison_id"] for row in rows] != sorted({row["comparison_id"] for row in rows}):
        raise ValueError("aggregate rows must be unique and sorted")
    if len(rows) != cfg.aggregation.total_comparisons:
        raise ValueError("aggregate cardinality mismatch")
    manual = [row for row in rows if row["source"] == "human_pair"]
    automatic = [row for row in rows if row["source"] == "automatic_tie"]
    if len(manual) != cfg.aggregation.manual_comparisons or len(automatic) != cfg.aggregation.automatic_comparisons:
        raise ValueError("aggregate source cardinality mismatch")
    expected_agreement = {
        "schema_version": "1",
        "protocol": cfg.protocol,
        "scope": "manual-only",
        "records": [
            {
                "comparison_id": row["comparison_id"],
                "family": row["family"],
                "sample_id": row["sample_id"],
                "annotator-a": row["human"]["annotator-a"]["canonical"],
                "annotator-b": row["human"]["annotator-b"]["canonical"],
            }
            for row in manual
        ],
    }
    if read_json(directory / "agreement-input.json") != expected_agreement:
        raise ValueError("agreement input does not match aggregate facts")
    receipt = read_json(directory / "aggregation-receipt.json")
    expected_receipt = {
        "status": "passed",
        "protocol": cfg.protocol,
        "aggregate_records": len(rows),
        "human_pairs": len(manual),
        "automatic_ties": len(automatic),
        "aggregate_canonical_sha256": canonical_sha256(rows),
    }
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise ValueError("aggregation receipt mismatch")
    current_environment = source_evidence()
    recorded_environment = receipt.get("environment", {})
    for key in ("code_files", "dependencies", "python", "platform"):
        if recorded_environment.get(key) != current_environment[key]:
            raise ValueError(f"aggregate source environment drift: {key}")
    return rows


def _preserve_failed(staging: Path, output: Path, exc: Exception) -> None:
    if not staging.exists():
        return
    try:
        write_json(staging / "AGGREGATION_FAILED.json", {"status": "failed", "error": str(exc), "at": now()})
    finally:
        failed = output.with_name(f".{output.name}-{uuid.uuid4().hex}.failed")
        rename_noreplace(staging, failed)


def validate_formal_sources(
    bundle_path: Path,
    left: Path,
    right: Path,
    dual_verification: Path,
    selection: Path,
    metrics: Path,
    design: Path,
    ingest: Path,
    cfg: AnalysisConfig,
) -> tuple[dict, list[dict], dict]:
    """Validate every formal source and reconstruct the expected aggregate in memory."""
    pinned = {
        "bundle": bundle_path / "bundle.json",
        "annotator_a_inventory": left / "SHA256SUMS",
        "annotator_b_inventory": right / "SHA256SUMS",
        "dual_verification": dual_verification,
        "pilot": Path("configs/defense_mvp/pilot.yaml").resolve(),
        "comparisons": selection / "comparisons.json",
        "selection_lock": selection / "selection-lock.json",
    }
    for name, path in pinned.items():
        if sha256_file(path) != cfg.input_pins[name]:
            raise ValueError(f"frozen formal input drift: {name}")

    bundle = load_bundle(bundle_path)
    if bundle["mode"] != "formal":
        raise ValueError("D4 accepts formal annotation bundles only")
    expected_locations = {
        "selection": selection,
        "metrics": metrics,
        "design": design,
        "ingest": ingest,
        "pilot": Path("configs/defense_mvp/pilot.yaml").resolve(),
    }
    for name, path in expected_locations.items():
        if Path(bundle["input_locations"][name]).resolve() != path:
            raise ValueError(f"bundle input location mismatch: {name}")
    verify_sums(selection, "SELECTION_SHA256SUMS")
    verify_sums(metrics, "METRICS_SHA256SUMS")
    verify_sums(design, "DESIGN_SHA256SUMS")
    verify_sums(ingest.parent, "INGEST_SHA256SUMS")

    dual = verify_annotations(bundle_path, [left, right])
    if dual != read_json(dual_verification):
        raise ValueError("dual verification receipt does not match current verification")
    required = {
        "status": "complete",
        "mode": "formal",
        "scope": "dual",
        "exported_answers": 64,
        "manual_per_annotator": 32,
        "automatic_ties_shared": 10,
    }
    if any(dual.get(key) != value for key, value in required.items()):
        raise ValueError("formal dual completeness gate failed")

    session_a, records_a = _read_export_records(bundle, left)
    session_b, records_b = _read_export_records(bundle, right)
    if session_a.annotator_id != "annotator-a" or session_b.annotator_id != "annotator-b":
        raise ValueError("left/right export identities must be annotator-a/annotator-b")
    rows = aggregate_verified_records(
        bundle["comparisons"], records_a, records_b, automatic_ties(bundle["comparisons"]), cfg
    )
    return bundle, rows, dual


def aggregate_annotations(
    bundle_path: Path,
    left: Path,
    right: Path,
    dual_verification: Path,
    selection: Path,
    metrics: Path,
    design: Path,
    ingest: Path,
    config_path: Path,
    output: Path,
) -> dict:
    """Verify the unique formal inputs and publish one no-replace aggregate."""
    paths = [bundle_path, left, right, dual_verification, selection, metrics, design, ingest, config_path, output]
    (bundle_path, left, right, dual_verification, selection, metrics, design, ingest, config_path, output) = [
        Path(path).resolve() for path in paths
    ]
    cfg = load_analysis_config(config_path)
    staging = stage(output)
    try:
        _, rows, _ = validate_formal_sources(
            bundle_path, left, right, dual_verification, selection, metrics, design, ingest, cfg
        )
        inputs = _logical_inputs(
            bundle_path, left, right, dual_verification, selection, metrics, design, ingest, config_path
        )
        write_json(staging / "input-manifest.json", {
            "schema_version": "1",
            "protocol": cfg.protocol,
            "inputs": inputs,
        })
        _write_jsonl(staging / "aggregate.jsonl", rows)
        manual = [
            {
                "comparison_id": row["comparison_id"],
                "family": row["family"],
                "sample_id": row["sample_id"],
                "annotator-a": row["human"]["annotator-a"]["canonical"],
                "annotator-b": row["human"]["annotator-b"]["canonical"],
            }
            for row in rows if row["source"] == "human_pair"
        ]
        write_json(staging / "agreement-input.json", {
            "schema_version": "1",
            "protocol": cfg.protocol,
            "scope": "manual-only",
            "records": manual,
        })
        stable_sha = canonical_sha256(rows)
        receipt = {
            "schema_version": "1",
            "status": "passed",
            "protocol": cfg.protocol,
            "created_at": now(),
            "aggregate_records": len(rows),
            "human_pairs": sum(row["source"] == "human_pair" for row in rows),
            "automatic_ties": sum(row["source"] == "automatic_tie" for row in rows),
            "aggregate_canonical_sha256": stable_sha,
            "source_locations": {
                "bundle": str(bundle_path),
                "annotator-a": str(left),
                "annotator-b": str(right),
                "dual_verification": str(dual_verification),
            },
            "environment": source_evidence(),
        }
        write_json(staging / "aggregation-receipt.json", receipt)
        write_sums(staging)
        rename_noreplace(staging, output)
        return receipt
    except Exception as exc:
        _preserve_failed(staging, output, exc)
        raise
