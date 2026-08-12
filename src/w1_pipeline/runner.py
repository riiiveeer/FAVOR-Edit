"""Idempotent candidate runner."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .backends import GenerationBackend
from .cache import Cache
from .models import CandidateRecord, CandidateStatus


def load_plan(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if set(value) != {"inversions", "candidates"}:
        raise ValueError("plan must contain inversions and candidates")
    return value


def run_candidates(plan_path: Path, experiment_dir: Path, cache_path: Path, backend: GenerationBackend) -> Tuple[List[CandidateRecord], int]:
    tasks = load_plan(plan_path)["candidates"]
    records: List[CandidateRecord] = []
    cache_hits = 0
    with Cache(cache_path) as cache:
        for task in tasks:
            cached = cache.get_generation(task["generation_key"])
            if cached and cached.get("status") == CandidateStatus.SUCCEEDED.value:
                candidate = CandidateRecord.model_validate(cached)
                if candidate.video_path and Path(candidate.video_path).is_file():
                    records.append(candidate)
                    cache_hits += 1
                    continue
            running = CandidateRecord(
                candidate_id=task["candidate_id"],
                sample_id=task["sample_id"],
                generation_key=task["generation_key"],
                config=task["config"],
                status=CandidateStatus.RUNNING,
                artifact_dir=task["artifact_dir"],
                code_snapshot=task["code_snapshot"],
            )
            cache.put_generation(task["generation_key"], task["candidate_id"], "running", running.model_dump(mode="json"))
            try:
                candidate = backend.generate(task, experiment_dir)
            except Exception as error:  # preserve diagnostic state for resume
                candidate = running.model_copy(update={"status": CandidateStatus.FAILED, "error": str(error)})
            cache.put_generation(
                task["generation_key"], task["candidate_id"], candidate.status.value,
                candidate.model_dump(mode="json"), candidate.error,
            )
            records.append(candidate)
    manifest_path = experiment_dir / "candidates.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp = manifest_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps([record.model_dump(mode="json") for record in records], indent=2), encoding="utf-8")
    temp.replace(manifest_path)
    return records, cache_hits

