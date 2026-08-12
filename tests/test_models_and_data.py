from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest
from pydantic import ValidationError
from PIL import Image

from w1_pipeline.data import load_spec, prepare_dataset, validate_prepared_manifest, validate_spec
from w1_pipeline.models import ExperimentSpec, SourceInput, TaskType


MANIFEST = Path("configs/w1_manifest.yaml")


def test_fixed_manifest_is_valid() -> None:
    spec = load_spec(MANIFEST)
    validate_spec(spec)
    assert len(spec.inputs) == 10
    assert len(spec.seeds) == 5


def test_duplicate_seed_is_rejected() -> None:
    payload = load_spec(MANIFEST).model_dump(mode="json")
    payload["seeds"] = [101, 101]
    with pytest.raises(ValidationError, match="seeds must be unique"):
        ExperimentSpec.model_validate(payload)


def test_duplicate_sample_is_rejected() -> None:
    payload = load_spec(MANIFEST).model_dump(mode="json")
    payload["inputs"][1]["sample_id"] = payload["inputs"][0]["sample_id"]
    with pytest.raises(ValidationError, match="sample_id values must be unique"):
        ExperimentSpec.model_validate(payload)


def test_ivebench_is_rejected() -> None:
    spec = load_spec(MANIFEST)
    spec.inputs[0].instruction = "Use IVEBench example"
    with pytest.raises(ValueError, match="IVEBench"):
        validate_spec(spec)


def test_illegal_split_is_rejected() -> None:
    payload = load_spec(MANIFEST).model_dump(mode="json")
    payload["split"] = "test"
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate(payload)


def test_prepare_synthetic_davis_clip(tmp_path: Path) -> None:
    root = tmp_path / "DAVIS"
    frame_dir = root / "JPEGImages" / "480p" / "bear"
    mask_dir = root / "Annotations" / "480p" / "bear"
    frame_dir.mkdir(parents=True)
    mask_dir.mkdir(parents=True)
    for index in range(50):
        frame = np.full((80, 120, 3), index, dtype=np.uint8)
        mask = np.zeros((80, 120), dtype=np.uint8)
        mask[20:60, 40:80] = 1
        Image.fromarray(frame).save(frame_dir / f"{index:05d}.jpg")
        Image.fromarray(mask).save(mask_dir / f"{index:05d}.png")

    spec = ExperimentSpec(
        dataset="DAVIS-2017",
        split="train",
        seeds=[101, 202, 303, 404, 505],
        inputs=[
            SourceInput(
                sample_id="bear-white",
                sequence="bear",
                task_type=TaskType.ATTRIBUTE,
                instruction="Make the bear white",
                target_caption="A white bear walking",
            )
        ],
    )
    # Exercise the media path without applying the fixed 10-input policy.
    import w1_pipeline.data as data_module

    record = data_module._prepare_one(root, tmp_path / "prepared", spec, spec.inputs[0])
    assert len(record.source_frame_paths) == 16
    assert record.crop.side == 50
    assert all(Image.open(path).size == (512, 512) for path in record.source_frame_paths)
    reader = imageio.get_reader(record.source_video_path)
    assert reader.get_meta_data()["fps"] == 8.0
    assert sum(1 for _ in reader) == 16


def test_prepared_manifest_rejects_missing_files(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="10 unique"):
        validate_prepared_manifest(path)
