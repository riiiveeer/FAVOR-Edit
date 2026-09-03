"""Read-only verification and normalized ingest of an extracted E0 handoff package."""

from __future__ import annotations

import csv
import json
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from w1_pipeline.hashing import canonical_sha256, combined_file_sha256, sha256_file

from .compat import (
    CompatibilityInput, normalize_legacy_manifest, resolve_compatibility_profile,
    validate_legacy_verification,
)
from .config import load_config
from .io import rename_noreplace, write_json
from .models import (
    DefenseConfigV1, FrameSetV1, PackageManifestV1, validate_relative_path,
)


SUMS_NAME = "PACKAGE_SHA256SUMS"
MANIFEST_NAME = "PACKAGE_MANIFEST.json"
VERIFICATION_NAME = "PACKAGE_VERIFICATION.json"
SUM_LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def _regular_files(root: Path) -> List[Path]:
    paths: List[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"delivery package must not contain symlinks: {path}")
        if path.is_file():
            paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _package_file(root: Path, relative_path: str) -> Path:
    relative_path = validate_relative_path(relative_path)
    root_resolved = root.resolve()
    path = root / Path(*relative_path.split("/"))
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"package file is missing or not regular: {relative_path}")
    try:
        path.resolve().relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"package path escapes delivery root: {relative_path}") from exc
    return path


def verify_package_sums(
    root: Path, compatibility_profile: CompatibilityInput = None
) -> Tuple[int, List[dict]]:
    profile = resolve_compatibility_profile(compatibility_profile)
    sums = root / SUMS_NAME
    if not sums.is_file() or sums.is_symlink():
        raise ValueError(f"missing regular {SUMS_NAME}")
    rows: List[Tuple[str, str]] = []
    for line_number, line in enumerate(sums.read_text(encoding="utf-8").splitlines(), start=1):
        match = SUM_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid {SUMS_NAME} line {line_number}")
        digest, relative = match.groups()
        rows.append((validate_relative_path(relative), digest))
    paths = [relative for relative, _ in rows]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError(f"{SUMS_NAME} paths must be sorted and unique")
    expected = [
        path.relative_to(root).as_posix() for path in _regular_files(root)
        if path != sums
    ]
    if paths != expected:
        missing = sorted(set(expected) - set(paths))
        extra = sorted(set(paths) - set(expected))
        raise ValueError(f"{SUMS_NAME} tree mismatch; missing={missing}; extra={extra}")
    mismatches = []
    for relative, digest in rows:
        actual = sha256_file(_package_file(root, relative))
        if actual != digest:
            mismatches.append({
                "relative_path": relative, "declared_sha256": digest,
                "actual_sha256": actual,
            })
    if mismatches:
        allowed = [] if profile is None else [{
            "relative_path": VERIFICATION_NAME,
            "declared_sha256": profile.verification_declared_sha256,
            "actual_sha256": profile.verification_actual_sha256,
        }]
        if mismatches != allowed:
            raise ValueError(f"package checksum mismatch: {mismatches[0]['relative_path']}")
    if profile is not None and len(rows) != profile.checksum_rows:
        raise ValueError("compatibility package checksum row count drifted")
    return len(rows), mismatches


def _verify_frame_set(root: Path, frames: FrameSetV1, label: str) -> None:
    paths = [_package_file(root, value) for value in frames.relative_paths]
    actual = [sha256_file(path) for path in paths]
    if actual != frames.sha256:
        raise ValueError(f"{label} frame checksum mismatch")
    if combined_file_sha256(paths) != frames.combined_sha256:
        raise ValueError(f"{label} combined checksum mismatch")


def _verify_manifest_files(root: Path, manifest: PackageManifestV1) -> None:
    for item in manifest.files:
        path = _package_file(root, item.relative_path)
        if path.stat().st_size != item.size_bytes:
            raise ValueError(f"package file size mismatch: {item.relative_path}")
        if sha256_file(path) != item.sha256:
            raise ValueError(f"package manifest checksum mismatch: {item.relative_path}")


def _load_json(root: Path, relative: str):
    return json.loads(_package_file(root, relative).read_text(encoding="utf-8"))


