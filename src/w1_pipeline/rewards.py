"""Non-research mock/replay reward execution and caching."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .cache import Cache
from .hashing import canonical_sha256
from .models import CandidateRecord, RewardDimensions, RewardRequest, RewardResult


def reward_key(request: RewardRequest) -> str:
    return canonical_sha256(request.model_dump(mode="json"))


def build_reward_requests(candidates_path: Path, backend: str, model: str, prompt_version: str) -> List[RewardRequest]:
    candidates = [CandidateRecord.model_validate(value) for value in json.loads(candidates_path.read_text(encoding="utf-8"))]
    requests = []
    for candidate in candidates:
        if candidate.status.value != "succeeded" or not candidate.video_checksum:
            continue
        requests.append(
            RewardRequest(
                request_id=f"reward-{candidate.candidate_id}", candidate_a_checksum=candidate.video_checksum,
                instruction=candidate.candidate_id, target_caption=candidate.candidate_id,
                backend=backend, model=model, prompt_version=prompt_version,
            )
        )
    return requests


def _mock_result(request: RewardRequest, key: str) -> RewardResult:
    # Deterministic schema exercise only; these values are never research measurements.
    digest = bytes.fromhex(key)
    values = [round(digest[index] / 255.0, 6) for index in range(4)]
    dimensions = RewardDimensions(
        faithfulness=values[0], preservation=values[1], temporal_consistency=values[2], visual_quality=values[3]
    )
    return RewardResult(
        request_id=request.request_id, reward_key=key, dimensions_a=dimensions,
        preference="uncertain", confidence=0.0,
        raw_response={"mock": True, "research_result": False, "note": "schema/cache validation only"},
        prompt_version=request.prompt_version,
    )


def _load_replay(path: Path) -> Dict[str, dict]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(values, list):
        return {value["reward_key"]: value for value in values}
    return values


def run_rewards(
    candidates_path: Path, cache_path: Path, backend: str, model: str, prompt_version: str,
    output_path: Path, replay_path: Optional[Path] = None,
) -> Tuple[List[RewardResult], int]:
    requests = build_reward_requests(candidates_path, backend, model, prompt_version)
    replay = _load_replay(replay_path) if replay_path else {}
    results, hits = [], 0
    with Cache(cache_path) as cache:
        for request in requests:
            key = reward_key(request)
            cached = cache.get_reward(key)
            if cached:
                results.append(RewardResult.model_validate(cached))
                hits += 1
                continue
            if backend == "mock":
                result = _mock_result(request, key)
            elif backend == "replay":
                if key not in replay:
                    raise ValueError(f"replay result missing for reward key {key}")
                result = RewardResult.model_validate(replay[key])
                if result.reward_key != key:
                    raise ValueError("replay reward key mismatch")
            else:
                raise ValueError("W1 permits only mock or replay reward backends")
            cache.put_reward(key, request.request_id, "succeeded", result.model_dump(mode="json"))
            results.append(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    temp.write_text(json.dumps([result.model_dump(mode="json") for result in results], indent=2), encoding="utf-8")
    temp.replace(output_path)
    return results, hits

