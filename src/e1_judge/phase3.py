"""Atomic orchestration for the complete E1 phase-3 preparation bundle."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from w1_pipeline.hashing import sha256_file

from .hashing import canonical_sha256
from .models import MediaManifestV2, RuntimeConfigV2
from .packets import build_packets
from .pairs import build_pairs
from .preparation import (
    EXPECTED_ADAPTER_PYTHON,
    EXPECTED_ADAPTER_SCRIPT,
    EXPECTED_MODEL_NAME,
    EXPECTED_MODEL_PATH,
    EXPECTED_MODEL_REVISION,
    PreparationPathMapping,
    verify_preparation,
)
from .prompts import load_prompt
from .runner import build_judge_plan, code_snapshot

PREPARE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
RUNTIME_MANIFEST_PLACEHOLDER = "REQUIRED_64_HEX_SHA256_OF_SHA256SUMS"
PREPARATION_REPORT_NAME = "preparation-verification-v01.json"
PREPARATION_RECEIPT_NAME = "phase3-preparation-v01.json"
PREPARATION_CHECKSUMS_NAME = "PREPARATION_SHA256SUMS"
FAILURE_MARKER_NAME = "PREPARATION_FAILED.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _atomic_new_bytes(path: Path, payload: bytes) -> None:
    """Publish a new file atomically without replacing an existing path."""
    path = Path(path)
    if _lexists(path):
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise FileExistsError(f"output already exists: {path}") from exc
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_replace_bytes(path: Path, payload: bytes) -> None:
    """Atomically replace an internal staging file."""
    path = Path(path)
    temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _json_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_new_json(path: Path, payload: dict) -> None:
    _atomic_new_bytes(path, _json_bytes(payload))


def _atomic_replace_json(path: Path, payload: dict) -> None:
    _atomic_replace_bytes(path, _json_bytes(payload))


def _rename_noreplace(source: Path, target: Path) -> None:
    """Atomically rename a directory while refusing every existing target."""
    source = Path(source)
    target = Path(target)
    if not _lexists(source):
        raise FileNotFoundError(source)
    if _lexists(target):
        raise FileExistsError(f"publish target already exists: {target}")
    if sys.platform == "win32":
        os.rename(source, target)
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(errno.ENOSYS, "renameat2(RENAME_NOREPLACE) is unavailable")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(source),
            -100,
            os.fsencode(target),
            1,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number == errno.EEXIST:
                raise FileExistsError(f"publish target already exists: {target}")
            raise OSError(error_number, os.strerror(error_number), str(target))
        return
    raise OSError(
        errno.ENOSYS,
        f"atomic no-replace directory publish is unsupported on {sys.platform}",
    )


class Phase3PreparationError(RuntimeError):
    """Failure with an explicit preserved artifact or staging location."""

    def __init__(
        self,
        stage: str,
        error: Exception | str,
        *,
        failure_root: Optional[Path] = None,
        staging_root: Optional[Path] = None,
        published_root: Optional[Path] = None,
    ) -> None:
        self.stage = stage
        self.failure_root = failure_root
        self.staging_root = staging_root
        self.published_root = published_root
        location = failure_root or staging_root or published_root
        suffix = f"; preserved at {location}" if location else ""
        super().__init__(f"phase-3 preparation failed at {stage}: {error}{suffix}")


def _project_root(config: Path) -> Path:
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=config.parent,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"cannot resolve project Git root from {config}: {exc}") from exc
    return Path(output).resolve()


def _file_identity(path: Path) -> dict:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return {"path": str(path), "sha256": sha256_file(path)}


def _external_input_inventory(
    e0_plan: Path,
    e0_candidates: Path,
    e0_audit: Path,
) -> dict:
    plan_payload = json.loads(Path(e0_plan).read_text(encoding="utf-8"))
    candidate_payload = json.loads(Path(e0_candidates).read_text(encoding="utf-8"))
    if not isinstance(candidate_payload, list):
        raise ValueError("E0 candidates must be a JSON list")
    paths = {Path(e0_plan), Path(e0_candidates), Path(e0_audit)}
    for task in plan_payload.get("candidates") or []:
        input_record = task.get("input") or {}
        paths.add(Path(input_record["source_video_path"]))
        paths.update(Path(item) for item in input_record.get("mask_frame_paths", []))
    for candidate in candidate_payload:
        paths.add(Path(candidate["video_path"]))
    files = [_file_identity(path) for path in sorted(paths, key=lambda item: str(item))]
    return {
        "files": files,
        "file_count": len(files),
        "inventory_sha256": canonical_sha256(files),
    }


def _materialize_runtime(
    template: Path,
    model_manifest: Path,
    output: Path,
) -> RuntimeConfigV2:
    payload = yaml.safe_load(Path(template).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime template must be a YAML mapping")
    try:
        manifest_value = payload["model"]["manifest_sha256"]
    except (KeyError, TypeError) as exc:
        raise ValueError("runtime template is missing model.manifest_sha256") from exc
    if manifest_value != RUNTIME_MANIFEST_PLACEHOLDER:
        raise ValueError(
            "runtime template model.manifest_sha256 must be the audited REQUIRED placeholder"
        )
    model_manifest_identity = _file_identity(model_manifest)
    payload["model"]["manifest_sha256"] = model_manifest_identity["sha256"]
    runtime = RuntimeConfigV2.model_validate(payload)
    fixed_fields = {
        "backend": (runtime.backend, "command"),
        "model.name": (runtime.model.name, EXPECTED_MODEL_NAME),
        "model.revision": (runtime.model.revision, EXPECTED_MODEL_REVISION),
        "model.local_path": (runtime.model.local_path, EXPECTED_MODEL_PATH),
        "adapter.python": (runtime.adapter.python, EXPECTED_ADAPTER_PYTHON),
        "adapter.script": (runtime.adapter.script, EXPECTED_ADAPTER_SCRIPT),
        "adapter.timeout_seconds": (runtime.adapter.timeout_seconds, 0),
        "adapter.replay_source": (runtime.adapter.replay_source, None),
    }
    drift = [
        f"{field}: expected {expected!r}, got {actual!r}"
        for field, (actual, expected) in fixed_fields.items()
        if actual != expected
    ]
    if drift:
        raise ValueError("runtime template fixed identity drifted: " + "; ".join(drift))
    rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).encode("utf-8")
    _atomic_new_bytes(output, rendered)
    return runtime


def _rebase_path(value: str, staging_root: Path, final_root: Path) -> str:
    path = Path(os.path.abspath(value))
    staging_root = Path(os.path.abspath(staging_root))
    final_root = Path(os.path.abspath(final_root))
    try:
        relative = path.relative_to(staging_root)
    except ValueError:
        return value
    return str(final_root / relative)


def _rebase_media_manifest(
    manifest_path: Path,
    staging_root: Path,
    final_root: Path,
) -> dict:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    MediaManifestV2.model_validate(payload)
    mapping = PreparationPathMapping(final_root, staging_root)
    for collection in (payload["sources"], payload["candidates"]):
        for asset in collection.values():
            asset["video"]["path"] = _rebase_path(
                asset["video"]["path"], staging_root, final_root
            )
            for frame in asset["frames"]:
                frame["path"] = _rebase_path(frame["path"], staging_root, final_root)
            asset["contact_sheet"]["path"] = _rebase_path(
                asset["contact_sheet"]["path"], staging_root, final_root
            )
    for pair_id, packet in payload["pairs"].items():
        if packet["mask_overlay"] is not None:
            packet["mask_overlay"]["path"] = _rebase_path(
                packet["mask_overlay"]["path"], staging_root, final_root
            )
        packet["metadata_path"] = _rebase_path(
            packet["metadata_path"], staging_root, final_root
        )
        identity = {
            "schema_version": "2",
            "pair_id": pair_id,
            "source": payload["sources"][packet["source_asset_id"]],
            "candidate_a": payload["candidates"][packet["candidate_a_asset_id"]],
            "candidate_b": payload["candidates"][packet["candidate_b_asset_id"]],
            "mask_overlay": packet["mask_overlay"],
        }
        packet["packet_checksum"] = canonical_sha256(identity)
        physical_metadata = mapping.physical_path(packet["metadata_path"])
        _atomic_replace_json(
            physical_metadata,
            {**identity, "packet_checksum": packet["packet_checksum"]},
        )
    validated = MediaManifestV2.model_validate(payload).model_dump(mode="json")
    _atomic_replace_json(manifest_path, validated)
    return validated


def _tree_files(root: Path, excluded: Iterable[str] = ()) -> list[Path]:
    excluded_set = set(excluded)
    files = []
    for path in root.rglob("*"):
        if path.relative_to(root).as_posix() in excluded_set:
            continue
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _write_preparation_checksums(root: Path) -> Path:
    target = root / PREPARATION_CHECKSUMS_NAME
    records = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in _tree_files(root, excluded=(PREPARATION_CHECKSUMS_NAME,))
    ]
    _atomic_new_bytes(target, ("\n".join(records) + "\n").encode("utf-8"))
    verify_preparation_checksums(root)
    return target


def verify_preparation_checksums(root: Path) -> int:
    root = Path(root)
    manifest = root / PREPARATION_CHECKSUMS_NAME
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    count = 0
    seen = set()
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        if "  " not in line:
            raise ValueError(f"{manifest}:{line_number}: invalid checksum line")
        expected, relative = line.split("  ", 1)
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"{manifest}:{line_number}: invalid SHA-256")
        if relative in seen or relative == PREPARATION_CHECKSUMS_NAME:
            raise ValueError(f"{manifest}:{line_number}: duplicate/forbidden path {relative}")
        seen.add(relative)
        path = root / Path(relative)
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != expected:
            raise ValueError(f"preparation checksum mismatch: {relative}")
        count += 1
    expected_paths = {
        path.relative_to(root).as_posix()
        for path in _tree_files(root, excluded=(PREPARATION_CHECKSUMS_NAME,))
    }
    if seen != expected_paths:
        raise ValueError(
            f"preparation checksum coverage mismatch: missing={sorted(expected_paths - seen)} "
            f"extra={sorted(seen - expected_paths)}"
        )
    return count


def _prompt_identities(config: Path) -> Dict[str, dict]:
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    identities = {}
    for method, method_config in payload["methods"].items():
        prompt_path = config.parent / method_config["prompt"]
        spec, checksum = load_prompt(prompt_path)
        identities[method] = {
            "path": str(prompt_path.resolve()),
            "sha256": checksum,
            "prompt_version": spec.prompt_version,
            "parser_version": spec.parser_version,
            "generation_parameters": spec.generation_parameters,
        }
    return identities


def _artifact_identity(physical: Path, declared: Path) -> dict:
    return {"path": str(declared), "sha256": sha256_file(physical)}


def _failure_payload(
    prepare_id: str,
    stage: str,
    error: Exception,
    output_root: Path,
    staging_root: Path,
    snapshot: Optional[str],
) -> dict:
    return {
        "schema_version": "1",
        "status": "failed",
        "failed_at": _utc_now(),
        "prepare_id": prepare_id,
        "stage": stage,
        "error_type": type(error).__name__,
        "error": str(error),
        "output_root": str(output_root),
        "staging_root": str(staging_root),
        "code_snapshot": snapshot,
        "ready_for_smoke": False,
    }


def prepare_phase3(
    e0_plan: Path,
    e0_candidates: Path,
    e0_audit: Path,
    config: Path,
    runtime_template: Path,
    model_manifest: Path,
    output_root: Path,
    prepare_id: str,
    *,
    snapshot: Optional[str] = None,
) -> dict:
    """Build, verify, and atomically publish a complete phase-3 root."""
    if not PREPARE_ID_PATTERN.fullmatch(prepare_id):
        raise ValueError(
            "prepare_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,79}"
        )
    e0_plan = Path(e0_plan).resolve()
    e0_candidates = Path(e0_candidates).resolve()
    e0_audit = Path(e0_audit).resolve()
    config = Path(config).resolve()
    runtime_template = Path(runtime_template).resolve()
    model_manifest = Path(model_manifest).resolve()
    output_root = Path(output_root).resolve()
    parent = output_root.parent
    if not parent.is_dir():
        raise FileNotFoundError(f"output parent must already exist: {parent}")
    staging_root = parent / f".{output_root.name}.prepare-{prepare_id}.staging"
    failure_root = parent / f"{output_root.name}.prepare-{prepare_id}.failed"
    for label, path in (
        ("final output root", output_root),
        ("staging root", staging_root),
        ("failure root", failure_root),
    ):
        if _lexists(path):
            raise FileExistsError(f"{label} already exists: {path}")
    for path in (e0_plan, e0_candidates, e0_audit, config, runtime_template, model_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)

    stage = "preflight-input-inventory"
    snapshot_value = snapshot
    external_before = _external_input_inventory(e0_plan, e0_candidates, e0_audit)
    project_root = _project_root(config)
    snapshot_value = snapshot_value or code_snapshot(project_root)
    input_identities = {
        "e0_plan": _file_identity(e0_plan),
        "e0_candidates": _file_identity(e0_candidates),
        "e0_audit": _file_identity(e0_audit),
        "config": _file_identity(config),
        "runtime_template": _file_identity(runtime_template),
        "model_manifest": _file_identity(model_manifest),
        "prompts": _prompt_identities(config),
        "external_inventory": external_before,
    }
    staging_created = False
    published = False
    try:
        stage = "create-staging-layout"
        staging_root.mkdir()
        staging_created = True
        for relative in ("inputs", "human", "plans", "runs", "logs"):
            (staging_root / relative).mkdir()

        stage = "materialize-runtime"
        runtime_path = staging_root / "runtime-dev.yaml"
        runtime = _materialize_runtime(runtime_template, model_manifest, runtime_path)

        stage = "build-pairs"
        pairs_path = staging_root / "inputs" / "pairs.jsonl"
        build_pairs(e0_plan, e0_candidates, e0_audit, config, pairs_path)

        stage = "build-packets"
        packets_path = staging_root / "inputs" / "media-packets"
        build_packets(pairs_path, packets_path)

        stage = "rebase-media-identities"
        manifest_path = packets_path / "media-manifest.json"
        _rebase_media_manifest(manifest_path, staging_root, output_root)

        stage = "build-judge-plan"
        plan_path = staging_root / "plans" / "judge-plan-development.jsonl"
        build_judge_plan(
            pairs_path,
            packets_path,
            config,
            runtime_path,
            plan_path,
            snapshot=snapshot_value,
        )

        stage = "verify-prepublication"
        mapping = PreparationPathMapping(output_root, staging_root)
        report_path = staging_root / PREPARATION_REPORT_NAME
        report = verify_preparation(
            pairs_path,
            packets_path,
            plan_path,
            config,
            runtime_path,
            report_path,
            path_mapping=mapping,
        )

        stage = "verify-external-inputs-before-publish"
        external_after_build = _external_input_inventory(e0_plan, e0_candidates, e0_audit)
        if external_after_build != external_before:
            raise ValueError("E0/external media checksums changed during preparation")

        stage = "write-preparation-receipt"
        receipt_path = staging_root / PREPARATION_RECEIPT_NAME
        receipt = {
            "schema_version": "1",
            "status": "passed",
            "created_at": _utc_now(),
            "prepare_id": prepare_id,
            "code_snapshot": snapshot_value,
            "output_root": str(output_root),
            "staging_root_at_build": str(staging_root),
            "inputs": input_identities,
            "runtime": {
                "backend": runtime.backend,
                "model": runtime.model.model_dump(mode="json"),
                "adapter": runtime.adapter.model_dump(mode="json"),
            },
            "artifacts": {
                "runtime": _artifact_identity(
                    runtime_path, output_root / "runtime-dev.yaml"
                ),
                "pairs": _artifact_identity(
                    pairs_path, output_root / "inputs" / "pairs.jsonl"
                ),
                "media_manifest": _artifact_identity(
                    manifest_path,
                    output_root / "inputs" / "media-packets" / "media-manifest.json",
                ),
                "judge_plan": _artifact_identity(
                    plan_path,
                    output_root / "plans" / "judge-plan-development.jsonl",
                ),
                "verification_report": _artifact_identity(
                    report_path, output_root / PREPARATION_REPORT_NAME
                ),
            },
            "counts": report["counts"],
            "prompt_checksums": report["prompt_checksums"],
            "runtime_fingerprint": report["runtime"]["fingerprint"],
            "external_inputs_unchanged": True,
            "ready_for_smoke": True,
        }
        _atomic_new_json(receipt_path, receipt)

        stage = "write-preparation-checksums"
        checksums_path = _write_preparation_checksums(staging_root)
        checksum_file_count = verify_preparation_checksums(staging_root)
        checksums_sha256 = sha256_file(checksums_path)

        stage = "atomic-publish"
        _rename_noreplace(staging_root, output_root)
        published = True

        stage = "verify-external-inputs-after-publish"
        external_after_publish = _external_input_inventory(e0_plan, e0_candidates, e0_audit)
        if external_after_publish != external_before:
            failure_marker = output_root / "PREPARATION_PUBLISH_FAILED.json"
            _atomic_new_json(
                failure_marker,
                {
                    "schema_version": "1",
                    "status": "failed",
                    "failed_at": _utc_now(),
                    "prepare_id": prepare_id,
                    "stage": stage,
                    "error": "E0/external media checksums changed after publish",
                    "ready_for_smoke": False,
                },
            )
            raise ValueError("E0/external media checksums changed after publish")

        return {
            "status": "passed",
            "prepare_id": prepare_id,
            "output_root": str(output_root),
            "verification_report": str(output_root / PREPARATION_REPORT_NAME),
            "receipt": str(output_root / PREPARATION_RECEIPT_NAME),
            "checksums": str(output_root / PREPARATION_CHECKSUMS_NAME),
            "checksums_sha256": checksums_sha256,
            "checksummed_files": checksum_file_count,
            "counts": report["counts"],
            "ready_for_smoke": True,
        }
    except Exception as exc:
        if published:
            raise Phase3PreparationError(
                stage, exc, published_root=output_root
            ) from exc
        preserved_failure: Optional[Path] = None
        preserved_staging: Optional[Path] = staging_root if staging_created else None
        if staging_created and staging_root.exists():
            marker = staging_root / FAILURE_MARKER_NAME
            if not marker.exists():
                try:
                    _atomic_new_json(
                        marker,
                        _failure_payload(
                            prepare_id,
                            stage,
                            exc,
                            output_root,
                            staging_root,
                            snapshot_value,
                        ),
                    )
                except Exception:
                    pass
            try:
                _rename_noreplace(staging_root, failure_root)
            except Exception:
                preserved_staging = staging_root
            else:
                preserved_failure = failure_root
                preserved_staging = None
        raise Phase3PreparationError(
            stage,
            exc,
            failure_root=preserved_failure,
            staging_root=preserved_staging,
        ) from exc
