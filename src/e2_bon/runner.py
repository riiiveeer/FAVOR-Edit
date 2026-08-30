"""E2 batch execution using the audited E1 backend/cache envelope contract."""

from __future__ import annotations

import json
import os
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from e1_judge.backends import CommandBackend, MockBackend, ReplayBackend
from e1_judge.cache import JudgeCache
from e1_judge.models import RuntimeConfigV2, load_runtime_config
from e1_judge.prompts import parse_response
from e1_judge.runner import runtime_fingerprint

from .models import E2JudgeRequestV1, E2JudgeResultV1

LOCK_NAME = ".e2-run.lock"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def _acquire(experiment_dir: Path) -> None:
    experiment_dir.mkdir(parents=True, exist_ok=True)
    lock = experiment_dir / LOCK_NAME
    payload = {"pid": os.getpid(), "hostname": socket.gethostname(), "started_at": _utc_now(), "command": "e2 run"}
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
    except FileExistsError as exc:
        raise RuntimeError(f"E2 run lock exists at {lock}") from exc


def _release(experiment_dir: Path) -> None:
    lock = experiment_dir / LOCK_NAME
    if lock.exists():
        lock.unlink()


def unlock(experiment_dir: Path, reason: str) -> None:
    lock = Path(experiment_dir) / LOCK_NAME
    if not lock.is_file():
        raise FileNotFoundError(lock)
    with (Path(experiment_dir) / ".e2-unlock.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": _utc_now(), "reason": reason}, sort_keys=True) + "\n")
    lock.unlink()


def _backend(runtime: RuntimeConfigV2):
    if runtime.backend == "mock":
        return MockBackend()
    if runtime.backend == "replay":
        return ReplayBackend()
    if runtime.backend == "command":
        return CommandBackend()
    raise ValueError(runtime.backend)


def _result(request: E2JudgeRequestV1, status: str, parsed=None, raw=None, error=None, runtime_seconds=0.0, peak_vram_mb=0.0) -> dict:
    return E2JudgeResultV1(
        experiment_id=request.experiment_id, stage=request.stage, split=request.split,
        request_id=request.request_id, judge_key=request.judge_key, pair_id=request.pair_id,
        sample_id=request.sample_id, method=request.method,
        comparison_direction=request.comparison_direction,
        candidate_a_id=request.candidate_a_id, candidate_b_id=request.candidate_b_id,
        status=status, parsed=parsed, raw_response=raw or {}, parse_error=error,
        runtime_seconds=runtime_seconds, peak_vram_mb=peak_vram_mb,
        prompt_version=request.prompt_version, prompt_checksum=request.prompt_checksum,
        parser_version=request.parser_version, generation_parameters=request.generation_parameters,
        model_name=request.model_name, model_revision=request.model_revision,
        model_manifest_sha256=request.model_manifest_sha256,
        runtime_fingerprint=request.runtime_fingerprint,
        e1_protocol_fingerprint=request.e1_protocol_fingerprint,
        reward_artifact_sha256=request.reward_artifact_sha256,
        created_at=_utc_now(),
    ).model_dump(mode="json")


def _ingest(request: E2JudgeRequestV1, envelope_path: Path, raw_dir: Path) -> dict:
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    if envelope.get("request_id") != request.request_id or envelope.get("judge_key") != request.judge_key:
        raise ValueError("adapter envelope identity mismatch")
    raw_target = raw_dir / f"{request.judge_key}.json"
    temporary = raw_target.with_suffix(".tmp")
    shutil.copy2(envelope_path, temporary)
    temporary.replace(raw_target)
    runtime_seconds = float(envelope.get("runtime_seconds", 0))
    peak_vram_mb = float(envelope.get("peak_vram_mb", 0))
    if envelope.get("status") != "succeeded":
        return _result(
            request, "failed", raw=envelope.get("raw_response", {}),
            error=str(envelope.get("error") or "adapter reported failure"),
            runtime_seconds=runtime_seconds, peak_vram_mb=peak_vram_mb,
        )
    raw_text = envelope.get("raw_text")
    parsed = parse_response(request.method, raw_text)
    raw = dict(envelope.get("raw_response") or {})
    raw["text"] = raw_text
    return _result(
        request, "succeeded", parsed=parsed, raw=raw,
        runtime_seconds=runtime_seconds, peak_vram_mb=peak_vram_mb,
    )


def run_e2_judge(
    plan: Path, runtime_path: Path, experiment_dir: Path, cache_path: Path,
    request_ids: Optional[Sequence[str]] = None,
) -> Dict[str, int]:
    runtime = load_runtime_config(runtime_path)
    runtime_sha = runtime_fingerprint(runtime)
    requests = [E2JudgeRequestV1.model_validate(item) for item in _read_jsonl(plan)]
    if request_ids:
        selected = set(request_ids)
        requests = [item for item in requests if item.request_id in selected]
        missing = selected - {item.request_id for item in requests}
        if missing:
            raise ValueError(f"request IDs missing from E2 plan: {sorted(missing)}")
    if not requests:
        raise ValueError("E2 selected shard contains no requests")
    if len({item.stage for item in requests}) != 1:
        raise ValueError("one E2 run may contain only one request stage")
    for request in requests:
        if request.runtime_fingerprint != runtime_sha or request.backend != runtime.backend:
            raise ValueError("E2 runtime does not match plan fingerprint")

    experiment_dir = Path(experiment_dir)
    _acquire(experiment_dir)
    try:
        raw_dir = experiment_dir / "raw-responses"
        raw_dir.mkdir(parents=True, exist_ok=True)
        with JudgeCache(cache_path) as store:
            cache_hits = sum(store.get_succeeded(item.judge_key) is not None for item in requests)
            pending = [item for item in requests if store.get_succeeded(item.judge_key) is None]
            backend_error = None
            output_dir = None
            if pending:
                batches = experiment_dir / "batches"
                batches.mkdir(exist_ok=True)
                attempt = 1
                while (batches / f"attempt-{attempt:04d}").exists():
                    attempt += 1
                batch = batches / f"attempt-{attempt:04d}"
                batch.mkdir()
                output_dir = batch / "adapter-output"
                pending_path = batch / "pending.jsonl"
                _write_jsonl(pending_path, [item.model_dump(mode="json") for item in pending])
                try:
                    _backend(runtime).run_batch(pending_path, output_dir, runtime)
                except Exception as exc:
                    backend_error = str(exc)
                for request in pending:
                    envelope = output_dir / f"{request.judge_key}.json"
                    if not envelope.is_file():
                        result = _result(request, "failed", error=backend_error or "adapter produced no envelope")
                    else:
                        try:
                            result = _ingest(request, envelope, raw_dir)
                        except Exception as exc:
                            result = _result(request, "failed", error=str(exc))
                    store.put(
                        request.judge_key, request.request_id, result["status"], result,
                        result.get("parse_error"), result.get("runtime_seconds", 0), result.get("peak_vram_mb", 0),
                    )
            succeeded = store.succeeded_payloads([item.judge_key for item in requests])
            ordered = [succeeded[item.judge_key] for item in requests if item.judge_key in succeeded]
            _write_jsonl(experiment_dir / "results.jsonl", ordered)
            return {
                "selected": len(requests), "cache_hits": cache_hits, "attempted": len(pending),
                "succeeded": len(ordered), "failed": len(requests) - len(ordered),
                "research_measurements": len(ordered) if runtime.backend == "command" else 0,
            }
    finally:
        _release(experiment_dir)
