"""Directional and boundary tests for CPU-only Defense MVP metrics."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from defense_mvp.config import load_config
from defense_mvp.metrics import _load_masks, _load_rgb_frames, score_arrays, score_ingest
from w1_pipeline.hashing import sha256_file


CONFIG = Path("configs/defense_mvp/pilot.yaml")


def _arrays(frames: int = 4, size: int = 32):
    source = np.full((frames, size, size, 3), 0.35, dtype=np.float32)
    masks = np.zeros((frames, size, size), dtype=bool)
    masks[:, size // 4:3 * size // 4, size // 4:3 * size // 4] = True
    return source, masks


def test_target_color_evidence_increases_faithfulness() -> None:
    cfg = load_config(CONFIG)
    source, masks = _arrays()
    unchanged = score_arrays(source, source.copy(), masks, cfg.color_rules["bus-red"], cfg)
    red = source.copy()
    red[masks] = np.array([0.9, 0.08, 0.08], dtype=np.float32)
    edited = score_arrays(source, red, masks, cfg.color_rules["bus-red"], cfg)
    assert unchanged["scores"]["F"] == 0.0
    assert edited["scores"]["F"] > unchanged["scores"]["F"]
    assert edited["components"]["target_color_pixel_hits"] > 0


def test_background_damage_lowers_preservation() -> None:
    cfg = load_config(CONFIG)
    source, masks = _arrays()
    inside_only = source.copy()
    inside_only[masks] = 0.7
    damaged = inside_only.copy()
    damaged[~masks] = 0.95
    kept = score_arrays(source, inside_only, masks, cfg.color_rules["bus-red"], cfg)
    broken = score_arrays(source, damaged, masks, cfg.color_rules["bus-red"], cfg)
    assert broken["scores"]["P"] < kept["scores"]["P"]


def test_edit_flicker_lowers_temporal_consistency() -> None:
    cfg = load_config(CONFIG)
    source, masks = _arrays()
    stable = source.copy()
    stable[masks] = np.array([0.9, 0.08, 0.08], dtype=np.float32)
    flicker = stable.copy()
    flicker[1::2] = source[1::2]
    stable_result = score_arrays(source, stable, masks, cfg.color_rules["bus-red"], cfg)
    flicker_result = score_arrays(source, flicker, masks, cfg.color_rules["bus-red"], cfg)
    assert flicker_result["scores"]["T"] < stable_result["scores"]["T"]


def test_overexposed_flat_frames_lower_quality() -> None:
    cfg = load_config(CONFIG)
    frames, size = 4, 32
    checker = (np.indices((size, size)).sum(axis=0) % 2).astype(np.float32)
    frame = 0.2 + checker[..., None] * 0.6
    source = np.repeat(frame[None, ...], frames, axis=0)
    source = np.repeat(source, 3, axis=3).astype(np.float32)
    masks = np.zeros((frames, size, size), dtype=bool)
    masks[:, 8:24, 8:24] = True
    clean = score_arrays(source, source.copy(), masks, cfg.color_rules["bus-red"], cfg)
    overexposed = np.ones_like(source)
    degraded = score_arrays(source, overexposed, masks, cfg.color_rules["bus-red"], cfg)
    assert degraded["scores"]["Q"] < clean["scores"]["Q"]
    assert degraded["components"]["abnormal_frame_count"] == frames


def test_mask_fraction_and_no_replace_are_enforced(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    source, _ = _arrays()
    empty = np.zeros(source.shape[:3], dtype=bool)
    with pytest.raises(ValueError, match="mask fraction"):
        score_arrays(source, source.copy(), empty, cfg.color_rules["bus-red"], cfg)
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        score_ingest(tmp_path / "missing.json", CONFIG, output)


def test_palette_mask_uses_nonzero_class_indices(tmp_path: Path) -> None:
    raw = np.zeros((512, 512), dtype=np.uint8)
    raw[128:384, 128:384] = 1
    image = Image.new("P", (512, 512))
    image.putdata(raw.ravel())
    image.putpalette([0, 0, 0, 128, 0, 0] + [0] * (256 * 3 - 6))
    path = tmp_path / "mask.png"
    image.save(path)
    masks = _load_masks(tmp_path, ["mask.png"], [sha256_file(path)], "index-nonzero-v1")
    assert masks.shape == (1, 512, 512)
    assert masks[0].mean() == pytest.approx(0.25)


def test_rgb_loader_rejects_non_rgb_frames(tmp_path: Path) -> None:
    path = tmp_path / "gray.png"
    Image.new("L", (512, 512), color=127).save(path)
    with pytest.raises(ValueError, match="512x512 RGB"):
        _load_rgb_frames(tmp_path, ["gray.png"], [sha256_file(path)])


def test_local_color_evidence_excludes_existing_target_pixels() -> None:
    cfg = load_config(CONFIG)
    source, masks = _arrays()
    source[masks] = [0.8, 0.08, 0.08]
    candidate = source.copy()
    candidate[masks] = [0.9, 0.08, 0.08]
    local = score_arrays(source, candidate, masks, cfg.color_rules["hiker-backpack"], cfg)
    attribute = score_arrays(source, candidate, masks, cfg.color_rules["bus-red"], cfg)
    assert local["components"]["target_color_pixel_hits"] == 0
    assert local["scores"]["F"] == 0.0
    assert attribute["scores"]["F"] > 0.0


def test_blur_alone_lowers_quality_without_exposure_penalty() -> None:
    cfg = load_config(CONFIG)
    source, masks = _arrays()
    checker = (np.indices(source.shape[1:3]).sum(axis=0) % 2).astype(np.float32)
    source[:] = 0.2 + checker[..., None] * 0.6
    blurred = np.full_like(source, 0.5)
    clean = score_arrays(source, source, masks, cfg.color_rules["bus-red"], cfg)
    degraded = score_arrays(source, blurred, masks, cfg.color_rules["bus-red"], cfg)
    assert degraded["components"]["exposure_good"] == 1.0
    assert degraded["components"]["brightness_stability"] == 1.0
    assert degraded["scores"]["Q"] < clean["scores"]["Q"]
