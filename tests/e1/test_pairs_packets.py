"""Tests for E1 pair construction and media packets (§18.2, §10)."""

import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest
from PIL import Image

from e1_judge.packets import build_packets
from e1_judge.pairs import build_pairs, _display_direction

SAMPLES = [
    ("bear-white", "attribute"),
    ("bus-red", "attribute"),
    ("elephant-pink", "attribute"),
    ("classic-car-blue", "attribute"),
    ("dog-tiger", "object"),
    ("horse-zebra", "object"),
    ("mallard-swan", "object"),
    ("hiker-backpack", "local"),
    ("rider-helmet", "local"),
    ("car-headlights", "local"),
]
SEEDS = [101, 202, 303, 404, 505]
SIZE = (48, 48)


def _video(path: Path, base: int, n: int = 16) -> None:
    with imageio.get_writer(path, fps=8, codec="libx264", quality=8, macro_block_size=None) as writer:
        for i in range(n):
            writer.append_data(np.full((SIZE[1], SIZE[0], 3), (base + i) % 255, dtype=np.uint8))


def _checksum(path: Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def e0_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("e0")
    media = root / "media"
    media.mkdir()

    inversions = []
    plan_candidates = []
    candidates = []

    for sample_id, task_type in SAMPLES:
        sample_dir = media / sample_id
        sample_dir.mkdir(parents=True)
        source = sample_dir / "source.mp4"
        _video(source, 0)

        inversions.append({"sample_id": sample_id, "source_video_path": str(source), "source_checksum": "a" * 64})

        for seed in SEEDS:
            cid = f"{sample_id}-s{seed}"
            video = sample_dir / f"seed-{seed}.mp4"
            _video(video, seed)
            plan_candidates.append(
                {
                    "candidate_id": cid,
                    "sample_id": sample_id,
                    "input": {
                        "sample_id": sample_id,
                        "task_type": task_type,
                        "instruction": f"instruction for {sample_id}",
                        "target_caption": f"target caption for {sample_id}",
                        "source_video_path": str(source),
                        "source_checksum": "a" * 64,
                        "mask_frame_paths": [],
                    },
                }
            )
            candidates.append(
                {
                    "candidate_id": cid,
                    "sample_id": sample_id,
                    "video_path": str(video),
                    "video_checksum": _checksum(video),
                }
            )

    plan_path = root / "plan.json"
    candidates_path = root / "candidates.json"
    plan_path.write_text(json.dumps({"inversions": inversions, "candidates": plan_candidates}), encoding="utf-8")
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")

    audit_path = root / "audit.csv"
    with audit_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("candidate_id,faithfulness,preservation,temporal_consistency,visual_quality,failure_tags,systematic_failure,usable_for_e1,reviewer,reviewed_at,notes\n")
        for record in candidates:
            handle.write(f"{record['candidate_id']},2,2,2,2,,,,yes,anon-01,2026-08-23,\n")

    config_path = root / "pilot.yaml"
    config_path.write_text(
        "dataset: DAVIS-2017\n"
        "split: train\n"
        "dev_samples: [bear-white, dog-tiger, hiker-backpack]\n"
        "frozen_eval_samples: [bus-red, elephant-pink, classic-car-blue, horse-zebra, mallard-swan, rider-helmet, car-headlights]\n",
        encoding="utf-8",
    )
    return root, plan_path, candidates_path, audit_path, config_path


def test_build_pairs_100_with_correct_split(e0_fixture, tmp_path):
    _, plan, candidates, audit, config = e0_fixture
    output = tmp_path / "pairs.jsonl"
    pairs = build_pairs(plan, candidates, audit, config, output)
    assert len(pairs) == 100
    assert sum(1 for p in pairs if p["split"] == "dev") == 30
    assert sum(1 for p in pairs if p["split"] == "frozen-eval") == 70
    assert len({p["pair_id"] for p in pairs}) == 100
    from collections import Counter

    counts = Counter(p["sample_id"] for p in pairs)
    assert all(count == 10 for count in counts.values())
    assert len(counts) == 10


def test_build_pairs_no_cross_sample(e0_fixture, tmp_path):
    _, plan, candidates, audit, config = e0_fixture
    pairs = build_pairs(plan, candidates, audit, config, tmp_path / "pairs.jsonl")
    for pair in pairs:
        assert pair["candidate_left_id"].startswith(pair["sample_id"])
        assert pair["candidate_right_id"].startswith(pair["sample_id"])


def test_display_direction_is_deterministic():
    first = _display_direction("bear-white-p01", "annotator-01", 7)
    second = _display_direction("bear-white-p01", "annotator-01", 7)
    assert first == second
    assert first in ("a_vs_b", "b_vs_a")


def test_build_packets_creates_dirs_and_metadata(e0_fixture, tmp_path):
    _, plan, candidates, audit, config = e0_fixture
    pairs_path = tmp_path / "pairs.jsonl"
    build_pairs(plan, candidates, audit, config, pairs_path)
    packet_dir = tmp_path / "media-packets"
    records = build_packets(pairs_path, packet_dir)
    assert len(records) == 100
    first_dir = packet_dir / "bear-white-p01"
    assert (first_dir / "source.mp4").exists() or (first_dir / "source.mp4").is_symlink()
    assert (first_dir / "candidate-a.mp4").exists() or (first_dir / "candidate-a.mp4").is_symlink()
    assert (first_dir / "candidate-b.mp4").exists() or (first_dir / "candidate-b.mp4").is_symlink()
    metadata = json.loads((first_dir / "metadata.json").read_text())
    assert metadata["pair_id"] == "bear-white-p01"
    assert metadata["mask_available"] is False
    with Image.open(first_dir / "source-contact.jpg") as image:
        image.load()
        assert image.size[0] > 0


def test_build_packets_refuses_existing_dir(e0_fixture, tmp_path):
    _, plan, candidates, audit, config = e0_fixture
    pairs_path = tmp_path / "pairs.jsonl"
    build_pairs(plan, candidates, audit, config, pairs_path)
    packet_dir = tmp_path / "media-packets"
    packet_dir.mkdir()
    with pytest.raises(FileExistsError):
        build_packets(pairs_path, packet_dir)


