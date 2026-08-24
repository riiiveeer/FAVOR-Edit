"""Deterministic mock backend (not a research measurement)."""

import json
from pathlib import Path

from .base import JudgeBackend


class MockBackend(JudgeBackend):
    name = "mock"

    def run(self, request_path: Path, output_path: Path) -> None:
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        result = {
            "request_id": request["request_id"],
            "judge_key": request.get("judge_key", "0" * 64),
            "status": "succeeded",
            "overall_preference": "uncertain",
            "confidence": 0.0,
            "per_dimension_preference": {
                "faithfulness": "uncertain",
                "preservation": "uncertain",
                "temporal_consistency": "uncertain",
                "visual_quality": "uncertain",
            },
            "evidence": "",
            "raw_response": {"research_result": False},
            "parse_error": None,
            "runtime_seconds": 0.0,
            "peak_vram_mb": 0.0,
            "prompt_version": request.get("prompt_version", "mock"),
            "model_revision": request.get("model_revision", "mock"),
            "created_at": "",
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding="utf-8")
