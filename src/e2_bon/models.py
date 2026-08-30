"""Strict public records for the E2 Best-of-N pilot."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import SCHEMA_VERSION
from e1_judge.models import MediaFileV2, RequestMediaV2


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class E2ConfigV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    dataset: Literal["DAVIS-2017"]
    split: Literal["train"]
    sample_ids: List[str] = Field(min_length=10, max_length=10)
    base_seeds: List[int] = Field(min_length=5, max_length=5)
    extension_seeds: List[int] = Field(min_length=3, max_length=3)
    n_values: List[int] = Field(min_length=4, max_length=4)
    subset_design: Literal["balanced-cyclic"]
    replicates: Literal[8]
    randomization_seed: int
    bootstrap_seed: int
    bootstrap_iterations: int = Field(ge=100)
    human_comparison: Literal["n4-vs-n1"]
    primary_annotators: Literal[2]
    third_party_adjudication: Literal[True]

    @model_validator(mode="after")
    def fixed_protocol(self) -> "E2ConfigV1":
        if len(set(self.sample_ids)) != 10:
            raise ValueError("E2 pilot requires 10 unique sample IDs")
        if self.base_seeds != [101, 202, 303, 404, 505]:
            raise ValueError("E2 base seeds must preserve the E0 five-seed pool")
        if self.extension_seeds != [606, 707, 808]:
            raise ValueError("E2 extension seeds must be 606/707/808")
        if set(self.base_seeds) & set(self.extension_seeds):
            raise ValueError("base and extension seeds must be disjoint")
        if self.n_values != [1, 2, 4, 8]:
            raise ValueError("E2 N values must be 1/2/4/8")
        return self

    @property
    def all_seeds(self) -> List[int]:
        return self.base_seeds + self.extension_seeds


class PoolCandidateV1(StrictModel):
    candidate_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    seed: int
    origin: Literal["e0", "extension"]
    generation_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_config: Dict[str, Any]
    input: Dict[str, Any]
    artifact_dir: str = Field(min_length=1)
    video_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frame_paths: List[str] = Field(min_length=16, max_length=16)
    frame_sha256: List[str] = Field(min_length=16, max_length=16)
    code_snapshot: str = Field(min_length=1)
    runtime_seconds: Optional[float] = Field(default=None, ge=0)
    peak_vram_mb: Optional[float] = Field(default=None, ge=0)


class CandidatePoolV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    e0_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    e0_candidates_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    e0_audit_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension_candidates_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension_audit_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pool_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_count: Literal[80]
    sample_count: Literal[10]
    candidates: List[PoolCandidateV1] = Field(min_length=80, max_length=80)

    @model_validator(mode="after")
    def fixed_counts(self) -> "CandidatePoolV1":
        ids = [item.candidate_id for item in self.candidates]
        if len(set(ids)) != 80:
            raise ValueError("candidate pool IDs must be unique")
        return self


class CandidateRefV1(StrictModel):
    candidate_id: str = Field(min_length=1)
    seed: int
    video_path: str = Field(min_length=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class E2PairV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    pair_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    task_type: Literal["attribute", "object", "local"]
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    source_video_path: str = Field(min_length=1)
    source_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_frame_paths: List[str] = Field(min_length=16, max_length=16)
    mask_frame_paths: List[str] = Field(default_factory=list)
    candidate_a: CandidateRefV1
    candidate_b: CandidateRefV1

    @model_validator(mode="after")
    def canonical_candidates(self) -> "E2PairV1":
        if self.candidate_a.candidate_id >= self.candidate_b.candidate_id:
            raise ValueError("E2 pair candidates must be lexicographically ordered")
        return self


class BonTrialV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    trial_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    replicate: int = Field(ge=0, le=7)
    candidate_order: List[str] = Field(min_length=8, max_length=8)
    subsets: Dict[str, List[str]]


E2Method = Literal["pairwise-swap-v1", "rubric-swap-v1"]
E2Stage = Literal["primary", "auxiliary-rubric"]


class E2JudgeRequestV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    stage: E2Stage
    split: Literal["e2-pilot"]
    request_id: str = Field(min_length=1)
    judge_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    task_type: Literal["attribute", "object", "local"]
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    method: E2Method
    comparison_direction: Literal["a_vs_b", "b_vs_a"]
    candidate_a_id: str = Field(min_length=1)
    candidate_b_id: str = Field(min_length=1)
    source: RequestMediaV2
    candidate_a: RequestMediaV2
    candidate_b: RequestMediaV2
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
    e1_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reward_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    code_snapshot: str = Field(min_length=1)


class E2JudgeResultV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    stage: E2Stage
    split: Literal["e2-pilot"]
    request_id: str = Field(min_length=1)
    judge_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    method: E2Method
    backend: Literal["mock", "command", "replay"]
    comparison_direction: Literal["a_vs_b", "b_vs_a"]
    candidate_a_id: str = Field(min_length=1)
    candidate_b_id: str = Field(min_length=1)
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
    e1_protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reward_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(min_length=1)


SelectionMethod = Literal["random", "primary-bradley-terry", "equal-linear", "pareto-maxmin"]
HumanPreference = Literal["a", "b", "tie", "uncertain"]
HumanOutcome = Literal["n4", "n1", "tie", "uncertain"]


class E2SelectionV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    trial_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    replicate: int = Field(ge=0, le=7)
    n: Literal[1, 2, 4, 8]
    method: SelectionMethod
    candidate_id: str = Field(min_length=1)
    candidate_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    utility: Optional[float] = None
    dimension_utilities: Dict[str, float] = Field(default_factory=dict)


class E2HumanComparisonV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    comparison_id: str = Field(min_length=1)
    trial_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    replicate: int = Field(ge=0, le=7)
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    n4_candidate_id: str = Field(min_length=1)
    n4_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    n1_candidate_id: str = Field(min_length=1)
    n1_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identical_selection: bool
    randomization_seed: int = Field(ge=0)

    @model_validator(mode="after")
    def checksum_identity(self) -> "E2HumanComparisonV1":
        identical = self.n4_video_sha256 == self.n1_video_sha256
        if self.identical_selection != identical:
            raise ValueError("identical_selection must exactly match candidate video checksums")
        return self


class E2SelectionBundleV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    experiment_id: Literal["E2-bon-pilot-v01"]
    measurement_mode: Literal["mock", "replay", "formal-command"]
    method_status: Dict[SelectionMethod, Literal["AVAILABLE", "NOT_APPLICABLE"]]
    selections: List[E2SelectionV1] = Field(min_length=640, max_length=1280)
    human_comparisons: List[E2HumanComparisonV1] = Field(min_length=80, max_length=80)
    primary_method: E2Method
    confidence_threshold: float = Field(ge=0, le=1)
    dependencies: Dict[str, Any]
    comparison_audit: Dict[str, Any]
    research_measurements: int = Field(ge=0)

    @model_validator(mode="after")
    def fixed_selection_counts(self) -> "E2SelectionBundleV1":
        selection_ids = [(item.trial_id, item.n, item.method) for item in self.selections]
        if len(selection_ids) != len(set(selection_ids)):
            raise ValueError("E2 selections must be unique by trial/N/method")
        comparison_ids = [item.comparison_id for item in self.human_comparisons]
        if len(set(comparison_ids)) != 80:
            raise ValueError("E2 human plan requires 80 unique comparisons")
        return self


class E2HumanAnnotationV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    annotation_id: str = Field(min_length=1)
    comparison_id: str = Field(min_length=1)
    annotator_id: str = Field(min_length=1)
    display_direction: Literal["a_vs_b", "b_vs_a"]
    faithfulness_preference: HumanPreference
    preservation_preference: HumanPreference
    temporal_consistency_preference: HumanPreference
    visual_quality_preference: HumanPreference
    overall_preference: HumanPreference
    confidence: float = Field(ge=0, le=1)
    notes: str = ""
    started_at: str = Field(min_length=1)
    submitted_at: str = Field(min_length=1)


class E2AdjudicatedComparisonV1(StrictModel):
    schema_version: Literal["1"] = SCHEMA_VERSION
    comparison_id: str = Field(min_length=1)
    trial_id: str = Field(min_length=1)
    sample_id: str = Field(min_length=1)
    replicate: int = Field(ge=0, le=7)
    n4_candidate_id: str = Field(min_length=1)
    n1_candidate_id: str = Field(min_length=1)
    identical_selection: bool
    automatic_tie: bool
    annotator_ids: List[str] = Field(default_factory=list, max_length=2)
    primary_agreement: Optional[bool] = None
    third_annotator_id: Optional[str] = None
    faithfulness_outcome: HumanOutcome
    preservation_outcome: HumanOutcome
    temporal_consistency_outcome: HumanOutcome
    visual_quality_outcome: HumanOutcome
    overall_outcome: HumanOutcome
    adjudicated_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def automatic_tie_contract(self) -> "E2AdjudicatedComparisonV1":
        if self.automatic_tie != self.identical_selection:
            raise ValueError("automatic_tie is reserved for identical selections")
        if self.automatic_tie:
            outcomes = (
                self.faithfulness_outcome, self.preservation_outcome,
                self.temporal_consistency_outcome, self.visual_quality_outcome,
                self.overall_outcome,
            )
            if any(value != "tie" for value in outcomes) or self.annotator_ids:
                raise ValueError("identical selections must be annotation-free ties")
        elif len(self.annotator_ids) != 2 or self.primary_agreement is None:
            raise ValueError("non-identical selections require two primary annotators")
        return self
