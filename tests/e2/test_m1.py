from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner
from PIL import Image

from e2_bon.cli import app
from e2_bon.io import read_json
from e2_bon.models import CandidatePoolV1
from e2_bon.pool import build_candidate_pool, plan_generation_extension
from w1_pipeline.hashing import sha256_file
from w1_pipeline.models import CandidateRecord, CandidateStatus


def _extension_records(fixture, plan_path: Path):
    records = []
    for task in read_json(plan_path)["candidates"]:
        candidate_id = task["candidate_id"]
        video = fixture["root"] / "extension-media" / candidate_id / "video.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(candidate_id.encode())
        frames = []
        for index in range(16):
            frame = video.parent / f"{index:05d}.png"
            Image.new("RGB", (8, 8), (index, int(task["config"]["seed"]) % 255, 80)).save(frame)
            frames.append(frame)
        records.append(CandidateRecord(
            candidate_id=candidate_id, sample_id=task["sample_id"], generation_key=task["generation_key"],
            config=task["config"], status=CandidateStatus.SUCCEEDED, artifact_dir=task["artifact_dir"],
            video_path=str(video), frame_paths=[str(item) for item in frames], video_checksum=sha256_file(video),
            frame_checksums=[sha256_file(item) for item in frames], runtime_seconds=2.0, peak_vram_mb=0.0,
            code_snapshot=task["code_snapshot"],
        ).model_dump(mode="json"))
    return records


def test_plan_generation_builds_exact_30_tasks(e2_m1_fixture):
    output = e2_m1_fixture["root"] / "extension-plan.json"
    payload = plan_generation_extension(
        e2_m1_fixture["e0_plan"], e2_m1_fixture["config"], output, "extension-snapshot"
    )
    assert output.is_file()
    assert len(payload["inversions"]) == 10
    assert len(payload["candidates"]) == 30
    assert {task["config"]["seed"] for task in payload["candidates"]} == {606, 707, 808}
    assert all(task["code_snapshot"] == "extension-snapshot" for task in payload["candidates"])
    assert len({task["generation_key"] for task in payload["candidates"]}) == 30
    with pytest.raises(FileExistsError):
        plan_generation_extension(e2_m1_fixture["e0_plan"], e2_m1_fixture["config"], output, "retry")


def test_generation_planner_rejects_semantic_drift(e2_m1_fixture):
    payload = read_json(e2_m1_fixture["e0_plan"])
    payload["candidates"][1]["config"]["cfg"] = 8.0
    bad = e2_m1_fixture["root"] / "bad-plan.json"
    e2_m1_fixture["write_json"](bad, payload)
    with pytest.raises(ValueError, match="drift"):
        plan_generation_extension(bad, e2_m1_fixture["config"], e2_m1_fixture["root"] / "out.json", "x")


def test_build_pool_verifies_80_candidates_and_files(e2_m1_fixture):
    extension_plan = e2_m1_fixture["root"] / "extension-plan.json"
    plan_generation_extension(e2_m1_fixture["e0_plan"], e2_m1_fixture["config"], extension_plan, "extension-snapshot")
    extension_records = _extension_records(e2_m1_fixture, extension_plan)
    extension_candidates = e2_m1_fixture["root"] / "extension-candidates.json"
    extension_audit = e2_m1_fixture["root"] / "extension-audit.csv"
    e2_m1_fixture["write_json"](extension_candidates, extension_records)
    e2_m1_fixture["write_audit"](
        extension_audit, [item["candidate_id"] for item in extension_records], "usable_for_e2"
    )
    output = e2_m1_fixture["root"] / "candidate-pool.json"
    payload = build_candidate_pool(
        e2_m1_fixture["e0_plan"], e2_m1_fixture["e0_candidates"], e2_m1_fixture["e0_audit"],
        extension_plan, extension_candidates, extension_audit, e2_m1_fixture["config"], output,
    )
    model = CandidatePoolV1.model_validate(payload)
    assert model.candidate_count == 80 and model.sample_count == 10
    assert {item.origin for item in model.candidates} == {"e0", "extension"}
    for sample_id in e2_m1_fixture["sample_ids"]:
        assert sorted(item.seed for item in model.candidates if item.sample_id == sample_id) == [101,202,303,404,505,606,707,808]
    with pytest.raises(FileExistsError):
        build_candidate_pool(
            e2_m1_fixture["e0_plan"], e2_m1_fixture["e0_candidates"], e2_m1_fixture["e0_audit"],
            extension_plan, extension_candidates, extension_audit, e2_m1_fixture["config"], output,
        )


def test_pool_rejects_checksum_and_audit_corruption(e2_m1_fixture):
    extension_plan = e2_m1_fixture["root"] / "extension-plan.json"
    plan_generation_extension(e2_m1_fixture["e0_plan"], e2_m1_fixture["config"], extension_plan, "extension-snapshot")
    records = _extension_records(e2_m1_fixture, extension_plan)
    records[0]["video_checksum"] = "0" * 64
    extension_candidates = e2_m1_fixture["root"] / "bad-candidates.json"
    extension_audit = e2_m1_fixture["root"] / "extension-audit.csv"
    e2_m1_fixture["write_json"](extension_candidates, records)
    e2_m1_fixture["write_audit"](extension_audit, [item["candidate_id"] for item in records], "usable_for_e2")
    with pytest.raises(ValueError, match="checksum"):
        build_candidate_pool(
            e2_m1_fixture["e0_plan"], e2_m1_fixture["e0_candidates"], e2_m1_fixture["e0_audit"],
            extension_plan, extension_candidates, extension_audit, e2_m1_fixture["config"],
            e2_m1_fixture["root"] / "pool.json",
        )
    rows = extension_audit.read_text(encoding="utf-8").replace("yes", "no", 1)
    extension_audit.write_text(rows, encoding="utf-8")
    with pytest.raises(ValueError, match="usable_for_e2"):
        build_candidate_pool(
            e2_m1_fixture["e0_plan"], e2_m1_fixture["e0_candidates"], e2_m1_fixture["e0_audit"],
            extension_plan, extension_candidates, extension_audit, e2_m1_fixture["config"],
            e2_m1_fixture["root"] / "pool-2.json", verify_files=False,
        )


def test_cli_validate_and_help():
    runner = CliRunner()
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0 and '"candidates": 80' in result.stdout
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    for command in ("validate", "plan-generation", "build-pool"):
        assert command in help_result.stdout
