"""Tests for the E1 strict schema (§18.1)."""

import pytest
from pydantic import ValidationError

from e1_judge.hashing import canonical_sha256
from e1_judge.models import (
    AdjudicatedLabel,
    HumanAnnotation,
    JudgeRequest,
    JudgeResult,
    PairRecord,
)


def _pair_payload(**overrides):
    base = dict(
        pair_id="bear-white-p01",
        sample_id="bear-white",
        task_type="attribute",
        instruction="Make the bear white",
        target_caption="A white bear walking",
        source_video_path="/tmp/source.mp4",
        source_checksum="a" * 64,
        mask_paths=[],
        candidate_left_id="bear-white-s101",
        candidate_left_checksum="b" * 64,
        candidate_left_path="/tmp/a.mp4",
        candidate_right_id="bear-white-s202",
        candidate_right_checksum="c" * 64,
        candidate_right_path="/tmp/b.mp4",
        canonical_candidate_a_id="bear-white-s101",
        canonical_candidate_b_id="bear-white-s202",
        display_direction="a_vs_b",
        split="dev",
        randomization_seed=101,
        pair_schema_version="1",
    )
    base.update(overrides)
    return base


def test_pair_requires_all_fields() -> None:
    payload = _pair_payload()
    payload.pop("instruction")
    with pytest.raises(ValidationError):
        PairRecord.model_validate(payload)


def test_pair_rejects_unknown_field() -> None:
    payload = _pair_payload(extra_field="nope")
    with pytest.raises(ValidationError):
        PairRecord.model_validate(payload)


def test_pair_rejects_self_comparison() -> None:
    payload = _pair_payload(candidate_right_id="bear-white-s101")
    with pytest.raises(ValidationError, match="distinct candidates"):
        PairRecord.model_validate(payload)


def test_pair_rejects_unsorted_canonical() -> None:
    payload = _pair_payload(
        canonical_candidate_a_id="bear-white-s202",
        canonical_candidate_b_id="bear-white-s101",
    )
    with pytest.raises(ValidationError, match="lexicographically"):
        PairRecord.model_validate(payload)


def test_pair_rejects_bad_checksum() -> None:
    payload = _pair_payload(source_checksum="not-a-checksum")
    with pytest.raises(ValidationError):
        PairRecord.model_validate(payload)


def test_pair_rejects_ivebench() -> None:
    payload = _pair_payload(instruction="Use IVEBench example")
    with pytest.raises(ValidationError, match="IVEBench"):
        PairRecord.model_validate(payload)


def test_human_annotation_rejects_illegal_preference() -> None:
    payload = dict(
        annotation_id="a1",
        pair_id="bear-white-p01",
        annotator_id="annotator-01",
        display_direction="a_vs_b",
        faithfulness_preference="a",
        preservation_preference="b",
        temporal_consistency_preference="tie",
        visual_quality_preference="uncertain",
        overall_preference="nope",
        confidence=0.8,
        started_at="now",
        submitted_at="later",
        annotation_schema_version="1",
    )
    with pytest.raises(ValidationError):
        HumanAnnotation.model_validate(payload)


def test_judge_request_rejects_ivebench() -> None:
    payload = dict(
        request_id="r1",
        pair_id="bear-white-p01",
        method="pairwise-swap-v1",
        comparison_direction="a_vs_b",
        source_checksum="a" * 64,
        candidate_a_checksum="b" * 64,
        candidate_b_checksum="c" * 64,
        instruction="Use IVEBench prompt",
        target_caption="caption",
        task_type="attribute",
        media_packet_checksum="p" * 64,
        backend="mock",
        model_name="mock",
        model_revision="v0",
        prompt_version="v1",
        parser_version="v1",
    )
    with pytest.raises(ValidationError, match="IVEBench"):
        JudgeRequest.model_validate(payload)


def test_judge_request_absolute_must_not_carry_b() -> None:
    payload = dict(
        request_id="r1",
        candidate_id="bear-white-s101",
        method="absolute-v1",
        comparison_direction="absolute",
        source_checksum="a" * 64,
        candidate_a_checksum="b" * 64,
        candidate_b_checksum="c" * 64,
        instruction="edit",
        target_caption="caption",
        task_type="attribute",
        media_packet_checksum="p" * 64,
        backend="mock",
        model_name="mock",
        model_revision="v0",
        prompt_version="v1",
        parser_version="v1",
    )
    with pytest.raises(ValidationError, match="absolute"):
        JudgeRequest.model_validate(payload)


def test_judge_result_rejects_bad_key() -> None:
    payload = dict(
        request_id="r1",
        judge_key="not-a-hash",
        status="succeeded",
        overall_preference="a",
        confidence=0.9,
        runtime_seconds=1.0,
        peak_vram_mb=100.0,
        prompt_version="v1",
        model_revision="v0",
        created_at="now",
    )
    with pytest.raises(ValidationError):
        JudgeResult.model_validate(payload)


def test_adjudicated_label_rejects_single_annotator() -> None:
    payload = dict(
        pair_id="bear-white-p01",
        annotator_ids=["annotator-01"],
        agreement=True,
        faithfulness_preference="a",
        preservation_preference="b",
        temporal_consistency_preference="tie",
        visual_quality_preference="uncertain",
        overall_preference="a",
        adjudicated_at="now",
        protocol_version="1",
    )
    with pytest.raises(ValidationError, match="too_short"):
        AdjudicatedLabel.model_validate(payload)


def test_canonical_hash_is_order_independent() -> None:
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_canonical_hash_differs_by_value() -> None:
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})
