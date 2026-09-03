"""Defense-only, versioned blind annotation records; never E1/E2 records."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import MediaRefV1

PROTOCOL = "defense-blind-v1"
FIELDS = ("overall", "faithfulness", "preservation", "temporal_consistency", "visual_quality")
ANNOTATORS = ("annotator-a", "annotator-b")
FAMILIES = ("proposed-n4-vs-n1", "proposed-vs-linear-n4")
CONFIG = {
    "protocol": PROTOCOL, "seed": 20260901, "fields": list(FIELDS),
    "choices": ["A", "B", "tie", "uncertain"],
    "confidence": [0.0, 0.25, 0.5, 0.75, 1.0], "notes_limit": 1000,
    "direction": "family-balanced-sha256-v1", "order": "independent-sha256-v1",
    "timing": "current-view-server-elapsed-not-active-labor",
    "presentation": "lossless-vp9-yuv420p-v1",
}
Mode = Literal["formal", "practice"]
Annotator = Literal["annotator-a", "annotator-b"]
Choice = Literal["A", "B", "tie", "uncertain"]
CanonicalChoice = Literal["X", "Y", "tie", "uncertain"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class CandidateSide(Strict):
    role: str
    candidate_id: str
    video: MediaRefV1


class Comparison(Strict):
    schema_version: Literal["1"]
    comparison_id: str
    family: Literal["proposed-n4-vs-n1", "proposed-vs-linear-n4"]
    trial_id: str
    sample_id: str
    replicate: int = Field(ge=1, le=4)
    instruction: str = Field(min_length=1)
    target_caption: str
    source_video: MediaRefV1
    candidate_x: CandidateSide
    candidate_y: CandidateSide
    identical_selection: bool


class Display(Strict):
    comparison_id: str
    position: int = Field(ge=1)
    x_as: Literal["A", "B"]


class Answers(Strict):
    overall: Choice
    faithfulness: Choice
    preservation: Choice
    temporal_consistency: Choice
    visual_quality: Choice
    confidence: float = Field(ge=0, le=1)
    notes: str = Field(default="", max_length=1000)

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_code(cls, value):
        if type(value) not in (float, int) or value not in CONFIG["confidence"]:
            raise ValueError("confidence must use a frozen code")
        return float(value)


class DraftAnswers(Strict):
    overall: Optional[Choice] = None
    faithfulness: Optional[Choice] = None
    preservation: Optional[Choice] = None
    temporal_consistency: Optional[Choice] = None
    visual_quality: Optional[Choice] = None
    confidence: Optional[float] = None
    notes: str = Field(default="", max_length=1000)

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_code(cls, value):
        return None if value is None else Answers.confidence_code(value)


class Session(Strict):
    protocol: Literal["defense-blind-v1"]
    mode: Mode
    annotator_id: Annotator
    bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    created_at: str


class Annotation(Strict):
    protocol: Literal["defense-blind-v1"]
    mode: Mode
    source: Literal["human", "practice"]
    status: Literal["confirmed"]
    session_id: str
    annotator_id: Annotator
    bundle_sha256: str
    protocol_sha256: str
    comparison_id: str
    position: int = Field(ge=1)
    x_as: Literal["A", "B"]
    screen: Answers
    canonical: Dict[str, CanonicalChoice]
    media: Dict[str, MediaRefV1]
    presentation_media: Dict[str, MediaRefV1]
    presentation_mode: Literal["lossless-vp9-yuv420p-v1", "fixture-native-v1"]
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    view_started_at: str
    submitted_at: str
    current_view_elapsed_seconds: float = Field(ge=0)
    timing: Literal["current-view-server-elapsed-not-active-labor"]


class Draft(Strict):
    session_id: str
    bundle_sha256: str
    comparison_id: str
    revision: int = Field(ge=1)
    answers: DraftAnswers
    updated_at: str


class AutomaticTie(Strict):
    comparison_id: str
    source: Literal["automatic_tie"]
    reason: Literal["media_identity"]
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["tie"]


class Coverage(Strict):
    protocol: Literal["defense-blind-v1"]
    mode: Mode
    bundle_sha256: str
    annotator_id: Annotator
    status: Literal["incomplete", "complete"]
    human_comparison_ids: List[str]
    automatic_comparison_ids: List[str]
    missing_comparison_ids: List[str]
    covered: int = Field(ge=0)
    total: Literal[42]


def canonical_answers(answers: Answers, x_as: str) -> dict:
    if x_as not in ("A", "B"):
        raise ValueError("invalid direction")
    return {
        field: ("X" if value == x_as else "Y") if value in ("A", "B") else value
        for field, value in answers.model_dump().items() if field in FIELDS
    }
