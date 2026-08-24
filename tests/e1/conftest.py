import csv
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest

from e1_judge.packets import build_packets
from e1_judge.pairs import build_pairs

SAMPLES = [
    ("bear-white", "attribute"), ("bus-red", "attribute"),
    ("elephant-pink", "attribute"), ("classic-car-blue", "attribute"),
    ("dog-tiger", "object"), ("horse-zebra", "object"),
    ("mallard-swan", "object"), ("hiker-backpack", "local"),
    ("rider-helmet", "local"), ("car-headlights", "local"),
]
SEEDS = [101, 202, 303, 404, 505]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_video(path: Path, base: int) -> None:
    with imageio.get_writer(path, fps=8, codec="libx264", quality=8, macro_block_size=None) as writer:
        for index in range(16):
            writer.append_data(np.full((16, 16, 3), (base + index) % 255, dtype=np.uint8))


@pytest.fixture(scope="session")
def e1_v2_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("e1-v2-fixture")
    media = root / "media"
    media.mkdir()
    plan_candidates = []
    candidates = []
    audit_rows = []
    for sample_index, (sample_id, task_type) in enumerate(SAMPLES):
        sample_dir = media / sample_id
        sample_dir.mkdir()
        source = sample_dir / "source.mp4"
        make_video(source, sample_index * 17)
        source_sha = sha256(source)
        for seed_index, seed in enumerate(SEEDS):
            candidate_id = f"{sample_id}-s{seed}"
            video = sample_dir / f"candidate-{seed}.mp4"
            make_video(video, sample_index * 23 + seed_index * 7 + 1)
            plan_candidates.append({
                "candidate_id": candidate_id,
                "sample_id": sample_id,
                "input": {
                    "sample_id": sample_id,
                    "task_type": task_type,
                    "instruction": f"instruction for {sample_id}",
                    "target_caption": f"target for {sample_id}",
                    "source_video_path": str(source),
                    "source_checksum": source_sha,
                    "mask_frame_paths": [],
                },
            })
            candidates.append({
                "candidate_id": candidate_id,
                "sample_id": sample_id,
                "status": "succeeded",
                "video_path": str(video),
                "video_checksum": sha256(video),
            })
            audit_rows.append({"candidate_id": candidate_id, "usable_for_e1": "yes"})

    plan = root / "plan.json"
    candidate_path = root / "candidates.json"
    audit = root / "audit.csv"
    plan.write_text(json.dumps({"candidates": plan_candidates}), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
    with audit.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", "usable_for_e1"])
        writer.writeheader()
        writer.writerows(audit_rows)
    config = Path(__file__).parents[2] / "configs" / "e1" / "pilot.yaml"
    pairs_path = root / "pairs.jsonl"
    pairs = build_pairs(plan, candidate_path, audit, config, pairs_path)
    packets_dir = root / "media-packets"
    manifest = build_packets(pairs_path, packets_dir)
    return {
        "root": root, "plan": plan, "candidates": candidate_path, "audit": audit,
        "config": config, "pairs_path": pairs_path, "pairs": pairs,
        "packets_dir": packets_dir, "manifest": manifest,
    }
