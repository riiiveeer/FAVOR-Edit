from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from w1_pipeline.hashing import sha256_file
from w1_pipeline.models import CandidateRecord, CandidateStatus, GenerationConfig, InputRecord
from w1_pipeline.planning import generation_key


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _write_audit(path: Path, candidate_ids, field: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_id", field])
        writer.writeheader()
        for candidate_id in candidate_ids:
            writer.writerow({"candidate_id": candidate_id, field: "yes"})


@pytest.fixture()
def e2_m1_fixture(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    source_frames = []
    masks = []
    for index in range(16):
        frame = tmp_path / "source" / f"{index:05d}.png"
        mask = tmp_path / "mask" / f"{index:05d}.png"
        frame.parent.mkdir(parents=True, exist_ok=True)
        mask.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (index, 20, 30)).save(frame)
        Image.new("L", (8, 8), 255 if index % 2 else 0).save(mask)
        source_frames.append(str(frame))
        masks.append(str(mask))

    sample_ids = [f"sample-{index:02d}" for index in range(10)]
    config = tmp_path / "pilot.yaml"
    config.write_text(yaml.safe_dump({
        "schema_version": "1", "experiment_id": "E2-bon-pilot-v01",
        "dataset": "DAVIS-2017", "split": "train", "sample_ids": sample_ids,
        "base_seeds": [101, 202, 303, 404, 505], "extension_seeds": [606, 707, 808],
        "n_values": [1, 2, 4, 8], "subset_design": "balanced-cyclic", "replicates": 8,
        "randomization_seed": 20260829, "bootstrap_seed": 20260829,
        "bootstrap_iterations": 200, "human_comparison": "n4-vs-n1",
        "primary_annotators": 2, "third_party_adjudication": True,
    }, sort_keys=False), encoding="utf-8")

    inversions = []
    tasks = []
    records = []
    for sample_id in sample_ids:
        input_record = InputRecord(
            sample_id=sample_id, dataset="DAVIS-2017", split="train", sequence=sample_id,
            task_type="attribute", instruction=f"edit {sample_id}", target_caption=f"target {sample_id}",
            source_frame_paths=source_frames, mask_frame_paths=masks, source_video_path=str(source),
            source_checksum="1" * 64, mask_checksum="2" * 64, video_checksum=sha256_file(source),
            crop={"x": 0, "y": 0, "side": 32, "output_size": 512, "window_start": 0,
                  "source_window_length": 48, "stride": 3},
        )
        inversions.append({"inversion_id": f"inv-{sample_id}", "sample_id": sample_id})
        for seed in [101, 202, 303, 404, 505]:
            generation = GenerationConfig(
                backend="mock", model_commit="mock-model-v1", anyv2v_commit="mock-anyv2v-v1", seed=seed,
            )
            candidate_id = f"{sample_id}-s{seed}"
            key = generation_key(input_record, generation, "base-snapshot")
            task = {
                "candidate_id": candidate_id, "sample_id": sample_id, "generation_key": key,
                "input": input_record.model_dump(mode="json"), "config": generation.model_dump(mode="json"),
                "artifact_dir": f"candidates/{sample_id}/seed-{seed}", "code_snapshot": "base-snapshot",
            }
            tasks.append(task)
            video = tmp_path / "media" / candidate_id / "video.mp4"
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(candidate_id.encode())
            frames = []
            for frame_index in range(16):
                frame = video.parent / f"{frame_index:05d}.png"
                Image.new("RGB", (8, 8), (frame_index, seed % 255, 40)).save(frame)
                frames.append(frame)
            records.append(CandidateRecord(
                candidate_id=candidate_id, sample_id=sample_id, generation_key=key, config=generation,
                status=CandidateStatus.SUCCEEDED, artifact_dir=task["artifact_dir"], video_path=str(video),
                frame_paths=[str(item) for item in frames], video_checksum=sha256_file(video),
                frame_checksums=[sha256_file(item) for item in frames], runtime_seconds=1.0,
                peak_vram_mb=0.0, code_snapshot="base-snapshot",
            ).model_dump(mode="json"))

    e0_plan = tmp_path / "e0-plan.json"
    e0_candidates = tmp_path / "e0-candidates.json"
    e0_audit = tmp_path / "e0-audit.csv"
    _write_json(e0_plan, {"inversions": inversions, "candidates": tasks})
    _write_json(e0_candidates, records)
    _write_audit(e0_audit, [item["candidate_id"] for item in tasks], "usable_for_e1")
    return {
        "root": tmp_path, "config": config, "sample_ids": sample_ids,
        "e0_plan": e0_plan, "e0_candidates": e0_candidates, "e0_audit": e0_audit,
        "write_json": _write_json, "write_audit": _write_audit,
    }
