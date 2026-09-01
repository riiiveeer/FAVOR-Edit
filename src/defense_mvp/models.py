"""Strict protocol models for the independent Defense MVP."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from w1_pipeline.models import CropParameters, GenerationConfig


PRIMARY_SAMPLE_IDS = [
    "bear-white",
    "bus-red",
    "elephant-pink",
    "classic-car-blue",
    "hiker-backpack",
    "rider-helmet",
    "car-headlights",
]
QUALITATIVE_SAMPLE_IDS = ["dog-tiger", "horse-zebra", "mallard-swan"]
SEEDS = [101, 202, 303, 404, 505]
N_VALUES = [1, 2, 4]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColorRuleV1(StrictModel):
    color_name: Literal["white", "red", "pink", "blue", "yellow"]
    hue_ranges: List[Tuple[float, float]] = Field(min_length=1)
    saturation_min: float = Field(ge=0.0, le=1.0)
    saturation_max: float = Field(ge=0.0, le=1.0)
    value_min: float = Field(ge=0.0, le=1.0)
    value_max: float = Field(ge=0.0, le=1.0)
    require_new_color: bool

    @model_validator(mode="after")
    def valid_ranges(self) -> "ColorRuleV1":
        if self.saturation_min > self.saturation_max:
            raise ValueError("saturation_min must not exceed saturation_max")
        if self.value_min > self.value_max:
            raise ValueError("value_min must not exceed value_max")
        for low, high in self.hue_ranges:
            if not 0.0 <= low <= high <= 1.0:
                raise ValueError("hue ranges must satisfy 0 <= low <= high <= 1")
        return self


class DefenseConfigV1(StrictModel):
    schema_version: Literal["1"]
    experiment_id: Literal["DEFENSE-MVP-v01"]
    dataset: Literal["DAVIS-2017"]
    split: Literal["train"]
    primary_sample_ids: List[str]
    qualitative_sample_ids: List[str]
    seeds: List[int]
    n_values: List[int]
    replicates: Literal[5]
    n4_vs_n1_replicates: Literal[4]
    pareto_vs_linear_replicates: Literal[2]
    randomization_seed: Literal[20260901]
    bootstrap_seed: Literal[20260901]
    bootstrap_iterations: Literal[2000]
    mask_threshold: float = Field(gt=0.0, lt=1.0)
    min_mask_fraction: float = Field(gt=0.0, lt=1.0)
    max_mask_fraction: float = Field(gt=0.0, le=1.0)
    color_rules: Dict[str, ColorRuleV1]

    @model_validator(mode="after")
    def fixed_protocol(self) -> "DefenseConfigV1":
        if self.primary_sample_ids != PRIMARY_SAMPLE_IDS:
            raise ValueError("primary sample IDs must match the fixed seven-task protocol")
        if self.qualitative_sample_ids != QUALITATIVE_SAMPLE_IDS:
            raise ValueError("qualitative sample IDs must match the fixed three-task boundary")
        if self.seeds != SEEDS:
            raise ValueError("seeds must be 101/202/303/404/505")
        if self.n_values != N_VALUES:
            raise ValueError("N values must be 1/2/4")
        if set(self.color_rules) != set(PRIMARY_SAMPLE_IDS):
            raise ValueError("color rules must cover exactly the seven primary samples")
        if self.min_mask_fraction >= self.max_mask_fraction:
            raise ValueError("min_mask_fraction must be below max_mask_fraction")
        return self

    @property
    def sample_ids(self) -> List[str]:
        return self.primary_sample_ids + self.qualitative_sample_ids

    @property
    def candidate_count(self) -> int:
        return len(self.sample_ids) * len(self.seeds)

    @property
    def quantitative_candidate_count(self) -> int:
        return len(self.primary_sample_ids) * len(self.seeds)

    @property
    def qualitative_candidate_count(self) -> int:
        return len(self.qualitative_sample_ids) * len(self.seeds)

    @property
    def comparisons_per_annotator(self) -> int:
        return len(self.primary_sample_ids) * (
            self.n4_vs_n1_replicates + self.pareto_vs_linear_replicates
        )


def validate_relative_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("package paths must use POSIX separators")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe package relative path: {value!r}")
    if path.as_posix() != value:
        raise ValueError(f"package path is not canonical POSIX: {value!r}")
    return value


class PackageFileV1(StrictModel):
    relative_path: str
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

    @model_validator(mode="after")
    def safe_path(self) -> "PackageFileV1":
        self.relative_path = validate_relative_path(self.relative_path)
        return self


class MediaRefV1(StrictModel):
    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def safe_path(self) -> "MediaRefV1":
        self.relative_path = validate_relative_path(self.relative_path)
        return self


class FrameSetV1(StrictModel):
    relative_paths: List[str] = Field(min_length=16, max_length=16)
    sha256: List[str] = Field(min_length=16, max_length=16)
    combined_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def safe_unique_paths(self) -> "FrameSetV1":
        self.relative_paths = [validate_relative_path(value) for value in self.relative_paths]
        if len(set(self.relative_paths)) != 16:
            raise ValueError("frame-set paths must be unique")
        if any(len(value) != 64 or any(char not in "0123456789abcdef" for char in value) for value in self.sha256):
            raise ValueError("frame-set sha256 values must be lowercase 64-hex")
        return self


class PackageSampleV1(StrictModel):
    sample_id: str
    sequence: str
    task_type: Literal["attribute", "object", "local"]
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)
    source_video: MediaRefV1
    source_frames: FrameSetV1
    masks: FrameSetV1
    crop: CropParameters


class PackageCandidateV1(StrictModel):
    candidate_id: str
    sample_id: str
    seed: int
    status: Literal["succeeded"]
    video: MediaRefV1
    frames: FrameSetV1
    generation_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    config: GenerationConfig
    runtime_seconds: float = Field(ge=0.0)
    peak_vram_mb: Optional[float] = Field(default=None, ge=0.0)
    code_snapshot: str = Field(min_length=1)

    @model_validator(mode="after")
    def matching_seed_and_backend(self) -> "PackageCandidateV1":
        if self.seed != self.config.seed:
            raise ValueError("candidate seed must match generation config")
        if self.config.backend != "anyv2v":
            raise ValueError("Defense MVP accepts only real AnyV2V E0 candidates")
        return self


class PackageSourceIdentityV1(StrictModel):
    e0_root: str = Field(min_length=1)
    audit_root: Optional[str] = None
    repo_head: str = Field(min_length=1)
    repo_status: str
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidates_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    audit_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    e0_code_snapshots: List[str] = Field(min_length=1)
    model_commits: List[str] = Field(min_length=1)
    anyv2v_commits: List[str] = Field(min_length=1)


class PackageCountsV1(StrictModel):
    samples: Literal[10]
    candidates: Literal[50]
    mp4: Literal[60]
    source_frames: Literal[160]
    masks: Literal[160]
    candidate_frames: Literal[800]
    files: int = Field(gt=0)
    total_bytes: int = Field(gt=0)


class PackageManifestV1(StrictModel):
    schema_version: Literal["1"]
    package_id: Literal["DEFENSE-MVP-E0-HANDOFF-v01"]
    created_at: str = Field(min_length=1)
    created_by: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    status: Literal["passed"]
    source: PackageSourceIdentityV1
    counts: PackageCountsV1
    samples: List[PackageSampleV1] = Field(min_length=10, max_length=10)
    candidates: List[PackageCandidateV1] = Field(min_length=50, max_length=50)
    files: List[PackageFileV1] = Field(min_length=1)
    warnings: List[str] = Field(default_factory=list)
    missing_optional_artifacts: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fixed_delivery_identity(self) -> "PackageManifestV1":
        sample_ids = [item.sample_id for item in self.samples]
        if sample_ids != PRIMARY_SAMPLE_IDS + QUALITATIVE_SAMPLE_IDS:
            raise ValueError("package samples must follow the fixed 7+3 order")
        candidate_pairs = [(item.sample_id, item.seed) for item in self.candidates]
        expected_pairs = [(sample_id, seed) for sample_id in sample_ids for seed in SEEDS]
        if candidate_pairs != expected_pairs:
            raise ValueError("package candidates must follow the fixed sample/seed matrix")
        if len({item.candidate_id for item in self.candidates}) != 50:
            raise ValueError("package candidate IDs must be unique")
        file_paths = [item.relative_path for item in self.files]
        if len(file_paths) != len(set(file_paths)):
            raise ValueError("package file entries must be unique")
        if self.counts.files != len(self.files):
            raise ValueError("package file count does not match file entries")
        if self.counts.total_bytes != sum(item.size_bytes for item in self.files):
            raise ValueError("package byte count does not match file entries")
        return self
