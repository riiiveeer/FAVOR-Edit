import json
from pathlib import Path

import pytest
from PIL import Image

from e1_judge.packets import build_packets


def test_pair_counts_splits_and_canonical_context(e1_v2_fixture):
    pairs = e1_v2_fixture["pairs"]
    plan = json.loads(e1_v2_fixture["plan"].read_text(encoding="utf-8"))
    inputs_by_sample = {
        task["sample_id"]: task["input"]
        for task in plan["candidates"]
    }
    assert len(pairs) == 100
    assert sum(pair["split"] == "dev" for pair in pairs) == 30
    assert sum(pair["split"] == "frozen-eval" for pair in pairs) == 70
    assert all(pair["candidate_a"]["candidate_id"] < pair["candidate_b"]["candidate_id"] for pair in pairs)
    assert all(pair["source"]["sample_id"] == pair["sample_id"] for pair in pairs)
    assert all(
        pair["source"]["video_sha256"] == inputs_by_sample[pair["sample_id"]]["video_checksum"]
        for pair in pairs
    )
    assert all(
        pair["source"]["video_sha256"] != inputs_by_sample[pair["sample_id"]]["source_checksum"]
        for pair in pairs
    )


def test_media_manifest_deduplicates_and_contains_exact_frames(e1_v2_fixture):
    manifest = e1_v2_fixture["manifest"]
    assert manifest["schema_version"] == "2"
    assert len(manifest["sources"]) == 10
    assert len(manifest["candidates"]) == 50
    assert len(manifest["pairs"]) == 100
    for asset in [*manifest["sources"].values(), *manifest["candidates"].values()]:
        assert len(asset["frames"]) == 16
        assert all(Path(frame["path"]).is_file() for frame in asset["frames"])
        with Image.open(asset["contact_sheet"]["path"]) as image:
            assert image.size == (650, 650)
    stored = json.loads((e1_v2_fixture["packets_dir"] / "media-manifest.json").read_text(encoding="utf-8"))
    assert stored == manifest


def test_packet_output_must_be_new(e1_v2_fixture):
    with pytest.raises(FileExistsError, match="already exists"):
        build_packets(e1_v2_fixture["pairs_path"], e1_v2_fixture["packets_dir"])
