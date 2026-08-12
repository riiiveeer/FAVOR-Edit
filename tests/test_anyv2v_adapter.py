from pathlib import Path


def test_official_configs_use_fixed_w1_values() -> None:
    source = Path("src/w1_pipeline/backends.py").read_text(encoding="utf-8")
    assert '"n_frames": 16' in source
    assert '"target_fps": 8' in source
    assert '"image_size": [512, 512]' in source
    assert "config.inversion_steps" in source
    assert "config.pnp_steps" in source
    assert "config.seed" in source


def test_remote_bootstrap_refuses_unpinned_commit() -> None:
    source = Path("scripts/bootstrap_anyv2v_remote.sh").read_text(encoding="utf-8")
    assert "exact AnyV2V commit required" in source
    assert "experiment directory already exists" in source