def _verify_original_records(root: Path, manifest: PackageManifestV1) -> None:
    plan_path = _package_file(root, "metadata/original-plan.json")
    candidates_path = _package_file(root, "metadata/original-candidates.json")
    if sha256_file(plan_path) != manifest.source.plan_sha256:
        raise ValueError("original plan checksum does not match source identity")
    if sha256_file(candidates_path) != manifest.source.candidates_sha256:
        raise ValueError("original candidates checksum does not match source identity")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    plan_tasks = plan.get("candidates") or []
    if len(plan.get("inversions") or []) != 10 or len(plan_tasks) != 50:
        raise ValueError("original plan must contain 10 inversions and 50 candidates")
    if not isinstance(candidates, list) or len(candidates) != 50:
        raise ValueError("original candidates must contain 50 records")
    package_by_id = {item.candidate_id: item for item in manifest.candidates}
    if len(package_by_id) != 50:
        raise ValueError("package candidate IDs are not unique")
    if {item.get("candidate_id") for item in plan_tasks} != set(package_by_id):
        raise ValueError("original plan candidate IDs do not match package manifest")
    if {item.get("candidate_id") for item in candidates} != set(package_by_id):
        raise ValueError("original candidate IDs do not match package manifest")
    for record in candidates:
        item = package_by_id[record["candidate_id"]]
        if record.get("status") != "succeeded":
            raise ValueError(f"original candidate is not succeeded: {item.candidate_id}")
        if record.get("sample_id") != item.sample_id:
            raise ValueError(f"candidate sample mismatch: {item.candidate_id}")
        if int(record.get("config", {}).get("seed", -1)) != item.seed:
            raise ValueError(f"candidate seed mismatch: {item.candidate_id}")
        if record.get("video_checksum") != item.video.sha256:
            raise ValueError(f"candidate video identity mismatch: {item.candidate_id}")
        if list(record.get("frame_checksums") or []) != item.frames.sha256:
            raise ValueError(f"candidate frame identity mismatch: {item.candidate_id}")
        if record.get("generation_key") != item.generation_key:
            raise ValueError(f"candidate generation identity mismatch: {item.candidate_id}")
        if record.get("code_snapshot") != item.code_snapshot:
            raise ValueError(f"candidate code snapshot mismatch: {item.candidate_id}")
        if record.get("config") != item.config.model_dump(mode="json"):
            raise ValueError(f"candidate generation config mismatch: {item.candidate_id}")

    if sorted(set(item.code_snapshot for item in manifest.candidates)) != sorted(manifest.source.e0_code_snapshots):
        raise ValueError("candidate code snapshots do not match source identity")
    if sorted(set(item.config.model_commit for item in manifest.candidates)) != sorted(manifest.source.model_commits):
        raise ValueError("candidate model commits do not match source identity")
    if sorted(set(item.config.anyv2v_commit for item in manifest.candidates)) != sorted(manifest.source.anyv2v_commits):
        raise ValueError("candidate AnyV2V commits do not match source identity")

    sample_by_id = {item.sample_id: item for item in manifest.samples}
    canonical_inputs: Dict[str, str] = {}
    for task in plan_tasks:
        sample_id = task.get("sample_id")
        payload = task.get("input") or {}
        candidate = package_by_id.get(task.get("candidate_id"))
        if candidate is None or candidate.sample_id != sample_id:
            raise ValueError(f"plan candidate/sample mismatch: {task.get('candidate_id')}")
        if int((task.get("config") or {}).get("seed", -1)) != candidate.seed:
            raise ValueError(f"plan candidate seed mismatch: {candidate.candidate_id}")
        if task.get("config") != candidate.config.model_dump(mode="json"):
            raise ValueError(f"plan generation config mismatch: {candidate.candidate_id}")
        identity = canonical_sha256(payload)
        if sample_id in canonical_inputs and canonical_inputs[sample_id] != identity:
            raise ValueError(f"plan input identity drifts within sample: {sample_id}")
        canonical_inputs[sample_id] = identity
        sample = sample_by_id.get(sample_id)
        if sample is None:
            raise ValueError(f"plan references unknown sample: {sample_id}")
        expected_metadata = {
            "sequence": sample.sequence, "task_type": sample.task_type,
            "instruction": sample.instruction, "target_caption": sample.target_caption,
        }
        if any(payload.get(key) != value for key, value in expected_metadata.items()):
            raise ValueError(f"sample metadata mismatch: {sample_id}")
        if payload.get("crop") != sample.crop.model_dump(mode="json"):
            raise ValueError(f"sample crop mismatch: {sample_id}")
        if payload.get("video_checksum") != sample.source_video.sha256:
            raise ValueError(f"source video identity mismatch: {sample_id}")
        if payload.get("source_checksum") != sample.source_frames.combined_sha256:
            raise ValueError(f"source frame identity mismatch: {sample_id}")
        if payload.get("mask_checksum") != sample.masks.combined_sha256:
            raise ValueError(f"mask identity mismatch: {sample_id}")

    audit_path = _package_file(root, "metadata/e0-audit/audit-manifest.json")
    if sha256_file(audit_path) != manifest.source.audit_manifest_sha256:
        raise ValueError("audit manifest checksum does not match source identity")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if set(audit.get("candidate_ids") or []) != set(package_by_id):
        raise ValueError("audit manifest candidate IDs do not match package")
    with _package_file(root, "metadata/e0-audit/audit.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 50 or {row.get("candidate_id") for row in rows} != set(package_by_id):
        raise ValueError("audit.csv must cover exactly the 50 package candidates")


def verify_delivery(
    delivery: Path, config_path: Path, compatibility_profile: CompatibilityInput = None
) -> Tuple[PackageManifestV1, dict]:
    root = Path(delivery)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("delivery must be an extracted regular directory")
    profile = resolve_compatibility_profile(compatibility_profile)
    manifest_path = _package_file(root, MANIFEST_NAME)
    verification_path = _package_file(root, VERIFICATION_NAME)
    sums_path = _package_file(root, SUMS_NAME)
    if profile is not None:
        pinned = {
            MANIFEST_NAME: (sha256_file(manifest_path), profile.manifest_sha256),
            SUMS_NAME: (sha256_file(sums_path), profile.package_sums_sha256),
            VERIFICATION_NAME: (
                sha256_file(verification_path), profile.verification_actual_sha256,
            ),
        }
        drifted = [name for name, (actual, expected) in pinned.items() if actual != expected]
        if drifted:
            raise ValueError(f"compatibility control fingerprint drifted: {drifted[0]}")
    checksum_rows, sum_mismatches = verify_package_sums(root, profile)
    cfg: DefenseConfigV1 = load_config(config_path)
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    compatibility_deviations: List[str] = []
    if profile is not None:
        normalized_manifest, compatibility_deviations = normalize_legacy_manifest(
            raw_manifest, cfg
        )
        manifest = PackageManifestV1.model_validate(normalized_manifest)
    else:
        manifest = PackageManifestV1.model_validate(raw_manifest)
    if [item.sample_id for item in manifest.samples] != cfg.sample_ids:
        raise ValueError("package sample identity does not match Defense config")
    _verify_manifest_files(root, manifest)
    referenced = set()
    for sample in manifest.samples:
        if sha256_file(_package_file(root, sample.source_video.relative_path)) != sample.source_video.sha256:
            raise ValueError(f"source video checksum mismatch: {sample.sample_id}")
        _verify_frame_set(root, sample.source_frames, f"source {sample.sample_id}")
        _verify_frame_set(root, sample.masks, f"mask {sample.sample_id}")
        referenced.add(sample.source_video.relative_path)
        referenced.update(sample.source_frames.relative_paths)
        referenced.update(sample.masks.relative_paths)
    for candidate in manifest.candidates:
        if sha256_file(_package_file(root, candidate.video.relative_path)) != candidate.video.sha256:
            raise ValueError(f"candidate video checksum mismatch: {candidate.candidate_id}")
        _verify_frame_set(root, candidate.frames, f"candidate {candidate.candidate_id}")
        referenced.add(candidate.video.relative_path)
        referenced.update(candidate.frames.relative_paths)
    if len(referenced) != 1180:
        raise ValueError(f"media references must cover 1180 unique files, got {len(referenced)}")
    manifest_files = {item.relative_path for item in manifest.files}
    if not referenced.issubset(manifest_files):
        raise ValueError("one or more media references are absent from package file inventory")
    _verify_original_records(root, manifest)
    verification = _load_json(root, VERIFICATION_NAME)
    if profile is not None:
        validate_legacy_verification(verification)
    elif verification.get("status") != "passed" or verification.get("ready_for_transfer") is not True:
        raise ValueError("server package verification is not passed/ready_for_transfer")
    report = {
        "status": "passed",
        "ready_for_ingest": True,
        "package_id": manifest.package_id,
        "package_manifest_sha256": sha256_file(manifest_path),
        "package_sums_sha256": sha256_file(root / SUMS_NAME),
        "checksum_rows": checksum_rows,
        "counts": manifest.counts.model_dump(mode="json"),
        "warnings": manifest.warnings,
        "missing_optional_artifacts": manifest.missing_optional_artifacts,
    }
    if profile is not None:
        report["compatibility"] = {
            "profile_id": profile.profile_id,
            "deviations": compatibility_deviations,
            "raw_manifest_sha256": sha256_file(manifest_path),
            "raw_package_sums_sha256": sha256_file(sums_path),
            "raw_verification_sha256": sha256_file(verification_path),
            "package_sum_mismatches": sum_mismatches,
            "normalized_manifest_sha256": canonical_sha256(
                manifest.model_dump(mode="json")
            ),
        }
    return manifest, report


def _write_ingest_sums(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    rows = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in files]
    (root / "INGEST_SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def ingest_delivery(
    delivery: Path, config_path: Path, output: Path,
    compatibility_profile: CompatibilityInput = None,
) -> dict:
    delivery, output = Path(delivery).resolve(), Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(f"ingest output already exists: {output}")
    source_before = {
        MANIFEST_NAME: sha256_file(delivery / MANIFEST_NAME),
        SUMS_NAME: sha256_file(delivery / SUMS_NAME),
        VERIFICATION_NAME: sha256_file(delivery / VERIFICATION_NAME),
    }
    manifest, report = verify_delivery(delivery, config_path, compatibility_profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / f".{output.name}.ingest-{uuid.uuid4().hex}.staging"
    if os.path.lexists(staging):
        raise FileExistsError(f"ingest staging already exists: {staging}")
    staging.mkdir()
    normalized = {
        "schema_version": "1",
        "experiment_id": "DEFENSE-MVP-v01",
        "package_id": manifest.package_id,
        "delivery_root": str(delivery),
        "package_manifest_sha256": report["package_manifest_sha256"],
        "package_sums_sha256": report["package_sums_sha256"],
        "primary_sample_ids": load_config(config_path).primary_sample_ids,
        "qualitative_sample_ids": load_config(config_path).qualitative_sample_ids,
        "samples": [item.model_dump(mode="json") for item in manifest.samples],
        "candidates": [item.model_dump(mode="json") for item in manifest.candidates],
    }
    if "compatibility" in report:
        normalized["compatibility"] = report["compatibility"]
    write_json(staging / "normalized-manifest.json", normalized)
    receipt = {
        "schema_version": "1",
        "status": "passed",
        "ready_for_scoring": True,
        "package_id": manifest.package_id,
        "delivery_root": str(delivery),
        "package_manifest_sha256": report["package_manifest_sha256"],
        "package_sums_sha256": report["package_sums_sha256"],
        "counts": report["counts"],
        "warnings": report["warnings"],
        "missing_optional_artifacts": report["missing_optional_artifacts"],
        "external_inputs_unchanged": True,
    }
    if "compatibility" in report:
        receipt["compatibility_profile"] = report["compatibility"]["profile_id"]
        receipt["compatibility_warnings"] = report["compatibility"]["deviations"]
        write_json(staging / "compatibility-receipt.json", {
            "schema_version": "1",
            "status": "accepted-with-pinned-compatibility",
            "package_id": manifest.package_id,
            "external_inputs_unchanged": True,
            **report["compatibility"],
        })
    write_json(staging / "ingest-receipt.json", receipt)
    _write_ingest_sums(staging)
    source_after = {
        MANIFEST_NAME: sha256_file(delivery / MANIFEST_NAME),
        SUMS_NAME: sha256_file(delivery / SUMS_NAME),
        VERIFICATION_NAME: sha256_file(delivery / VERIFICATION_NAME),
    }
    if source_after != source_before:
        raise RuntimeError("delivery identity changed during read-only ingest")
    rename_noreplace(staging, output)
    return receipt
