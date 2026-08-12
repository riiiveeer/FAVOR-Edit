import json
from pathlib import Path

import numpy as np
from PIL import Image

from w1_pipeline.backends import MockBackend
from w1_pipeline.cache import Cache
from w1_pipeline.hashing import canonical_sha256
from w1_pipeline.models import CropParameters, InputRecord, TaskType
from w1_pipeline.planning import build_plan, write_plan
from w1_pipeline.runner import run_candidates


def _prepared_manifest(tmp_path: Path) -> Path:
    records = []
    for sample_index in range(10):
        sample_dir = tmp_path / f"sample-{sample_index}"
        frames, masks = [], []
        for frame_index in range(16):
            frame_path = sample_dir / "frames" / f"{frame_index:05d}.png"
            mask_path = sample_dir / "masks" / f"{frame_index:05d}.png"
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(np.full((512, 512, 3), sample_index * 10, dtype=np.uint8)).save(frame_path)
            Image.fromarray(np.ones((512, 512), dtype=np.uint8)).save(mask_path)
            frames.append(frame_path)
            masks.append(mask_path)
        # Mock backend only needs an existing source video path; frame content drives outputs.
        source_video = sample_dir / "source.mp4"
        source_video.write_bytes(b"fixture")
        from w1_pipeline.hashing import combined_file_sha256, sha256_file

        records.append(
            InputRecord(
                sample_id=f"sample-{sample_index}", dataset="DAVIS-2017", split="train",
                sequence=f"sequence-{sample_index}", task_type=TaskType.ATTRIBUTE,
                instruction="Make it blue", target_caption="A blue object",
                source_frame_paths=[str(p.resolve()) for p in frames],
                mask_frame_paths=[str(p.resolve()) for p in masks],
                source_video_path=str(source_video.resolve()),
                source_checksum=combined_file_sha256(frames), mask_checksum=combined_file_sha256(masks),
                video_checksum=sha256_file(source_video), crop=CropParameters(x=0, y=0, side=512, window_start=0),
            ).model_dump(mode="json")
        )
    path = tmp_path / "prepared.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_canonical_hash_ignores_dict_order() -> None:
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_mock_plan_run_and_resume(tmp_path: Path) -> None:
    prepared = _prepared_manifest(tmp_path)
    inversions, candidates = build_plan(
        prepared, [101, 202, 303, 404, 505], "mock", "mock-model-v1", "mock-anyv2v-v1", "test-snapshot"
    )
    assert len(inversions) == 10
    assert len(candidates) == 50
    plan = tmp_path / "plan.json"
    write_plan(plan, inversions, candidates)
    backend = MockBackend()
    records, hits = run_candidates(plan, tmp_path / "experiment", tmp_path / "cache.sqlite3", backend)
    assert sum(record.status.value == "succeeded" for record in records) == 50
    assert backend.calls == 50 and hits == 0
    second_backend = MockBackend()
    second_records, second_hits = run_candidates(plan, tmp_path / "experiment", tmp_path / "cache.sqlite3", second_backend)
    assert len(second_records) == 50
    assert second_backend.calls == 0 and second_hits == 50


def test_cache_roundtrip(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put_generation("key", "candidate", "planned", {"value": 1})
        assert cache.get_generation("key") == {"value": 1}
