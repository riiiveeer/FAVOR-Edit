"""E1 judge runner, plan, locking, and merge."""

import json
import os
import socket
from pathlib import Path
from typing import List, Optional

import yaml

from .backends import CommandBackend, JudgeBackend, MockBackend, ReplayBackend
from .cache import JudgeCache
from .hashing import canonical_sha256
from .models import JudgeRequest

LOCK_NAME = ".e1-run.lock"


def judge_key(request: dict) -> str:
    """Canonical SHA-256 over all identity-bearing fields (§13.2)."""
    fields = [
        request["source_checksum"],
        request["candidate_a_checksum"],
        request.get("candidate_b_checksum"),
        request["method"],
        request["comparison_direction"],
        request["backend"],
        request["model_name"],
        request["model_revision"],
        request["prompt_version"],
        request["parser_version"],
        request["media_packet_checksum"],
        request["generation_parameters"],
    ]
    return canonical_sha256(fields)


def acquire_lock(experiment_dir: Path) -> None:
    """Acquire an exclusive lock via O_CREAT|O_EXCL; fail if a live lock exists."""
    Path(experiment_dir).mkdir(parents=True, exist_ok=True)
    lock_path = Path(experiment_dir) / LOCK_NAME
    payload = {
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "command": "e1 run",
        "started_at": "",
    }
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle)
    except FileExistsError as exc:
        raise RuntimeError(f"run lock exists at {lock_path}; use `e1 unlock` after confirming no live process") from exc


def release_lock(experiment_dir: Path) -> None:
    lock_path = Path(experiment_dir) / LOCK_NAME
    if lock_path.exists():
        lock_path.unlink()


def unlock(experiment_dir: Path, reason: str) -> None:
    lock_path = Path(experiment_dir) / LOCK_NAME
    if not lock_path.exists():
        raise FileNotFoundError(f"no lock found at {lock_path}")
    audit = Path(experiment_dir) / ".e1-unlock.log"
    with audit.open("a", encoding="utf-8") as handle:
        handle.write(f"unlocked reason={reason}\n")
    lock_path.unlink()


def _load_backend(backend: str, judge_python: Optional[str], judge_script: Optional[str]) -> JudgeBackend:
    if backend == "mock":
        return MockBackend()
    if backend == "command":
        if not judge_python or not judge_script:
            raise ValueError("command backend requires --judge-python and --judge-script")
        return CommandBackend(judge_python, judge_script)
    if backend == "replay":
        raise ValueError("replay backend requires a source dir via run command")
    raise ValueError(f"unknown backend: {backend}")


