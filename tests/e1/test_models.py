import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from e1_judge.models import CandidateRefV2, PairRecordV2, SourceRefV2, load_runtime_config, validate_config
from e1_judge.prompts import load_prompt, parse_response, render_prompt


def valid_pair():
    return {
        "schema_version": "2", "pair_id": "sample-p01", "sample_id": "sample",
        "task_type": "attribute", "instruction": "make white", "target_caption": "white object",
        "source": SourceRefV2(sample_id="sample", video_path="source.mp4", video_sha256="a" * 64),
        "candidate_a": CandidateRefV2(candidate_id="sample-s101", video_path="a.mp4", video_sha256="b" * 64),
        "candidate_b": CandidateRefV2(candidate_id="sample-s202", video_path="b.mp4", video_sha256="c" * 64),
        "split": "dev", "randomization_seed": 7,
    }


def test_pair_v2_strict_and_canonical():
    pair = PairRecordV2.model_validate(valid_pair())
    assert pair.schema_version == "2"
    payload = valid_pair()
    payload["candidate_a"], payload["candidate_b"] = payload["candidate_b"], payload["candidate_a"]
    with pytest.raises(ValidationError, match="lexicographically"):
        PairRecordV2.model_validate(payload)


def test_pair_rejects_unknown_and_ivebench():
    payload = valid_pair()
    payload["unknown"] = True
    with pytest.raises(ValidationError):
        PairRecordV2.model_validate(payload)
    payload = valid_pair()
    payload["instruction"] = "IVEBench prompt"
    with pytest.raises(ValidationError, match="IVEBench"):
        PairRecordV2.model_validate(payload)


def test_config_and_runtime_v2_validate():
    root = Path(__file__).parents[2]
    data = validate_config(root / "configs" / "e1" / "pilot.yaml")
    assert data["total_requests"] == 550
    runtime = load_runtime_config(root / "configs" / "e1" / "runtime-mock.yaml")
    assert runtime.backend == "mock"


def test_prompt_render_and_strict_parse():
    path = Path(__file__).parents[2] / "configs" / "e1" / "prompt-rubric-swap-v1.yaml"
    spec, checksum = load_prompt(path)
    rendered = render_prompt(spec, "turn the dog into a tiger", "a tiger")
    assert "turn the dog" in rendered and len(checksum) == 64
    payload = {
        dimension: {"preference": "a", "confidence": 0.9, "evidence": "visible"}
        for dimension in ("faithfulness", "preservation", "temporal_consistency", "visual_quality")
    }
    payload.update({"overall_preference": "a", "overall_confidence": 0.9, "failure_tags_a": [], "failure_tags_b": []})
    parsed = parse_response("rubric-swap-v1", json.dumps(payload))
    assert parsed["overall_preference"] == "a"
    with pytest.raises(ValueError, match="strict JSON"):
        parse_response("rubric-swap-v1", "```json\n{}\n```")


def test_absolute_parse_rejects_out_of_range():
    payload = {
        "scores": {"faithfulness": 5, "preservation": 2, "temporal_consistency": 2, "visual_quality": 2},
        "overall_score": 2, "confidence": 0.8, "evidence": "",
    }
    with pytest.raises(ValidationError):
        parse_response("absolute-v1", json.dumps(payload))
