"""E1 strict Pydantic data models.

All models use ``extra="forbid"`` so unknown fields are rejected. Preference
values are limited to ``a``, ``b``, ``tie``, and ``uncertain``. ``IVEBench`` is
rejected wherever a cross-contamination risk exists.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Preference = Literal["a", "b", "tie", "uncertain"]
DisplayDirection = Literal["a_vs_b", "b_vs_a"]
SplitName = Literal["dev", "frozen-eval"]
TaskTypeName = Literal["attribute", "object", "local"]


def _contains_ivebench(value: Any) -> bool:
    return "ivebench" in str(value).lower()


class PairRecord(StrictModel):
    """A single unordered pair of candidates from the same sample."""

    pair_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    task_type: TaskTypeName
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    source_video_path: str
    source_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    mask_paths: List[str] = Field(default_factory=list)
    candidate_left_id: str
    candidate_left_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_left_path: str
    candidate_right_id: str
    candidate_right_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_right_path: str
    canonical_candidate_a_id: str
    canonical_candidate_b_id: str
    display_direction: DisplayDirection
    split: SplitName
    randomization_seed: int
    pair_schema_version: str
    identical_media: bool = False
    excluded_reason: Optional[str] = None

    @model_validator(mode="after")
    def _validate_pair(self) -> "PairRecord":
        if self.candidate_left_id == self.candidate_right_id:
            raise ValueError("pair must contain two distinct candidates")
        canonical = sorted([self.candidate_left_id, self.candidate_right_id])
        if [self.canonical_candidate_a_id, self.canonical_candidate_b_id] != canonical:
            raise ValueError("canonical A/B must be lexicographically sorted candidate IDs")
        for _, value in self.model_dump().items():
            if _contains_ivebench(value):
                raise ValueError("IVEBench is forbidden in PairRecord")
        return self


class HumanAnnotation(StrictModel):
    """A single annotator's screen-facing preference record."""

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
    started_at: str
    submitted_at: str
    annotation_schema_version: str


class JudgeRequest(StrictModel):
    """A single judge call, either absolute or pairwise."""

    request_id: str = Field(min_length=1)
    pair_id: Optional[str] = None
    candidate_id: Optional[str] = None
    method: str = Field(min_length=1)
    comparison_direction: Literal["absolute", "a_vs_b", "b_vs_a"]
    source_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_a_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_b_checksum: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    task_type: TaskTypeName
    media_packet_checksum: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_request(self) -> "JudgeRequest":
        if self.pair_id is None and self.candidate_id is None:
            raise ValueError("JudgeRequest requires pair_id or candidate_id")
        if self.comparison_direction == "absolute" and self.candidate_b_checksum is not None:
            raise ValueError("absolute request must not carry candidate_b_checksum")
        for _, value in self.model_dump().items():
            if _contains_ivebench(value):
                raise ValueError("IVEBench is forbidden in JudgeRequest")
        return self


class DimensionResult(StrictModel):
    preference: Preference
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""


class JudgeResult(StrictModel):
    """A parsed judge result plus the immutable raw response."""

    request_id: str = Field(min_length=1)
    judge_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["succeeded", "failed"]
    dimensions_a: Optional[Dict[str, DimensionResult]] = None
    dimensions_b: Optional[Dict[str, DimensionResult]] = None
    per_dimension_preference: Dict[str, Preference] = Field(default_factory=dict)
    overall_preference: Optional[Preference] = None
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    parse_error: Optional[str] = None
    runtime_seconds: float = Field(ge=0)
    peak_vram_mb: float = Field(ge=0)
    prompt_version: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    created_at: str


class AdjudicatedLabel(StrictModel):
    """Final ground truth for one pair after annotator adjudication."""

    pair_id: str = Field(min_length=1)
    annotator_ids: List[str] = Field(min_length=2)
    agreement: bool
    third_annotator_id: Optional[str] = None
    faithfulness_preference: Preference
    preservation_preference: Preference
    temporal_consistency_preference: Preference
    visual_quality_preference: Preference
    overall_preference: Preference
    human_tie: bool = False
    human_uncertain: bool = False
    adjudicated_at: str
    protocol_version: str


def validate_config(config: Path) -> Dict[str, Any]:
    """Load and validate the E1 pilot YAML config. Returns the parsed dict."""
    data = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pilot config must be a mapping")
    required = {"dataset", "split", "dev_samples", "frozen_eval_samples", "methods", "thresholds"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"pilot config missing keys: {sorted(missing)}")
    methods = data.get("methods", {})
    if not isinstance(methods, dict):
        raise ValueError("methods must be a mapping")
    total = sum(int(item.get("requests", 0)) for item in methods.values() if isinstance(item, dict))
    if total != 550:
        raise ValueError(f"total judge requests must be 550, got {total}")
    return data
