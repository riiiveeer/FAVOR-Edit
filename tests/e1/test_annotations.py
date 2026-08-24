"""Tests for E1 human annotation adjudication (§18.5)."""

import json

import pytest

from e1_judge.annotations import adjudicate, _agreement
from e1_judge.models import HumanAnnotation


def _annotation(pair_id, annotator_id, overall="a", faithfulness="a", preservation="b", temporal="tie", quality="uncertain"):
    return dict(
        annotation_id=f"{pair_id}-{annotator_id}",
        pair_id=pair_id,
        annotator_id=annotator_id,
        display_direction="a_vs_b",
        faithfulness_preference=faithfulness,
        preservation_preference=preservation,
        temporal_consistency_preference=temporal,
        visual_quality_preference=quality,
        overall_preference=overall,
        confidence=0.8,
        started_at="",
        submitted_at="",
        annotation_schema_version="1",
    )


def _write(path, records):
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def test_adjudicate_agreement_uses_first(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out = tmp_path / "adjudicated.jsonl"
    _write(a, [_annotation("p1", "annotator-01", overall="a")])
    _write(b, [_annotation("p1", "annotator-02", overall="a")])
    results = adjudicate([a, b], None, out)
    assert len(results) == 1
    assert results[0]["agreement"] is True
    assert results[0]["overall_preference"] == "a"
    assert results[0]["third_annotator_id"] is None


def test_adjudicate_dispute_requires_third(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out = tmp_path / "adjudicated.jsonl"
    _write(a, [_annotation("p1", "annotator-01", overall="a")])
    _write(b, [_annotation("p1", "annotator-02", overall="b")])
    with pytest.raises(ValueError, match="no third annotation"):
        adjudicate([a, b], None, out)


def test_adjudicate_dispute_uses_third(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    c = tmp_path / "c.jsonl"
    out = tmp_path / "adjudicated.jsonl"
    _write(a, [_annotation("p1", "annotator-01", overall="a")])
    _write(b, [_annotation("p1", "annotator-02", overall="b")])
    _write(c, [_annotation("p1", "annotator-03", overall="b")])
    results = adjudicate([a, b], c, out)
    assert results[0]["agreement"] is False
    assert results[0]["third_annotator_id"] == "annotator-03"
    assert results[0]["overall_preference"] == "b"


def test_adjudicate_missing_annotator_fails(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out = tmp_path / "adjudicated.jsonl"
    _write(a, [_annotation("p1", "annotator-01", overall="a")])
    _write(b, [_annotation("p2", "annotator-02", overall="a")])
    with pytest.raises(ValueError, match="missing annotation"):
        adjudicate([a, b], None, out)


def test_agreement_flags_tie_uncertain(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    out = tmp_path / "adjudicated.jsonl"
    _write(a, [_annotation("p1", "annotator-01", overall="tie")])
    _write(b, [_annotation("p1", "annotator-02", overall="tie")])
    results = adjudicate([a, b], None, out)
    assert results[0]["human_tie"] is True
    assert results[0]["human_uncertain"] is False


def test_agreement_helper():
    x = HumanAnnotation.model_validate(_annotation("p1", "a", overall="a"))
    y = HumanAnnotation.model_validate(_annotation("p1", "b", overall="a"))
    assert _agreement(x, y) is True
    z = HumanAnnotation.model_validate(_annotation("p1", "b", overall="b"))
    assert _agreement(x, z) is False
