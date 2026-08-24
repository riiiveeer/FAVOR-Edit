"""Schema-v2 planning, batch execution, locking, resume, and result merging."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import yaml

from w1_pipeline.hashing import sha256_file

from .backends import CommandBackend, JudgeBackend, MockBackend, ReplayBackend
from .cache import JudgeCache
from .hashing import canonical_sha256
from .models import (
    JudgeRequestV2, JudgeResultV2, MediaAssetV2, MediaManifestV2, PairRecordV2,
    RequestMediaV2, RuntimeConfigV2, load_runtime_config, validate_config,
)
from .prompts import load_prompt, parse_response, render_prompt

LOCK_NAME = ".e1-run.lock"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl_atomic(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def code_snapshot(project_dir: Optional[Path] = None) -> str:
    cwd = str(project_dir) if project_dir else None
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        return f"{head}+dirty" if dirty else head
    except (OSError, subprocess.CalledProcessError):
        return "unknown-code-snapshot"


def runtime_fingerprint(runtime: RuntimeConfigV2) -> str:
    script_identity = None
    if runtime.adapter.script:
        script = Path(runtime.adapter.script)
        script_identity = sha256_file(script) if script.is_file() else script.name
    identity = {
        "schema_version": "2",
        "backend": runtime.backend,
        "model": {
            "name": runtime.model.name,
            "revision": runtime.model.revision,
            "manifest_sha256": runtime.model.manifest_sha256,
            "local_path": runtime.model.local_path,
        },
        "adapter": {
            "python": runtime.adapter.python,
            "script": str(runtime.adapter.script) if runtime.adapter.script else None,
            "script_identity": script_identity,
            "timeout_seconds": runtime.adapter.timeout_seconds,
            "replay_source": runtime.adapter.replay_source,
        },
    }
    return canonical_sha256(identity)


def frozen_protocol_fingerprint(
    config: Path,
    config_data: dict,
    prompt_checksums: Dict[str, str],
    runtime_sha: str,
    snapshot: str,
) -> Optional[str]:
    """Fingerprint the immutable inputs available before the frozen plan is written."""
    selection = config_data.get("frozen_selection")
    if selection is None:
        return None
    return canonical_sha256({
        "schema_version": "2",
        "code_snapshot": snapshot,
        "config_sha256": sha256_file(config),
        "runtime_fingerprint": runtime_sha,
        "prompt_checksums": prompt_checksums,
        "selection": selection,
    })


def judge_key(request: dict) -> str:
    def media_identity(media: Optional[dict]):
        if media is None:
            return None
        return {
            "asset_id": media["asset_id"],
            "video_sha256": media["video_sha256"],
            "frame_sha256": media["frame_sha256"],
            "contact_sheet_sha256": media["contact_sheet_sha256"],
        }

    identity = {
        "schema_version": request["schema_version"],
        "sample_id": request["sample_id"],
        "pair_id": request.get("pair_id"),
        "candidate_id": request.get("candidate_id"),
        "instruction": request["instruction"],
        "target_caption": request["target_caption"],
        "method": request["method"],
        "comparison_direction": request["comparison_direction"],
        "candidate_a_id": request["candidate_a_id"],
        "candidate_b_id": request.get("candidate_b_id"),
        "source": media_identity(request["source"]),
        "candidate_a": media_identity(request["candidate_a"]),
        "candidate_b": media_identity(request.get("candidate_b")),
        "mask_overlay": request.get("mask_overlay"),
        "media_packet_checksum": request["media_packet_checksum"],
        "backend": request["backend"],
        "model_name": request["model_name"],
        "model_revision": request["model_revision"],
        "model_manifest_sha256": request["model_manifest_sha256"],
        "prompt_version": request["prompt_version"],
        "prompt_checksum": request["prompt_checksum"],
        "rendered_prompt": request["rendered_prompt"],
        "parser_version": request["parser_version"],
        "generation_parameters": request["generation_parameters"],
        "runtime_fingerprint": request["runtime_fingerprint"],
        "frozen_protocol_fingerprint": request.get("frozen_protocol_fingerprint"),
        "code_snapshot": request["code_snapshot"],
    }
    return canonical_sha256(identity)


def _request_media(asset: MediaAssetV2) -> dict:
    return RequestMediaV2(
        asset_id=asset.asset_id,
        video_path=asset.video.path,
        video_sha256=asset.original_sha256,
        frame_paths=[frame.path for frame in asset.frames],
        frame_sha256=[frame.sha256 for frame in asset.frames],
        contact_sheet_path=asset.contact_sheet.path,
        contact_sheet_sha256=asset.contact_sheet.sha256,
    ).model_dump(mode="json")


def _base_request(
    pair: PairRecordV2,
    method: str,
    prompt_spec,
    prompt_sha: str,
    runtime: RuntimeConfigV2,
    runtime_sha: str,
    snapshot: str,
    protocol_sha: Optional[str],
) -> dict:
    return {
        "schema_version": "2",
        "sample_id": pair.sample_id,
        "split": pair.split,
        "task_type": pair.task_type,
        "instruction": pair.instruction,
        "target_caption": pair.target_caption,
        "method": method,
        "backend": runtime.backend,
        "model_name": runtime.model.name,
        "model_revision": runtime.model.revision,
        "model_manifest_sha256": runtime.model.manifest_sha256,
        "prompt_version": prompt_spec.prompt_version,
        "prompt_checksum": prompt_sha,
        "rendered_prompt": render_prompt(prompt_spec, pair.instruction, pair.target_caption),
        "parser_version": prompt_spec.parser_version,
        "generation_parameters": prompt_spec.generation_parameters,
        "runtime_fingerprint": runtime_sha,
        "frozen_protocol_fingerprint": protocol_sha,
        "code_snapshot": snapshot,
    }


def build_judge_plan(
    pairs: Path,
    packets: Path,
    config: Path,
    runtime_config: Path,
    output: Path,
    snapshot: Optional[str] = None,
) -> List[dict]:
    """Expand v2 pairs into 550 fully identified requests."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"judge plan already exists: {output}")
    cfg = validate_config(config)
    runtime = load_runtime_config(runtime_config)
    runtime_sha = runtime_fingerprint(runtime)
    snapshot = snapshot or code_snapshot(Path(config).resolve().parents[2])
    pair_records = [PairRecordV2.model_validate(record) for record in _read_jsonl(pairs)]
    manifest_path = Path(packets)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "media-manifest.json"
    manifest = MediaManifestV2.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))

    prompts = {}
    for method, method_cfg in cfg["methods"].items():
        prompts[method] = load_prompt(Path(config).parent / method_cfg["prompt"])
    protocol_sha = frozen_protocol_fingerprint(
        Path(config), cfg, {method: item[1] for method, item in prompts.items()}, runtime_sha, snapshot
    )

    candidate_context: Dict[str, PairRecordV2] = {}
    sample_packet = {}
    for pair in pair_records:
        for candidate in (pair.candidate_a, pair.candidate_b):
            existing = candidate_context.get(candidate.candidate_id)
            if existing and existing.sample_id != pair.sample_id:
                raise ValueError(f"candidate {candidate.candidate_id} appears in multiple samples")
            candidate_context[candidate.candidate_id] = pair
        sample_packet.setdefault(pair.sample_id, manifest.pairs[pair.pair_id])

    requests: List[dict] = []
    absolute_spec, absolute_sha = prompts["absolute-v1"]
    for candidate_id in sorted(candidate_context):
        pair = candidate_context[candidate_id]
        candidate = pair.candidate_a if pair.candidate_a.candidate_id == candidate_id else pair.candidate_b
        source_asset = manifest.sources[pair.sample_id]
        candidate_asset = manifest.candidates[candidate_id]
        mask = sample_packet[pair.sample_id].mask_overlay
        request = {
            **_base_request(
                pair, "absolute-v1", absolute_spec, absolute_sha, runtime, runtime_sha, snapshot, protocol_sha
            ),
            "request_id": f"absolute-v1:{candidate_id}:absolute",
            "judge_key": "0" * 64,
            "pair_id": None,
            "candidate_id": candidate_id,
            "comparison_direction": "absolute",
            "candidate_a_id": candidate_id,
            "candidate_b_id": None,
            "source": _request_media(source_asset),
            "candidate_a": _request_media(candidate_asset),
            "candidate_b": None,
            "mask_overlay": mask.model_dump(mode="json") if mask else None,
            "media_packet_checksum": canonical_sha256({
                "source": source_asset.original_sha256,
                "candidate": candidate_asset.original_sha256,
                "mask": mask.model_dump(mode="json") if mask else None,
            }),
        }
        request["judge_key"] = judge_key(request)
        requests.append(JudgeRequestV2.model_validate(request).model_dump(mode="json"))

    for method in ("pairwise-single-v1", "pairwise-swap-v1", "rubric-swap-v1"):
        prompt_spec, prompt_sha = prompts[method]
        swap = bool(cfg["methods"][method]["swap"])
        for pair in pair_records:
            packet = manifest.pairs[pair.pair_id]
            source_asset = manifest.sources[pair.sample_id]
            canonical_assets = [
                (pair.candidate_a.candidate_id, manifest.candidates[pair.candidate_a.candidate_id]),
                (pair.candidate_b.candidate_id, manifest.candidates[pair.candidate_b.candidate_id]),
            ]
            directions = ("a_vs_b", "b_vs_a") if swap else ("a_vs_b",)
            for direction in directions:
                screen_assets = canonical_assets if direction == "a_vs_b" else list(reversed(canonical_assets))
                request = {
                    **_base_request(
                        pair, method, prompt_spec, prompt_sha, runtime, runtime_sha, snapshot, protocol_sha
                    ),
                    "request_id": f"{method}:{pair.pair_id}:{direction}",
                    "judge_key": "0" * 64,
                    "pair_id": pair.pair_id,
                    "candidate_id": None,
                    "comparison_direction": direction,
                    "candidate_a_id": screen_assets[0][0],
                    "candidate_b_id": screen_assets[1][0],
                    "source": _request_media(source_asset),
                    "candidate_a": _request_media(screen_assets[0][1]),
                    "candidate_b": _request_media(screen_assets[1][1]),
                    "mask_overlay": packet.mask_overlay.model_dump(mode="json") if packet.mask_overlay else None,
                    "media_packet_checksum": packet.packet_checksum,
                }
                request["judge_key"] = judge_key(request)
                requests.append(JudgeRequestV2.model_validate(request).model_dump(mode="json"))

    if len(requests) != 550 or len({request["judge_key"] for request in requests}) != 550:
        raise ValueError("judge plan must contain 550 unique judge keys")
    split_counts = {split: sum(request["split"] == split for request in requests) for split in ("dev", "frozen-eval")}
    if split_counts != {"dev": 165, "frozen-eval": 385}:
        raise ValueError(f"expected dev/frozen request counts 165/385, got {split_counts}")
    _write_jsonl_atomic(output, requests)
    return requests


