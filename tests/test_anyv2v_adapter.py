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


def test_edit_image_driven_via_dict_file_path() -> None:
    """The edit_image adapter must use the official --dict_file path.

    The --video_path/--output_dir path in the upstream edit_image.py contains a
    video_filename debug-print bug, so the adapter must drive the editor through
    --dict_file instead of patching the external checkout.
    """
    source = Path("src/w1_pipeline/backends.py").read_text(encoding="utf-8")
    assert "--dict_file" in source
    assert "--input_dir" in source
    assert '"image_model": "instructpix2pix"' in source
    assert 'f"{record.sample_id}.mp4"' in source