def build_judge_plan(pairs: Path, config: Path, output: Path) -> List[dict]:
    """Expand pairs into the 550 judge requests across four methods."""
    pair_records = [json.loads(line) for line in Path(pairs).read_text(encoding="utf-8").splitlines() if line.strip()]
    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    methods = cfg["methods"]

    requests: List[dict] = []
    # absolute-v1: one request per unique candidate (50 total), not per pair.
    candidates_seen = {}
    for pair in pair_records:
        candidates_seen[pair["candidate_left_id"]] = (pair["candidate_left_checksum"], pair["candidate_left_path"])
        candidates_seen[pair["candidate_right_id"]] = (pair["candidate_right_checksum"], pair["candidate_right_path"])

    for method_name, method_cfg in methods.items():
        prompt = method_cfg.get("prompt", f"prompt-{method_name}.yaml")
        swap = bool(method_cfg.get("swap", False))
        if method_name == "absolute-v1":
            for candidate_id, (checksum, _) in sorted(candidates_seen.items()):
                request = _absolute_request(pair_records, candidate_id, checksum, method_name, prompt)
                request["judge_key"] = judge_key(request)
                requests.append(request)
            continue
        for pair in pair_records:
            directions = ("a_vs_b", "b_vs_a") if swap else ("a_vs_b",)
            for direction in directions:
                request = _request_for(pair, method_name, prompt, direction)
                request["judge_key"] = judge_key(request)
                requests.append(request)

    expected = int(cfg.get("total_requests", 550))
    if len(requests) != expected:
        raise ValueError(f"expected {expected} judge requests, got {len(requests)}")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with Path(output).open("w", encoding="utf-8") as handle:
        for request in requests:
            handle.write(json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n")
    return requests


def _absolute_request(pairs: List[dict], candidate_id: str, checksum: str, method: str, prompt: str) -> dict:
    pair = pairs[0]
    request = {
        "request_id": f"{method}:{candidate_id}:absolute",
        "pair_id": None,
        "candidate_id": candidate_id,
        "method": method,
        "comparison_direction": "absolute",
        "source_checksum": pair["source_checksum"],
        "candidate_a_checksum": checksum,
        "candidate_b_checksum": None,
        "instruction": pair["instruction"],
        "target_caption": pair["target_caption"],
        "task_type": pair["task_type"],
        "media_packet_checksum": "p" * 64,
        "backend": "mock",
        "model_name": "mock",
        "model_revision": "mock-v1",
        "prompt_version": prompt,
        "parser_version": "1",
        "generation_parameters": {},
    }
    JudgeRequest.model_validate(request)
    return request


def _request_for(pair: dict, method: str, prompt: str, direction: str) -> dict:
    a_id = pair["candidate_left_id"]
    b_id = pair["candidate_right_id"]
    a_checksum = pair["candidate_left_checksum"]
    b_checksum = pair["candidate_right_checksum"]
    if direction == "b_vs_a":
        a_id, b_id = b_id, a_id
        a_checksum, b_checksum = b_checksum, a_checksum

    request = {
        "request_id": f"{method}:{pair['pair_id']}:{direction}",
        "pair_id": pair["pair_id"],
        "candidate_id": None,
        "method": method,
        "comparison_direction": direction,
        "source_checksum": pair["source_checksum"],
        "candidate_a_checksum": a_checksum,
        "candidate_b_checksum": b_checksum,
        "instruction": pair["instruction"],
        "target_caption": pair["target_caption"],
        "task_type": pair["task_type"],
        "media_packet_checksum": "p" * 64,
        "backend": "mock",
        "model_name": "mock",
        "model_revision": "mock-v1",
        "prompt_version": prompt,
        "parser_version": "1",
        "generation_parameters": {},
    }
    JudgeRequest.model_validate(request)
    return request


def run_judge(
    backend: str,
    plan: Path,
    experiment_dir: Path,
    cache: Path,
    split: Optional[str],
    judge_python: Optional[str],
    judge_script: Optional[str],
) -> int:
    """Run pending judge requests with lock + cache resume; returns completed count."""
    requests = [json.loads(line) for line in Path(plan).read_text(encoding="utf-8").splitlines() if line.strip()]
    if split:
        requests = [r for r in requests if r.get("split") == split]

    implementation = _load_backend(backend, judge_python, judge_script)
    acquire_lock(experiment_dir)
    try:
        results_dir = Path(experiment_dir) / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        raw_dir = Path(experiment_dir) / "raw-responses"
        raw_dir.mkdir(parents=True, exist_ok=True)

        completed = 0
        with JudgeCache(cache) as store:
            for request in requests:
                key = request["judge_key"]
                cached = store.get(key)
                if cached is not None:
                    completed += 1
                    continue
                request_path = results_dir / f"{request['request_id']}.json"
                output_path = results_dir / f"{request['request_id']}.result.json"
                request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")
                try:
                    implementation.run(request_path, output_path)
                    result = json.loads(output_path.read_text(encoding="utf-8"))
                    raw = result.get("raw_response", {})
                    (raw_dir / f"{request['request_id']}.json").write_text(
                        json.dumps(raw, ensure_ascii=False, sort_keys=True), encoding="utf-8"
                    )
                    store.put(key, request["request_id"], "succeeded", result)
                    completed += 1
                except Exception as exc:  # noqa: BLE001
                    store.put(key, request["request_id"], "failed", {"request_id": request["request_id"]}, str(exc))
        return completed
    finally:
        release_lock(experiment_dir)


def merge_results(inputs: List[Path], output: Path) -> List[dict]:
    """Merge dev-final and frozen-eval results, rejecting duplicate request IDs."""
    seen = {}
    for path in inputs:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            request_id = record.get("request_id") or record.get("judge_key")
            if request_id in seen:
                raise ValueError(f"duplicate request ID {request_id} across inputs")
            seen[request_id] = record

    records = list(seen.values())
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with Path(output).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return records