def acquire_lock(experiment_dir: Path, command: str = "e1 run") -> None:
    experiment_dir.mkdir(parents=True, exist_ok=True)
    lock_path = experiment_dir / LOCK_NAME
    payload = {
        "pid": os.getpid(), "hostname": socket.gethostname(),
        "command": command, "started_at": _utc_now(),
    }
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
    except FileExistsError as exc:
        raise RuntimeError(f"run lock exists at {lock_path}; confirm process state before e1 unlock") from exc


def release_lock(experiment_dir: Path) -> None:
    lock_path = experiment_dir / LOCK_NAME
    if lock_path.exists():
        lock_path.unlink()


def unlock(experiment_dir: Path, reason: str) -> None:
    lock_path = Path(experiment_dir) / LOCK_NAME
    if not lock_path.is_file():
        raise FileNotFoundError(f"no lock found at {lock_path}")
    with (Path(experiment_dir) / ".e1-unlock.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": _utc_now(), "reason": reason}, sort_keys=True) + "\n")
    lock_path.unlink()


def _backend(runtime: RuntimeConfigV2) -> JudgeBackend:
    if runtime.backend == "mock":
        return MockBackend()
    if runtime.backend == "command":
        return CommandBackend()
    if runtime.backend == "replay":
        return ReplayBackend()
    raise ValueError(f"unknown backend {runtime.backend}")


