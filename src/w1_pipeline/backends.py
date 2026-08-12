"""Generation backends for deterministic mock runs and official AnyV2V."""

import json
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

import imageio.v2 as imageio
import numpy as np
import yaml
from PIL import Image, ImageDraw

from .hashing import sha256_file
from .models import CandidateRecord, CandidateStatus, GenerationConfig, InputRecord


class GenerationBackend(ABC):
    calls: int = 0

    @abstractmethod
    def generate(self, task: Dict[str, Any], experiment_dir: Path) -> CandidateRecord:
        raise NotImplementedError


def _replace_directory(source: Path, destination: Path, attempts: int = 10) -> None:
    """Atomically publish a completed directory, tolerating short Windows AV/ffmpeg locks."""
    for attempt in range(attempts):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))


def _record(task: Dict[str, Any], status: CandidateStatus, **updates: Any) -> CandidateRecord:
    return CandidateRecord(
        candidate_id=task["candidate_id"],
        sample_id=task["sample_id"],
        generation_key=task["generation_key"],
        config=GenerationConfig.model_validate(task["config"]),
        status=status,
        artifact_dir=task["artifact_dir"],
        code_snapshot=task["code_snapshot"],
        **updates,
    )


class MockBackend(GenerationBackend):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, task: Dict[str, Any], experiment_dir: Path) -> CandidateRecord:
        self.calls += 1
        started = time.perf_counter()
        record = InputRecord.model_validate(task["input"])
        config = GenerationConfig.model_validate(task["config"])
        final_dir = experiment_dir / task["artifact_dir"]
        temp_dir = final_dir.with_name(final_dir.name + ".tmp")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        rng = np.random.default_rng(config.seed)
        color = tuple(int(value) for value in rng.integers(32, 224, 3))
        frame_paths: List[Path] = []
        frames: List[np.ndarray] = []
        for index, source_path in enumerate(record.source_frame_paths):
            image = Image.open(source_path).convert("RGB")
            draw = ImageDraw.Draw(image)
            draw.rectangle((4, 4, 507, 507), outline=color, width=5)
            draw.text((12, 12), f"MOCK {config.seed} #{index:02d}", fill=color)
            frame_path = temp_dir / f"frame_{index:05d}.png"
            image.save(frame_path)
            frame_paths.append(frame_path)
            frames.append(np.asarray(image))
        video_path = temp_dir / "video.mp4"
        with imageio.get_writer(video_path, fps=config.fps, codec="libx264", quality=8, macro_block_size=None) as writer:
            for frame in frames:
                writer.append_data(frame)
        metadata = {"mock": True, "candidate_id": task["candidate_id"], "seed": config.seed, "research_result": False}
        (temp_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        _replace_directory(temp_dir, final_dir)
        final_frames = [final_dir / path.name for path in frame_paths]
        final_video = final_dir / "video.mp4"
        return _record(
            task,
            CandidateStatus.SUCCEEDED,
            video_path=str(final_video.resolve()),
            frame_paths=[str(path.resolve()) for path in final_frames],
            video_checksum=sha256_file(final_video),
            frame_checksums=[sha256_file(path) for path in final_frames],
            runtime_seconds=time.perf_counter() - started,
            peak_vram_mb=0.0,
        )


class AnyV2VBackend(GenerationBackend):
    """Adapter around an exact checkout of the official AnyV2V repository."""

    def __init__(self, anyv2v_root: Path, python_executable: str = "python", device: str = "cuda:0") -> None:
        self.root = anyv2v_root.resolve()
        self.python = python_executable
        self.device = device
        self.calls = 0

    def _checkout(self) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, check=True, text=True
        ).stdout.strip()

    def generate(self, task: Dict[str, Any], experiment_dir: Path) -> CandidateRecord:
        self.calls += 1
        started = time.perf_counter()
        config = GenerationConfig.model_validate(task["config"])
        record = InputRecord.model_validate(task["input"])
        if self._checkout() != config.anyv2v_commit:
            raise RuntimeError("AnyV2V checkout does not match the pinned commit")

        experiment_dir = experiment_dir.resolve()
        final_dir = (experiment_dir / task["artifact_dir"]).resolve()
        if experiment_dir not in final_dir.parents:
            raise RuntimeError("candidate artifact directory escaped the experiment directory")
        work_dir = final_dir.with_name(final_dir.name + ".tmp")
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=False)
        staging_dir = experiment_dir / "anyv2v_data"
        demo_dir = staging_dir / "demo"
        source_video = demo_dir / f"{record.sample_id}.mp4"
        source_frames = demo_dir / record.sample_id
        source_frames.mkdir(parents=True, exist_ok=True)
        if not source_video.is_file():
            shutil.copy2(record.source_video_path, source_video)
        for index, frame in enumerate(record.source_frame_paths):
            destination = source_frames / f"{index:05d}.png"
            if not destination.is_file():
                shutil.copy2(frame, destination)

        inversion_dir = staging_dir / "inversions" / "i2vgen-xl" / record.sample_id
        latent_dir = inversion_dir / "ddim_latents"
        if not latent_dir.is_dir() or not any(latent_dir.iterdir()):
            if inversion_dir.exists():
                raise RuntimeError(f"incomplete inversion exists and will not be overwritten: {inversion_dir}")
            inversion_template = {
                "seed": 8888, "device": self.device, "debug": False,
                "data_dir": str(staging_dir), "model_name": "i2vgen-xl", "exp_name": record.sample_id,
                "output_dir": str(inversion_dir), "image_size": [512, 512],
                "video_dir": str(demo_dir), "video_name": record.sample_id,
                "video_path": str(source_video), "video_frames_path": str(source_frames), "n_frames": 16,
                "inverse_config": {
                    "image_size": [512, 512], "n_frames": 16, "cfg": 1.0, "target_fps": 8,
                    "prompt": "", "negative_prompt": "", "n_steps": config.inversion_steps,
                    "output_dir": str(latent_dir), "inverse_static_video": False, "null_image_inversion": False,
                },
                "recon_config": {
                    "enable_recon": False, "image_size": [512, 512], "n_frames": 16, "cfg": config.cfg,
                    "target_fps": 8, "prompt": "", "negative_prompt": "", "n_steps": config.pnp_steps,
                    "ddim_init_latents_t_idx": 0, "ddim_latents_path": str(latent_dir),
                },
            }
            inversion_group = [{"active": True, "force_recompute_latents": False, "video_name": record.sample_id}]
            inv_template_path = work_dir / "inversion-template.yaml"
            inv_group_path = work_dir / "inversion-group.json"
            inv_template_path.write_text(yaml.safe_dump(inversion_template, sort_keys=False), encoding="utf-8")
            inv_group_path.write_text(json.dumps(inversion_group, indent=2), encoding="utf-8")
            subprocess.run(
                [self.python, "run_group_ddim_inversion.py", "--template_config", str(inv_template_path), "--configs_json", str(inv_group_path)],
                cwd=self.root / "i2vgen-xl", check=True,
            )
            if not latent_dir.is_dir() or not any(latent_dir.iterdir()):
                raise RuntimeError("AnyV2V inversion command completed without latent artifacts")
        edited_first_frame = work_dir / "edited_first_frame" / f"seed-{config.seed}.png"
        edited_first_frame.parent.mkdir()

        commands = [
            [
                self.python,
                str(self.root / "edit_image.py"),
                "--model", "instructpix2pix",
                "--video_path", str(source_video),
                "--output_dir", str(edited_first_frame.parent),
                "--prompt", record.instruction,
                "--seed", str(config.seed),
                "--force_512",
            ]
        ]
        # The official edit script names the result after the prompt.
        generated_first_frame = edited_first_frame.parent / f"{record.instruction}.png"
        for command in commands:
            subprocess.run(command, cwd=self.root, check=True)
        if not generated_first_frame.is_file():
            raise RuntimeError(f"edited first frame was not produced: {generated_first_frame}")

        official_output = work_dir / "official-output"
        pnp_template = {
            "seed": config.seed, "device": self.device, "debug": False,
            "data_dir": str(staging_dir), "model_name": "i2vgen-xl", "task_name": "Prompt-Based-Editing",
            "edited_video_name": task["candidate_id"], "output_dir": str(official_output),
            "image_size": [512, 512], "video_dir": str(demo_dir), "video_name": record.sample_id,
            "video_path": str(source_video), "video_frames_path": str(source_frames),
            "edited_first_frame_path": str(generated_first_frame), "ddim_latents_path": str(latent_dir),
            "n_frames": 16, "cfg": config.cfg, "target_fps": 8,
            "editing_prompt": record.target_caption,
            "editing_negative_prompt": "Distorted, discontinuous, ugly, blurry, low resolution, motionless, static, disfigured",
            "n_steps": config.pnp_steps, "ddim_init_latents_t_idx": config.ddim_init_latents_t_idx,
            "ddim_inv_prompt": "", "random_ratio": config.random_ratio,
            "pnp_f_t": config.pnp_f_t, "pnp_spatial_attn_t": config.pnp_spatial_attn_t,
            "pnp_temp_attn_t": config.pnp_temp_attn_t,
        }
        pnp_group = [{"active": True, "video_name": record.sample_id, "output_dir": str(official_output)}]
        pnp_template_path = work_dir / "pnp-template.yaml"
        pnp_group_path = work_dir / "pnp-group.json"
        pnp_template_path.write_text(yaml.safe_dump(pnp_template, sort_keys=False), encoding="utf-8")
        pnp_group_path.write_text(json.dumps(pnp_group, indent=2), encoding="utf-8")
        subprocess.run(
            [self.python, "run_group_pnp_edit.py", "--template_config", str(pnp_template_path), "--configs_json", str(pnp_group_path)],
            cwd=self.root / "i2vgen-xl", check=True,
        )

        produced_videos = list(official_output.rglob("video.mp4"))
        produced_frames = sorted(official_output.rglob("video_[0-9][0-9][0-9][0-9][0-9].png"))
        if len(produced_videos) != 1 or len(produced_frames) != 16:
            raise RuntimeError(f"expected one video and 16 frames, got {len(produced_videos)} and {len(produced_frames)}")
        canonical_video = work_dir / "video.mp4"
        shutil.copy2(produced_videos[0], canonical_video)
        canonical_frames = []
        for index, path in enumerate(produced_frames):
            output = work_dir / f"frame_{index:05d}.png"
            shutil.copy2(path, output)
            canonical_frames.append(output)
        metadata = {
            "mock": False, "candidate_id": task["candidate_id"], "record": record.model_dump(mode="json"),
            "generation": config.model_dump(mode="json"), "anyv2v_checkout": self._checkout(),
        }
        (work_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        _replace_directory(work_dir, final_dir)
        final_frames = [final_dir / path.name for path in canonical_frames]
        final_video = final_dir / canonical_video.name
        return _record(
            task, CandidateStatus.SUCCEEDED, video_path=str(final_video),
            frame_paths=[str(path) for path in final_frames], video_checksum=sha256_file(final_video),
            frame_checksums=[sha256_file(path) for path in final_frames],
            runtime_seconds=time.perf_counter() - started, peak_vram_mb=_peak_vram_mb(),
        )


def _peak_vram_mb() -> float:
    try:
        output = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, check=True, text=True,
        ).stdout.splitlines()
        return max([float(value.strip()) for value in output] or [0.0])
    except (OSError, subprocess.CalledProcessError, ValueError):
        return 0.0


def load_backend(name: str, anyv2v_root: Path = None, python_executable: str = "python", device: str = "cuda:0") -> GenerationBackend:
    if name == "mock":
        return MockBackend()
    if name == "anyv2v":
        if anyv2v_root is None:
            raise ValueError("--anyv2v-root is required for the anyv2v backend")
        return AnyV2VBackend(anyv2v_root, python_executable, device)
    raise ValueError(f"unknown backend: {name}")
