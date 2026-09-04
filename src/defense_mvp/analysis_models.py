"""Strict, result-independent D4 analysis protocol models."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


FIELDS = (
    "overall",
    "faithfulness",
    "preservation",
    "temporal_consistency",
    "visual_quality",
)
CATEGORIES = ("X", "Y", "tie", "uncertain")
FAMILIES = ("proposed-n4-vs-n1", "proposed-vs-linear-n4")
NODES = ("constrained-pareto-n4", "constrained-pareto-n1", "equal-linear-n4")
INPUT_PINS = {
    "bundle": "c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6",
    "annotator_a_inventory": "ad796e6aca1991b72f9820d2eee807c4fec89a9c80e9574ee1aae8ed3ffcae85",
    "annotator_b_inventory": "91e6a169b81ef825e29e808a8777c264be55b5f88d5eed8ab9f82d5afc936a3a",
    "dual_verification": "280b099845be84936021e3bffa9e4f69ab24749a7833f03ea3909f18737bd357",
    "pilot": "19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae",
    "comparisons": "486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb",
    "selection_lock": "99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2",
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class FamilyConfig(Strict):
    total: int = Field(gt=0)
    automatic_ties: int = Field(ge=0)
    proposed_role: Literal["constrained-pareto-n4"]
    comparator_role: Literal["constrained-pareto-n1", "equal-linear-n4"]


class AggregationConfig(Strict):
    rule: Literal["conservative-pair-v1"]
    manual_comparisons: Literal[32]
    automatic_comparisons: Literal[10]
    total_comparisons: Literal[42]


class AgreementConfig(Strict):
    scope: Literal["manual-only"]
    expected_comparisons: Literal[32]


class BradleyTerryConfig(Strict):
    field: Literal["overall"]
    nodes: List[str]
    algorithm: Literal["centered-newton-no-penalty-v1"]
    tolerance: float = Field(gt=0.0)
    max_iterations: int = Field(gt=0)
    max_step_halvings: int = Field(ge=0)

    @model_validator(mode="after")
    def fixed_nodes(self) -> "BradleyTerryConfig":
        if self.nodes != list(NODES):
            raise ValueError("Bradley-Terry nodes/order must match the frozen protocol")
        if self.tolerance != 1.0e-10 or self.max_iterations != 100 or self.max_step_halvings != 60:
            raise ValueError("Bradley-Terry numerical settings drifted")
        return self


class BootstrapConfig(Strict):
    cluster: Literal["sample_id"]
    expected_clusters: Literal[7]
    rng: Literal["numpy.Generator(PCG64)"]
    seed: Literal[20260901]
    iterations: Literal[2000]
    confidence_level: Literal[0.95]
    quantiles: List[float]
    quantile_method: Literal["linear"]
    fields: List[str]

    @model_validator(mode="after")
    def fixed_bootstrap(self) -> "BootstrapConfig":
        if self.quantiles != [0.025, 0.975]:
            raise ValueError("bootstrap quantiles must be 2.5%/97.5%")
        if self.fields != list(FIELDS):
            raise ValueError("bootstrap fields/order must match the frozen five fields")
        return self


class FailureCaseConfig(Strict):
    field: Literal["overall"]
    proposed_outcomes: List[str]
    sort: List[str]

    @model_validator(mode="after")
    def fixed_failure_cases(self) -> "FailureCaseConfig":
        if self.proposed_outcomes != ["loss", "uncertain"]:
            raise ValueError("failure-case outcomes drifted")
        if self.sort != ["family", "sample_id", "comparison_id"]:
            raise ValueError("failure-case sort drifted")
        return self


class TimingConfig(Strict):
    annotation_semantics: Literal["current-view-server-elapsed-not-active-labor"]
    analysis_clock: Literal["perf_counter-elapsed-seconds"]


class AnalysisConfig(Strict):
    schema_version: Literal["1"]
    protocol: Literal["defense-analysis-v1"]
    experiment_id: Literal["DEFENSE-MVP-v01"]
    fields: List[str]
    categories: List[str]
    input_pins: Dict[str, str]
    families: Dict[str, FamilyConfig]
    aggregation: AggregationConfig
    agreement: AgreementConfig
    primary_scope: Literal["all-42"]
    diagnostic_scope: Literal["manual-only"]
    bradley_terry: BradleyTerryConfig
    bootstrap: BootstrapConfig
    failure_cases: FailureCaseConfig
    timing: TimingConfig

    @model_validator(mode="after")
    def fixed_protocol(self) -> "AnalysisConfig":
        if self.fields != list(FIELDS) or self.categories != list(CATEGORIES):
            raise ValueError("analysis fields/categories/order drifted")
        if self.input_pins != INPUT_PINS:
            raise ValueError("formal input pins drifted")
        if list(self.families) != list(FAMILIES):
            raise ValueError("analysis families/order drifted")
        expected = {
            FAMILIES[0]: (28, 6, "constrained-pareto-n1"),
            FAMILIES[1]: (14, 4, "equal-linear-n4"),
        }
        for family, (total, automatic, comparator) in expected.items():
            item = self.families[family]
            if (item.total, item.automatic_ties, item.comparator_role) != (total, automatic, comparator):
                raise ValueError(f"family protocol drifted: {family}")
        return self


def load_analysis_config(path: Path) -> AnalysisConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return AnalysisConfig.model_validate(payload)


Canonical = Literal["X", "Y", "tie", "uncertain"]
AggregateSource = Literal["human_pair", "automatic_tie"]


class AggregateSide(Strict):
    role: str
    candidate_id: str
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class HumanObservation(Strict):
    canonical: Dict[str, Canonical]
    confidence: float = Field(ge=0.0, le=1.0)
    current_view_elapsed_seconds: float = Field(ge=0.0)

    @model_validator(mode="after")
    def complete_fields(self) -> "HumanObservation":
        if set(self.canonical) != set(FIELDS):
            raise ValueError("human observation fields drifted")
        self.canonical = {field: self.canonical[field] for field in FIELDS}
        return self


class AggregateRecord(Strict):
    schema_version: Literal["1"]
    protocol: Literal["defense-analysis-v1"]
    comparison_id: str
    family: Literal["proposed-n4-vs-n1", "proposed-vs-linear-n4"]
    trial_id: str
    sample_id: str
    replicate: int = Field(ge=1, le=4)
    source: AggregateSource
    reason: Optional[Literal["media_identity"]] = None
    candidate_x: AggregateSide
    candidate_y: AggregateSide
    proposed_side: Literal["X", "Y"]
    aggregate: Dict[str, Canonical]
    human: Optional[Dict[str, HumanObservation]] = None

    @model_validator(mode="after")
    def coherent_source_and_fields(self) -> "AggregateRecord":
        if set(self.aggregate) != set(FIELDS):
            raise ValueError("aggregate fields drifted")
        self.aggregate = {field: self.aggregate[field] for field in FIELDS}
        if self.source == "human_pair":
            if self.reason is not None or self.human is None or list(self.human) != ["annotator-a", "annotator-b"]:
                raise ValueError("human-pair provenance invalid")
        else:
            if self.reason != "media_identity" or self.human is not None:
                raise ValueError("automatic-tie provenance invalid")
            if any(value != "tie" for value in self.aggregate.values()):
                raise ValueError("automatic comparison must aggregate to tie")
        return self