def _failed_result(request: JudgeRequestV2, error: str) -> dict:
    return JudgeResultV2(
        request_id=request.request_id, judge_key=request.judge_key,
        pair_id=request.pair_id, candidate_id=request.candidate_id,
        sample_id=request.sample_id, split=request.split, method=request.method,
        comparison_direction=request.comparison_direction,
        candidate_a_id=request.candidate_a_id, candidate_b_id=request.candidate_b_id,
        status="failed", parsed=None, raw_response={}, parse_error=error,
        runtime_seconds=0, peak_vram_mb=0,
        prompt_version=request.prompt_version, prompt_checksum=request.prompt_checksum,
        parser_version=request.parser_version, generation_parameters=request.generation_parameters,
        model_name=request.model_name, model_revision=request.model_revision,
        model_manifest_sha256=request.model_manifest_sha256,
        runtime_fingerprint=request.runtime_fingerprint,
        frozen_protocol_fingerprint=request.frozen_protocol_fingerprint, created_at=_utc_now(),
    ).model_dump(mode="json")


def _ingest_envelope(request: JudgeRequestV2, path: Path, raw_dir: Path) -> dict:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("request_id") != request.request_id or envelope.get("judge_key") != request.judge_key:
        raise ValueError("adapter envelope identity mismatch")
    raw_target = raw_dir / f"{request.judge_key}.json"
    temporary = raw_target.with_suffix(".tmp")
    shutil.copy2(path, temporary)
    temporary.replace(raw_target)
    runtime_seconds = float(envelope.get("runtime_seconds", 0))
    peak_vram_mb = float(envelope.get("peak_vram_mb", 0))
    if envelope.get("status") != "succeeded":
        result = _failed_result(request, str(envelope.get("error") or "adapter reported failure"))
        result["raw_response"] = envelope.get("raw_response", {})
        result["runtime_seconds"] = runtime_seconds
        result["peak_vram_mb"] = peak_vram_mb
        return result
    raw_text = envelope.get("raw_text")
    parsed = parse_response(request.method, raw_text)
    raw_response = dict(envelope.get("raw_response") or {})
    raw_response["text"] = raw_text
    return JudgeResultV2(
        request_id=request.request_id, judge_key=request.judge_key,
        pair_id=request.pair_id, candidate_id=request.candidate_id,
        sample_id=request.sample_id, split=request.split, method=request.method,
        comparison_direction=request.comparison_direction,
        candidate_a_id=request.candidate_a_id, candidate_b_id=request.candidate_b_id,
        status="succeeded", parsed=parsed, raw_response=raw_response, parse_error=None,
        runtime_seconds=runtime_seconds, peak_vram_mb=peak_vram_mb,
        prompt_version=request.prompt_version, prompt_checksum=request.prompt_checksum,
        parser_version=request.parser_version, generation_parameters=request.generation_parameters,
        model_name=request.model_name, model_revision=request.model_revision,
        model_manifest_sha256=request.model_manifest_sha256,
        runtime_fingerprint=request.runtime_fingerprint,
        frozen_protocol_fingerprint=request.frozen_protocol_fingerprint, created_at=_utc_now(),
    ).model_dump(mode="json")


