"""Deterministic batch mock that emits parseable non-research envelopes."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import RuntimeConfigV2
from .base import JudgeBackend


def _mock_payload(method: str) -> dict:
    if method == "absolute-v1":
        return {
            "scores": {
                "faithfulness": 2, "preservation": 2,
                "temporal_consistency": 2, "visual_quality": 2,
            },
            "overall_score": 2, "confidence": 0, "evidence": "mock",
        }
    if method in {"pairwise-single-v1", "pairwise-swap-v1"}:
        return {"overall_preference": "uncertain", "confidence": 0, "evidence": "mock"}
    dimension = {"preference": "uncertain", "confidence": 0, "evidence": "mock"}
    return {
        "faithfulness": dimension, "preservation": dimension,
        "temporal_consistency": dimension, "visual_quality": dimension,
        "overall_preference": "uncertain", "overall_confidence": 0,
        "failure_tags_a": [], "failure_tags_b": [],
    }


class MockBackend(JudgeBackend):
    name = "mock"

    def run_batch(self, requests_path: Path, output_dir: Path, runtime: RuntimeConfigV2) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for line in Path(requests_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            request = json.loads(line)
            envelope = {
                "schema_version": "2",
                "request_id": request["request_id"],
                "judge_key": request["judge_key"],
                "status": "succeeded",
                "raw_text": json.dumps(_mock_payload(request["method"]), sort_keys=True),
                "raw_response": {"research_result": False, "backend": "mock"},
                "runtime_seconds": 0.0,
                "peak_vram_mb": 0.0,
            }
            target = output_dir / f"{request['judge_key']}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
            temporary.replace(target)
