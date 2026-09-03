"""Pinned compatibility handling for one audited server handoff artifact."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Union

from w1_pipeline.hashing import canonical_sha256

from .models import DefenseConfigV1


SERVER_AGENT_PROFILE_ID = "server-agent-20260902-v01"


@dataclass(frozen=True)
class CompatibilityProfile:
    profile_id: str
    archive_sha256: str
    manifest_sha256: str
    package_sums_sha256: str
    verification_declared_sha256: str
    verification_actual_sha256: str
    archive_members: int
    archive_expanded_bytes: int
    checksum_rows: int


SERVER_AGENT_20260902_V01 = CompatibilityProfile(
    profile_id=SERVER_AGENT_PROFILE_ID,
    archive_sha256="0aa0bd951f4609ef779013d78e424fa373201823a8e16e29cbdd070f3a66abdb",
    manifest_sha256="6c41bdd0f4d8c35445a2ce6fa26a7d9606226ea5aefb9c1888318ee5d4a4856e",
    package_sums_sha256="1ce2e1b87838092e0382489d6ac983c784f6f0fc088d3c29c642c69997e48be5",
    verification_declared_sha256="548fa36552d18a139490d3dee0fbf0304389e9e2684d790a12ed86f8dadbeff3",
    verification_actual_sha256="2c6477c7ae1f66f8af17f8cd81ad1dfc11b0e25d90d6a56bfed79cf1f18bafcc",
    archive_members=1265,
    archive_expanded_bytes=481708044,
    checksum_rows=1264,
)


CompatibilityInput = Optional[Union[str, CompatibilityProfile]]


def resolve_compatibility_profile(value: CompatibilityInput) -> Optional[CompatibilityProfile]:
    if value is None:
        return None
    if isinstance(value, CompatibilityProfile):
        return value
    if value != SERVER_AGENT_PROFILE_ID:
        raise ValueError(f"unknown compatibility profile: {value}")
    return SERVER_AGENT_20260902_V01


def _frame_set(items: Any, combined_sha256: str, label: str) -> Dict[str, Any]:
    if not isinstance(items, list) or len(items) != 16:
        raise ValueError(f"legacy {label} must contain exactly 16 frame records")
    if any(not isinstance(item, dict) or set(item) != {"relative_path", "sha256"} for item in items):
        raise ValueError(f"legacy {label} frame records have unexpected fields")
    return {
        "relative_paths": [item["relative_path"] for item in items],
        "sha256": [item["sha256"] for item in items],
        "combined_sha256": combined_sha256,
    }


def normalize_legacy_manifest(
    raw: Dict[str, Any], cfg: DefenseConfigV1
) -> tuple[Dict[str, Any], List[str]]:
    """Normalize only the exact wire-shape deviations of the pinned handoff."""
    payload = copy.deepcopy(raw)
    expected_top = {
        "schema_version", "package_id", "created_at", "created_by", "hostname", "status",
        "source", "counts", "samples", "candidates", "files", "warnings",
        "missing_optional_artifacts", "role_counts",
    }
    if set(payload) != expected_top:
        raise ValueError("legacy manifest top-level fields do not match the pinned profile")
    role_counts = payload.pop("role_counts")
    if not isinstance(role_counts, dict) or any(
        not isinstance(key, str) or not isinstance(value, int) or value < 0
        for key, value in role_counts.items()
    ):
        raise ValueError("legacy manifest role_counts is invalid")
    file_roles = Counter(item.get("role") for item in payload.get("files", []))
    if dict(sorted(file_roles.items())) != dict(sorted(role_counts.items())):
        raise ValueError("legacy manifest role_counts does not match file inventory")

    samples = payload.get("samples")
    candidates = payload.get("candidates")
    if not isinstance(samples, list) or not isinstance(candidates, list):
        raise ValueError("legacy manifest samples/candidates must be lists")
    sample_by_id = {item.get("sample_id"): item for item in samples if isinstance(item, dict)}
    if len(sample_by_id) != 10 or set(sample_by_id) != set(cfg.sample_ids):
        raise ValueError("legacy manifest sample identity is incomplete")
    candidate_by_pair = {
        (item.get("sample_id"), item.get("seed")): item
        for item in candidates if isinstance(item, dict)
    }
    expected_pairs = [(sample_id, seed) for sample_id in cfg.sample_ids for seed in cfg.seeds]
    if len(candidate_by_pair) != 50 or set(candidate_by_pair) != set(expected_pairs):
        raise ValueError("legacy manifest candidate matrix is incomplete")

    payload["samples"] = [sample_by_id[sample_id] for sample_id in cfg.sample_ids]
    payload["candidates"] = [candidate_by_pair[pair] for pair in expected_pairs]
    for sample in payload["samples"]:
        expected_sample_fields = {
            "sample_id", "sequence", "task_type", "instruction", "target_caption",
            "source_video", "source_frames", "source_combined_checksum", "masks",
            "mask_combined_checksum", "crop",
        }
        if set(sample) != expected_sample_fields:
            raise ValueError(f"legacy sample fields drifted: {sample.get('sample_id')}")
        sample["source_frames"] = _frame_set(
            sample["source_frames"], sample.pop("source_combined_checksum"),
            f"source {sample['sample_id']}",
        )
        sample["masks"] = _frame_set(
            sample["masks"], sample.pop("mask_combined_checksum"),
            f"mask {sample['sample_id']}",
        )

    for candidate in payload["candidates"]:
        expected_candidate_fields = {
            "candidate_id", "sample_id", "seed", "status", "video", "frames",
            "generation_key", "config", "runtime_seconds", "peak_vram_mb", "code_snapshot",
        }
        if set(candidate) != expected_candidate_fields:
            raise ValueError(f"legacy candidate fields drifted: {candidate.get('candidate_id')}")
        items = candidate["frames"]
        if not isinstance(items, list) or len(items) != 16:
            raise ValueError(f"legacy candidate frames are incomplete: {candidate['candidate_id']}")
        if any(not isinstance(item, dict) or set(item) != {"relative_path", "sha256"} for item in items):
            raise ValueError(f"legacy candidate frame fields drifted: {candidate['candidate_id']}")
        combined = canonical_sha256([
            {"name": PurePosixPath(item["relative_path"]).name, "sha256": item["sha256"]}
            for item in items
        ])
        candidate["frames"] = _frame_set(
            items, combined, f"candidate {candidate['candidate_id']}"
        )

    deviations = [
        "archive-layout:root-flat",
        "package-verification-checksum:known-control-file-drift",
        "package-verification-status:derived-from-15-passing-checks",
        "manifest-wire-shape:normalized-frame-sets-role-counts-and-7-plus-3-order",
    ]
    return payload, deviations


def validate_legacy_verification(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("legacy package verification must be an object")
    if "status" in payload:
        raise ValueError("pinned legacy verification unexpectedly contains status")
    if payload.get("package_id") != "DEFENSE-MVP-E0-HANDOFF-v01":
        raise ValueError("legacy verification package identity mismatch")
    if payload.get("ready_for_transfer") is not True or payload.get("failures") != []:
        raise ValueError("legacy verification is not ready or contains failures")
    checks = payload.get("checks")
    if not isinstance(checks, list) or len(checks) != 15:
        raise ValueError("legacy verification must contain exactly 15 checks")
    expected_ids = [f"v{index}" for index in range(1, 16)]
    if [item.get("id") for item in checks if isinstance(item, dict)] != expected_ids:
        raise ValueError("legacy verification check IDs drifted")
    if any(set(item) != {"id", "status", "summary"} or item.get("status") != "pass"
           for item in checks if isinstance(item, dict)):
        raise ValueError("legacy verification contains a non-passing or malformed check")