def run_judge(
    plan: Path,
    runtime_config: Path,
    experiment_dir: Path,
    cache: Path,
    split: Optional[str] = None,
    request_ids: Optional[Sequence[str]] = None,
) -> Dict[str, int]:
    """Run one model process for all pending requests in the selected shard."""
    runtime = load_runtime_config(runtime_config)
    expected_fingerprint = runtime_fingerprint(runtime)
    requests = [JudgeRequestV2.model_validate(record) for record in _read_jsonl(plan)]
    if split:
        if split not in {"dev", "frozen-eval"}:
            raise ValueError("split must be dev or frozen-eval")
        requests = [request for request in requests if request.split == split]
    if request_ids:
        selected_ids = set(request_ids)
        requests = [request for request in requests if request.request_id in selected_ids]
        missing_ids = selected_ids - {request.request_id for request in requests}
        if missing_ids:
            raise ValueError(f"request IDs not present in selected plan: {sorted(missing_ids)}")
    if not requests:
        raise ValueError("selected judge shard contains no requests")
    for request in requests:
        if request.runtime_fingerprint != expected_fingerprint or request.backend != runtime.backend:
            raise ValueError("runtime config does not match plan fingerprint")

    experiment_dir = Path(experiment_dir)
    acquire_lock(experiment_dir)
    try:
        raw_dir = experiment_dir / "raw-responses"
        raw_dir.mkdir(parents=True, exist_ok=True)
        with JudgeCache(cache) as store:
            cache_hits = sum(store.get_succeeded(request.judge_key) is not None for request in requests)
            pending = [request for request in requests if store.get_succeeded(request.judge_key) is None]
            backend_error = None
            batch_output = None
            if pending:
                batches = experiment_dir / "batches"
                batches.mkdir(exist_ok=True)
                attempt = 1
                while (batches / f"attempt-{attempt:04d}").exists():
                    attempt += 1
                batch_dir = batches / f"attempt-{attempt:04d}"
                batch_output = batch_dir / "adapter-output"
                batch_dir.mkdir()
                pending_path = batch_dir / "pending.jsonl"
                _write_jsonl_atomic(pending_path, [request.model_dump(mode="json") for request in pending])
                try:
                    _backend(runtime).run_batch(pending_path, batch_output, runtime)
                except Exception as exc:  # partial outputs remain ingestible
                    backend_error = str(exc)

                for request in pending:
                    envelope_path = batch_output / f"{request.judge_key}.json"
                    if not envelope_path.is_file():
                        result = _failed_result(request, backend_error or "adapter produced no envelope")
                    else:
                        try:
                            result = _ingest_envelope(request, envelope_path, raw_dir)
                        except Exception as exc:
                            result = _failed_result(request, str(exc))
                            try:
                                shutil.copy2(envelope_path, raw_dir / f"{request.judge_key}.json")
                            except OSError:
                                pass
                    store.put(
                        request.judge_key, request.request_id, result["status"], result,
                        result.get("parse_error"), result.get("runtime_seconds", 0), result.get("peak_vram_mb", 0),
                    )

            succeeded = store.succeeded_payloads([request.judge_key for request in requests])
            ordered_results = [succeeded[request.judge_key] for request in requests if request.judge_key in succeeded]
            _write_jsonl_atomic(experiment_dir / "results.jsonl", ordered_results)
            return {
                "selected": len(requests),
                "cache_hits": cache_hits,
                "attempted": len(pending),
                "succeeded": len(ordered_results),
                "failed": len(requests) - len(ordered_results),
            }
    finally:
        release_lock(experiment_dir)


def merge_results(inputs: List[Path], output: Path) -> List[dict]:
    seen: Dict[str, dict] = {}
    method_identity: Dict[str, tuple] = {}
    runtime_ids = set()
    for path in inputs:
        for record_data in _read_jsonl(path):
            record = JudgeResultV2.model_validate(record_data).model_dump(mode="json")
            if record["request_id"] in seen:
                raise ValueError(f"duplicate request ID {record['request_id']} across inputs")
            identity = (
                record["prompt_version"], record["prompt_checksum"], record["parser_version"],
                canonical_sha256(record["generation_parameters"]), record["model_name"],
                record["model_revision"], record["model_manifest_sha256"],
                record["frozen_protocol_fingerprint"],
            )
            previous = method_identity.setdefault(record["method"], identity)
            if previous != identity:
                raise ValueError(f"mixed prompt/parser/model identity for method {record['method']}")
            runtime_ids.add(record["runtime_fingerprint"])
            seen[record["request_id"]] = record
    if len(runtime_ids) > 1:
        raise ValueError("cannot merge results from mixed runtime fingerprints")
    records = sorted(seen.values(), key=lambda item: item["request_id"])
    _write_jsonl_atomic(output, records)
    return records
