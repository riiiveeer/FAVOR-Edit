import json
from pathlib import Path

import pytest

from e1_judge.annotations import (
    _render_page, adjudicate, canonical_preference, cohen_kappa,
    _load_pair_filter, display_direction, media_tokens, read_media_range,
)
from e1_judge.models import HumanAnnotationV2, MediaManifestV2, PairRecordV2


def _annotation(pair_id: str, annotator: str, preference: str = "a") -> dict:
    return HumanAnnotationV2(
        annotation_id=f"{annotator}-{pair_id}", pair_id=pair_id, annotator_id=annotator,
        display_direction="a_vs_b", faithfulness_preference=preference,
        preservation_preference=preference, temporal_consistency_preference=preference,
        visual_quality_preference=preference, overall_preference=preference,
        confidence=0.8, started_at="2026-08-24T00:00:00+00:00",
        submitted_at="2026-08-24T00:01:00+00:00",
    ).model_dump(mode="json")


def _write(path: Path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_display_direction_and_screen_mapping_are_deterministic():
    first = display_direction("sample-p01", "annotator-01", 7)
    assert first == display_direction("sample-p01", "annotator-01", 7)
    assert canonical_preference("left", "a_vs_b") == "a"
    assert canonical_preference("left", "b_vs_a") == "b"
    assert canonical_preference("right", "b_vs_a") == "a"
    assert canonical_preference("tie", "b_vs_a") == "tie"


def test_render_uses_opaque_media_tokens_and_hides_candidate_ids(e1_v2_fixture):
    pair = PairRecordV2.model_validate(e1_v2_fixture["pairs"][0])
    manifest = MediaManifestV2.model_validate(e1_v2_fixture["manifest"])
    tokens, files = media_tokens(manifest, [pair], "annotator-01")
    page = _render_page(pair, 0, 100, tokens, False)
    assert "<video" in page and "source-contact" not in page
    assert pair.candidate_a.candidate_id not in page
    assert pair.candidate_b.candidate_id not in page
    assert len(files) == 7


def test_media_range_supports_partial_video(e1_v2_fixture):
    video = Path(next(iter(e1_v2_fixture["manifest"]["sources"].values()))["video"]["path"])
    status, headers, body = read_media_range(video, "bytes=0-9")
    assert status == 206 and len(body) == 10
    assert headers["Content-Range"].startswith("bytes 0-9/")
    status, headers, body = read_media_range(video, None)
    assert status == 200 and len(body) == video.stat().st_size


def test_adjudicate_100_pairs_and_write_agreement_report(e1_v2_fixture, tmp_path):
    pair_ids = [pair["pair_id"] for pair in e1_v2_fixture["pairs"]]
    first = tmp_path / "annotator-01.jsonl"
    second = tmp_path / "annotator-02.jsonl"
    _write(first, [_annotation(pair_id, "annotator-01") for pair_id in pair_ids])
    _write(second, [_annotation(pair_id, "annotator-02") for pair_id in pair_ids])
    output = tmp_path / "adjudicated.jsonl"
    report = tmp_path / "agreement.json"
    records = adjudicate([first, second], None, output, report)
    assert len(records) == 100 and all(record["agreement"] for record in records)
    metrics = json.loads(report.read_text())
    assert metrics["disputed_pairs"] == 0
    assert metrics["agreement"]["overall"]["cohen_kappa"] == 1.0


def test_dispute_requires_exact_third_party_coverage(e1_v2_fixture, tmp_path):
    pair_ids = [pair["pair_id"] for pair in e1_v2_fixture["pairs"]]
    first_records = [_annotation(pair_id, "annotator-01") for pair_id in pair_ids]
    second_records = [_annotation(pair_id, "annotator-02") for pair_id in pair_ids]
    second_records[0] = _annotation(pair_ids[0], "annotator-02", "b")
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write(first, first_records)
    _write(second, second_records)
    with pytest.raises(ValueError, match="exactly disputed"):
        adjudicate([first, second], None, tmp_path / "bad.jsonl", tmp_path / "bad-report.json")
    precheck = json.loads((tmp_path / "bad-report.json").read_text(encoding="utf-8"))
    assert precheck["status"] == "needs_third_annotator"
    assert _load_pair_filter(tmp_path / "bad-report.json") == [pair_ids[0]]
    third = tmp_path / "third.jsonl"
    _write(third, [_annotation(pair_ids[0], "annotator-03", "b")])
    records = adjudicate([first, second], third, tmp_path / "ok.jsonl", tmp_path / "ok-report.json")
    assert records[0]["overall_preference"] == "b"
    assert records[0]["third_annotator_id"] == "annotator-03"


def test_cohen_kappa_known_values():
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["b", "b", "a", "a"]) == -1.0
