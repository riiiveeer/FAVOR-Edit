from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable

import pytest
import yaml

from defense_mvp.config import load_config
from defense_mvp.models import (
    FrameSetV1, MediaRefV1, PackageCandidateV1, PackageCountsV1, PackageFileV1,
    PackageManifestV1, PackageSampleV1, PackageSourceIdentityV1,
)
from w1_pipeline.hashing import combined_file_sha256, sha256_file
from w1_pipeline.models import (
    CandidateRecord, CandidateStatus, CropParameters, ExperimentSpec, GenerationConfig, InputRecord,
)


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _write_json(path: Path, payload) -> Path:
    return _write(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


@pytest.fixture
def handoff_factory(tmp_path: Path) -> Callable[[], Path]:
    def build() -> Path:
        root = tmp_path / "delivery"
        root.mkdir()
        cfg = load_config(Path("configs/defense_mvp/pilot.yaml"))
        spec = ExperimentSpec.model_validate(
            yaml.safe_load(Path("configs/w1_manifest.yaml").read_text(encoding="utf-8"))
        )
        tasks = {item.sample_id: item for item in spec.inputs}
        file_entries = []

        def add_file(relative: str, payload: bytes, role: str) -> Path:
            path = _write(root / Path(*relative.split("/")), payload)
            file_entries.append(PackageFileV1(
                relative_path=relative, role=role, sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            ))
            return path

        samples = []
        plan_inputs = {}
        for sample_id in cfg.sample_ids:
            task = tasks[sample_id]
            source_video_rel = f"media/sources/{sample_id}/source.mp4"
            source_video = add_file(source_video_rel, f"source:{sample_id}".encode(), "source-video")
            source_frames, masks = [], []
            source_frame_rels, mask_rels = [], []
            for index in range(16):
                source_rel = f"media/sources/{sample_id}/frames/{index:05d}.png"
                mask_rel = f"media/sources/{sample_id}/masks/{index:05d}.png"
                source_frame_rels.append(source_rel)
                mask_rels.append(mask_rel)
                source_frames.append(add_file(source_rel, f"source:{sample_id}:{index}".encode(), "source-frame"))
                masks.append(add_file(mask_rel, f"mask:{sample_id}:{index}".encode(), "mask"))
            crop = CropParameters(x=0, y=0, side=64, output_size=512, window_start=0, source_window_length=48, stride=3)
            input_record = InputRecord(
                sample_id=sample_id, dataset="DAVIS-2017", split="train",
                sequence=task.sequence, task_type=task.task_type, instruction=task.instruction,
                target_caption=task.target_caption,
                source_frame_paths=[f"/server/{value}" for value in source_frame_rels],
                mask_frame_paths=[f"/server/{value}" for value in mask_rels],
                source_video_path=f"/server/{source_video_rel}",
                source_checksum=combined_file_sha256(source_frames),
                mask_checksum=combined_file_sha256(masks),
                video_checksum=sha256_file(source_video), crop=crop,
            )
            plan_inputs[sample_id] = input_record
            samples.append(PackageSampleV1(
                sample_id=sample_id, sequence=task.sequence, task_type=task.task_type.value,
                instruction=task.instruction, target_caption=task.target_caption,
                source_video=MediaRefV1(relative_path=source_video_rel, sha256=sha256_file(source_video)),
                source_frames=FrameSetV1(relative_paths=source_frame_rels,
                    sha256=[sha256_file(path) for path in source_frames],
                    combined_sha256=combined_file_sha256(source_frames)),
                masks=FrameSetV1(relative_paths=mask_rels,
                    sha256=[sha256_file(path) for path in masks],
                    combined_sha256=combined_file_sha256(masks)),
                crop=crop,
            ))

        package_candidates = []
        original_candidates = []
        plan_candidates = []
        inversions = []
        for sample_id in cfg.sample_ids:
            inversions.append({"inversion_id": f"inv-{sample_id}", "sample_id": sample_id})
            for seed in cfg.seeds:
                candidate_id = f"{sample_id}-s{seed}"
                video_rel = f"media/candidates/{sample_id}/seed-{seed}/video.mp4"
                video = add_file(video_rel, f"video:{candidate_id}".encode(), "candidate-video")
                frame_rels, frames = [], []
                for index in range(16):
                    relative = f"media/candidates/{sample_id}/seed-{seed}/frames/{index:05d}.png"
                    frame_rels.append(relative)
                    frames.append(add_file(relative, f"frame:{candidate_id}:{index}".encode(), "candidate-frame"))
                config = GenerationConfig(
                    backend="anyv2v", model_commit="model-commit-v1",
                    anyv2v_commit="anyv2v-commit-v1", seed=seed,
                )
                generation_key = sha256_file(video)
                record = CandidateRecord(
                    candidate_id=candidate_id, sample_id=sample_id, generation_key=generation_key,
                    config=config, status=CandidateStatus.SUCCEEDED,
                    artifact_dir=f"/server/candidates/{sample_id}/seed-{seed}",
                    video_path=f"/server/{video_rel}",
                    frame_paths=[f"/server/{value}" for value in frame_rels],
                    video_checksum=sha256_file(video),
                    frame_checksums=[sha256_file(path) for path in frames],
                    runtime_seconds=1.0, peak_vram_mb=22000.0, code_snapshot="e0-snapshot-v1",
                )
                original_candidates.append(record.model_dump(mode="json"))
                plan_candidates.append({
                    "candidate_id": candidate_id, "sample_id": sample_id,
                    "input": plan_inputs[sample_id].model_dump(mode="json"),
                    "config": config.model_dump(mode="json"),
                })
                package_candidates.append(PackageCandidateV1(
                    candidate_id=candidate_id, sample_id=sample_id, seed=seed, status="succeeded",
                    video=MediaRefV1(relative_path=video_rel, sha256=sha256_file(video)),
                    frames=FrameSetV1(relative_paths=frame_rels,
                        sha256=[sha256_file(path) for path in frames],
                        combined_sha256=combined_file_sha256(frames)),
                    generation_key=generation_key, config=config, runtime_seconds=1.0,
                    peak_vram_mb=22000.0, code_snapshot="e0-snapshot-v1",
                ))

        plan_path = add_file(
            "metadata/original-plan.json",
            (json.dumps({"inversions": inversions, "candidates": plan_candidates}, sort_keys=True) + "\n").encode(),
            "metadata",
        )
        candidates_path = add_file(
            "metadata/original-candidates.json",
            (json.dumps(original_candidates, sort_keys=True) + "\n").encode(),
            "metadata",
        )
        candidate_ids = [item.candidate_id for item in package_candidates]
        audit_path = add_file(
            "metadata/e0-audit/audit-manifest.json",
            (json.dumps({"candidate_ids": candidate_ids}, sort_keys=True) + "\n").encode(),
            "audit",
        )
        audit_csv = root / "metadata/e0-audit/audit.csv"
        audit_csv.parent.mkdir(parents=True, exist_ok=True)
        with audit_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["candidate_id"])
            writer.writerows([[value] for value in candidate_ids])
        file_entries.append(PackageFileV1(relative_path="metadata/e0-audit/audit.csv",
            role="audit", sha256=sha256_file(audit_csv), size_bytes=audit_csv.stat().st_size))
        add_file("metadata/W1_REPORT.md", b"# real E0 fixture identity\n", "report")

        manifest = PackageManifestV1(
            schema_version="1", package_id="DEFENSE-MVP-E0-HANDOFF-v01",
            created_at="2026-09-01T00:00:00+08:00", created_by="fixture", hostname="fixture-host",
            status="passed",
            source=PackageSourceIdentityV1(
                e0_root="/server/e0", audit_root="/server/audit", repo_head="a" * 40, repo_status="clean",
                plan_sha256=sha256_file(plan_path), candidates_sha256=sha256_file(candidates_path),
                audit_manifest_sha256=sha256_file(audit_path), e0_code_snapshots=["e0-snapshot-v1"],
                model_commits=["model-commit-v1"], anyv2v_commits=["anyv2v-commit-v1"],
            ),
            counts=PackageCountsV1(samples=10, candidates=50, mp4=60, source_frames=160,
                masks=160, candidate_frames=800, files=len(file_entries),
                total_bytes=sum(item.size_bytes for item in file_entries)),
            samples=samples, candidates=package_candidates, files=file_entries,
            warnings=[], missing_optional_artifacts=[],
        )
        _write_json(root / "PACKAGE_MANIFEST.json", manifest.model_dump(mode="json"))
        _write_json(root / "PACKAGE_VERIFICATION.json", {
            "status": "passed", "ready_for_transfer": True,
            "counts": manifest.counts.model_dump(mode="json"),
        })
        _write(root / "PACKAGE_BUILD_LOG.txt", b"fixture build\n")
        _write(root / "PACKAGE_BUILD_SCRIPT.py", b"# fixture\n")
        _write(root / "README.md", b"# fixture package\n")
        sums = []
        for path in sorted((value for value in root.rglob("*") if value.is_file()),
                           key=lambda value: value.relative_to(root).as_posix()):
            sums.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
        (root / "PACKAGE_SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        return root

    return build
