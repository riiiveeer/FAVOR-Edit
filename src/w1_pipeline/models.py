"""Validated public records for W1 inputs, generation, and reward."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskType(str, Enum):
    ATTRIBUTE = "attribute"
    OBJECT = "object"
    LOCAL = "local"


class SourceInput(StrictModel):
    sample_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    sequence: str
    task_type: TaskType
    instruction: str = Field(min_length=1)
    target_caption: str = Field(min_length=1)


class ExperimentSpec(StrictModel):
    dataset: Literal["DAVIS-2017"]
    split: Literal["train"]
    year: Literal[2016, 2017] = 2017
    resolution: Literal["480p"] = "480p"
    seeds: List[int]
    inputs: List[SourceInput]

    @model_validator(mode="after")
    def unique_values(self) -> "ExperimentSpec":
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("seeds must be unique")
        ids = [item.sample_id for item in self.inputs]
        sequences = [item.sequence for item in self.inputs]
        if len(ids) != len(set(ids)):
            raise ValueError("sample_id values must be unique")
        if len(sequences) != len(set(sequences)):
            raise ValueError("sequence values must be unique")
        return self


class CropParameters(StrictModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    side: int = Field(gt=0)
    output_size: int = Field(default=512, gt=0)
    window_start: int = Field(ge=0)
    source_window_length: Literal[48] = 48
    stride: Literal[3] = 3


class InputRecord(StrictModel):
    sample_id: str
    dataset: Literal["DAVIS-2017"]
    split: Literal["train"]
    sequence: str
    task_type: TaskType
    instruction: str
    target_caption: str
    source_frame_paths: List[str] = Field(min_length=16, max_length=16)
    mask_frame_paths: List[str] = Field(min_length=16, max_length=16)
    source_video_path: str
    source_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    mask_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    video_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    crop: CropParameters


class GenerationConfig(StrictModel):
    backend: Literal["mock", "anyv2v"] = "anyv2v"
    model: str = "ali-vilab/i2vgen-xl"
    model_commit: str
    anyv2v_commit: str
    image_editor: str = "timbrooks/instruct-pix2pix"
    seed: int
    width: Literal[512] = 512
    height: Literal[512] = 512
    n_frames: Literal[16] = 16
    fps: Literal[8] = 8
    inversion_steps: Literal[500] = 500
    pnp_steps: Literal[50] = 50
    cfg: float = 9.0
    ddim_init_latents_t_idx: int = 0
    pnp_f_t: float = 0.2
    pnp_spatial_attn_t: float = 0.2
    pnp_temp_attn_t: float = 0.5
    random_ratio: float = 0.0


class CandidateStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CandidateRecord(StrictModel):
    candidate_id: str
    sample_id: str
    generation_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    config: GenerationConfig
    status: CandidateStatus
    artifact_dir: str
    video_path: Optional[str] = None
    frame_paths: List[str] = Field(default_factory=list)
    video_checksum: Optional[str] = None
    frame_checksums: List[str] = Field(default_factory=list)
    runtime_seconds: Optional[float] = None
    peak_vram_mb: Optional[float] = None
    code_snapshot: str
    error: Optional[str] = None


class RewardDimensions(StrictModel):
    faithfulness: float = Field(ge=0, le=1)
    preservation: float = Field(ge=0, le=1)
    temporal_consistency: float = Field(ge=0, le=1)
    visual_quality: float = Field(ge=0, le=1)


class RewardRequest(StrictModel):
    request_id: str
    candidate_a_checksum: str
    candidate_b_checksum: Optional[str] = None
    instruction: str
    target_caption: str
    backend: Literal["mock", "replay"]
    model: str
    prompt_version: str
    comparison_direction: Literal["absolute", "a_vs_b", "b_vs_a"] = "absolute"


class RewardResult(StrictModel):
    request_id: str
    reward_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    dimensions_a: RewardDimensions
    dimensions_b: Optional[RewardDimensions] = None
    preference: Literal["a", "b", "tie", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    raw_response: Dict[str, Any]
    prompt_version: str

