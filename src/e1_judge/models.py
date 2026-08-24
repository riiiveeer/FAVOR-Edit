"""Strict schema-v2 models for the E1 judge reliability pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2"
DIMENSIONS = ("faithfulness", "preservation", "temporal_consistency", "visual_quality")

Preference = Literal["a", "b", "tie", "uncertain"]
DisplayDirection = Literal["a_vs_b", "b_vs_a"]
SplitName = Literal["dev", "frozen-eval"]
TaskTypeName = Literal["attribute", "object", "local"]
JudgeMethod = Literal["absolute-v1", "pairwise-single-v1", "pairwise-swap-v1", "rubric-swap-v1"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _contains_ivebench(value: Any) -> bool:
    return "ivebench" in str(value).lower()


def _reject_ivebench(model: BaseModel) -> None:
    if _contains_ivebench(model.model_dump(mode="json")):
        raise ValueError("IVEBench is forbidden in E1 development records")


class CandidateRefV2(StrictModel):
    candidate_id: str = Field(min_length=1)
    video_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceRefV2(StrictModel):
    sample_id: str = Field(min_length=1)
    video_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mask_frame_paths: List[str] = Field(default_factory=list)


class PairRecordV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    pair_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    task_type: TaskTypeName
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    source: SourceRefV2
    candidate_a: CandidateRefV2
    candidate_b: CandidateRefV2
    split: SplitName
    randomization_seed: int
    identical_media: bool = False
    excluded_reason: Optional[str] = None

    @model_validator(mode="after")
    def _validate_pair(self) -> "PairRecordV2":
        if self.source.sample_id != self.sample_id:
            raise ValueError("source sample_id must match pair sample_id")
        if self.candidate_a.candidate_id >= self.candidate_b.candidate_id:
            raise ValueError("candidate A/B must be unique and lexicographically ordered")
        _reject_ivebench(self)
        return self


class MediaFileV2(StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MediaAssetV2(StrictModel):
    asset_id: str = Field(min_length=1)
    original_path: str = Field(min_length=1)
    original_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    video: MediaFileV2
    frames: List[MediaFileV2] = Field(min_length=16, max_length=16)
    contact_sheet: MediaFileV2


class PairPacketV2(StrictModel):
    pair_id: str = Field(min_length=1)
    source_asset_id: str = Field(min_length=1)
    candidate_a_asset_id: str = Field(min_length=1)
    candidate_b_asset_id: str = Field(min_length=1)
    mask_overlay: Optional[MediaFileV2] = None
    metadata_path: str = Field(min_length=1)
    packet_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")


class MediaManifestV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    sources: Dict[str, MediaAssetV2]
    candidates: Dict[str, MediaAssetV2]
    pairs: Dict[str, PairPacketV2]


class RequestMediaV2(StrictModel):
    asset_id: str = Field(min_length=1)
    video_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frame_paths: List[str] = Field(min_length=16, max_length=16)
    frame_sha256: List[str] = Field(min_length=16, max_length=16)
    contact_sheet_path: str = Field(min_length=1)
    contact_sheet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ModelIdentityV2(StrictModel):
    name: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    local_path: str = Field(min_length=1)


class AdapterConfigV2(StrictModel):
    python: Optional[str] = None
    script: Optional[str] = None
    timeout_seconds: int = Field(default=0, ge=0)
    replay_source: Optional[str] = None


class RuntimeConfigV2(StrictModel):
    runtime_schema_version: Literal["2"] = SCHEMA_VERSION
    backend: Literal["mock", "command", "replay"]
    model: ModelIdentityV2
    adapter: AdapterConfigV2 = Field(default_factory=AdapterConfigV2)

    @model_validator(mode="after")
    def _validate_backend(self) -> "RuntimeConfigV2":
        if self.backend == "command" and (not self.adapter.python or not self.adapter.script):
            raise ValueError("command runtime requires adapter.python and adapter.script")
        if self.backend == "replay" and not self.adapter.replay_source:
            raise ValueError("replay runtime requires adapter.replay_source")
        return self


class PromptSpecV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    prompt_version: str = Field(min_length=1)
    method: JudgeMethod
    parser_version: str = Field(min_length=1)
    status: Literal["development", "frozen"]
    created_from_commit: str = Field(min_length=7)
    visual_roles: List[str] = Field(min_length=2)
    system_prompt: str = Field(min_length=1)
    user_template: str = Field(min_length=1)
    output_schema: Dict[str, Any]
    generation_parameters: Dict[str, Any]


class JudgeRequestV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    request_id: str = Field(min_length=1)
    judge_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: Optional[str] = None
    candidate_id: Optional[str] = None
    sample_id: str = Field(min_length=1)
    split: SplitName
    task_type: TaskTypeName
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    method: JudgeMethod
    comparison_direction: Literal["absolute", "a_vs_b", "b_vs_a"]
    candidate_a_id: str = Field(min_length=1)
    candidate_b_id: Optional[str] = None
    source: RequestMediaV2
    candidate_a: RequestMediaV2
    candidate_b: Optional[RequestMediaV2] = None
    mask_overlay: Optional[MediaFileV2] = None
    media_packet_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend: Literal["mock", "command", "replay"]
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    model_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_version: str = Field(min_length=1)
    prompt_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    rendered_prompt: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    generation_parameters: Dict[str, Any]
    runtime_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_protocol_fingerprint: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    code_snapshot: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_request(self) -> "JudgeRequestV2":
        is_absolute = self.comparison_direction == "absolute"
        if is_absolute:
            if self.candidate_id is None or self.pair_id is not None:
                raise ValueError("absolute request requires candidate_id and no pair_id")
            if self.candidate_b is not None or self.candidate_b_id is not None:
                raise ValueError("absolute request must not include candidate B")
        else:
            if self.pair_id is None or self.candidate_b is None or self.candidate_b_id is None:
                raise ValueError("pairwise request requires pair_id and candidate B")
        _reject_ivebench(self)
        return self


class DimensionPreferenceV2(StrictModel):
    preference: Preference
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""


class AbsoluteScoresV2(StrictModel):
    faithfulness: float = Field(ge=0, le=4)
    preservation: float = Field(ge=0, le=4)
    temporal_consistency: float = Field(ge=0, le=4)
    visual_quality: float = Field(ge=0, le=4)


class AbsolutePayloadV2(StrictModel):
    scores: AbsoluteScoresV2
    overall_score: float = Field(ge=0, le=4)
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""


class PairwisePayloadV2(StrictModel):
    overall_preference: Preference
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""


class RubricPayloadV2(StrictModel):
    faithfulness: DimensionPreferenceV2
    preservation: DimensionPreferenceV2
    temporal_consistency: DimensionPreferenceV2
    visual_quality: DimensionPreferenceV2
    overall_preference: Preference
    overall_confidence: float = Field(ge=0, le=1)
    failure_tags_a: List[str] = Field(default_factory=list)
    failure_tags_b: List[str] = Field(default_factory=list)


class JudgeResultV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    request_id: str = Field(min_length=1)
    judge_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: Optional[str] = None
    candidate_id: Optional[str] = None
    sample_id: str = Field(min_length=1)
    split: SplitName
    method: JudgeMethod
    comparison_direction: Literal["absolute", "a_vs_b", "b_vs_a"]
    candidate_a_id: str = Field(min_length=1)
    candidate_b_id: Optional[str] = None
    status: Literal["succeeded", "failed"]
    parsed: Optional[Dict[str, Any]] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    parse_error: Optional[str] = None
    runtime_seconds: float = Field(ge=0)
    peak_vram_mb: float = Field(ge=0)
    prompt_version: str = Field(min_length=1)
    prompt_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    parser_version: str = Field(min_length=1)
    generation_parameters: Dict[str, Any]
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    model_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_protocol_fingerprint: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(min_length=1)


class HumanAnnotationV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    annotation_id: str = Field(min_length=1)
    pair_id: str = Field(min_length=1)
    annotator_id: str = Field(min_length=1)
    display_direction: DisplayDirection
    faithfulness_preference: Preference
    preservation_preference: Preference
    temporal_consistency_preference: Preference
    visual_quality_preference: Preference
    overall_preference: Preference
    confidence: float = Field(ge=0, le=1)
    failure_tags_a: List[str] = Field(default_factory=list)
    failure_tags_b: List[str] = Field(default_factory=list)
    notes: str = ""
    started_at: str = Field(min_length=1)
    submitted_at: str = Field(min_length=1)


class AdjudicatedLabelV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    pair_id: str = Field(min_length=1)
    annotator_ids: List[str] = Field(min_length=2, max_length=2)
    agreement: bool
    third_annotator_id: Optional[str] = None
    faithfulness_preference: Preference
    preservation_preference: Preference
    temporal_consistency_preference: Preference
    visual_quality_preference: Preference
    overall_preference: Preference
    human_tie: bool
    human_uncertain: bool
    adjudicated_at: str = Field(min_length=1)
    protocol_version: Literal["2"] = SCHEMA_VERSION


class FrozenProtocolV2(StrictModel):
    schema_version: Literal["2"] = SCHEMA_VERSION
    created_at: str = Field(min_length=1)
    code_snapshot: str = Field(min_length=1)
    selected_method: Literal["pairwise-swap-v1", "rubric-swap-v1"]
    confidence_threshold: float = Field(ge=0, le=1)
    absolute_delta_threshold: float = Field(ge=0, le=4)
    config_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_checksums: Dict[str, str]
    plan_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def load_runtime_config(path: Path) -> RuntimeConfigV2:
    return RuntimeConfigV2.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def validate_config(config: Path) -> Dict[str, Any]:
    """Validate the v2 pilot protocol and its four prompt specifications."""
    data = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pilot config must be a mapping")
    required = {
        "protocol_schema_version", "dataset", "split", "dev_samples", "frozen_eval_samples",
        "methods", "thresholds", "threshold_grids", "randomization_seed",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"pilot config missing keys: {sorted(missing)}")
    if str(data["protocol_schema_version"]) != SCHEMA_VERSION:
        raise ValueError("pilot protocol_schema_version must be 2")
    if _contains_ivebench(data):
        raise ValueError("IVEBench is forbidden in E1 pilot config")
    methods = data.get("methods")
    expected_methods = {"absolute-v1", "pairwise-single-v1", "pairwise-swap-v1", "rubric-swap-v1"}
    if not isinstance(methods, dict) or set(methods) != expected_methods:
        raise ValueError("pilot config must define exactly the four E1 judge methods")
    total = sum(int(item.get("requests", 0)) for item in methods.values())
    if total != 550 or int(data.get("total_requests", 0)) != 550:
        raise ValueError(f"total judge requests must be 550, got {total}")
    from .prompts import load_prompt

    for method, method_cfg in methods.items():
        prompt_path = Path(config).parent / str(method_cfg["prompt"])
        spec, _ = load_prompt(prompt_path)
        if spec.method != method:
            raise ValueError(f"prompt {prompt_path} declares {spec.method}, expected {method}")
    return data
