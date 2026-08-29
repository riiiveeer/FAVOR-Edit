"""Strict public records for the E2 Best-of-N pilot."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import SCHEMA_VERSION


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
