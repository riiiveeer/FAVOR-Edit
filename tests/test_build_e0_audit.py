"""Tests for the E0 visual audit builder (scripts/build_e0_audit.py)."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import pytest
from PIL import Image

from w1_pipeline.e0_audit import (
    AuditError,
    CSV_HEADER,
    build_audit,
    spot_check_ids,
    verify_existing,
)
from w1_pipeline.hashing import sha256_file

SAMPLES = [
    ("bear-white", "attribute"),
    ("bus-red", "attribute"),
    ("elephant-pink", "attribute"),
    ("classic-car-blue", "attribute"),
    ("dog-tiger", "object"),
    ("horse-zebra", "object"),
    ("mallard-swan", "object"),
    ("hiker-backpack", "local"),
    ("rider-helmet", "local"),
    ("car-headlights", "local"),
]
SEEDS = [101, 202, 303, 404, 505]
SIZE = (64, 64)


def _frames(base: int, n: int = 16):
    out = []
    for i in range(n):
        out.append(np.full((SIZE[1], SIZE[0], 3), (base + i) % 255, dtype=np.uint8))
    return out


def _write_video(path: Path, base: int, n: int = 16) -> None:
    with imageio.get_writer(path, fps=8, codec="libx264", quality=8, macro_block_size=None) as writer:
        for frame in _frames(base, n):
            writer.append_data(frame)


def _write_frames(frame_dir: Path, seed: int, n: int = 16):
    frame_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, frame in enumerate(_frames(seed, n)):
        path = frame_dir / f"frame_{i:05d}.png"
        Image.fromarray(frame).save(path)
        paths.append(path)
    return paths


@pytest.fixture(scope="session")
def e0_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("e0")
    media = root / "media"
    media.mkdir()

    inversions = []
    plan_candidates = []
    candidates = []

    for sample_id, task_type in SAMPLES:
        sample_dir = media / sample_id
        sample_dir.mkdir(parents=True)
        source_video = sample_dir / "source.mp4"
        _write_video(source_video, base=0)

        inversions.append(
            {
                "inversion_id": f"inv-{sample_id}",
                "sample_id": sample_id,
                "source_video_path": str(source_video),
                "source_checksum": sha256_file(source_video),
                "steps": 500,
                "artifact_dir": f"inversions/{sample_id}",
            }
        )

        input_record = {
            "sample_id": sample_id,
            "task_type": task_type,
            "instruction": f"instruction for {sample_id}",
            "target_caption": f"target caption for {sample_id}",
            "source_video_path": str(source_video),
        }

        for seed in SEEDS:
            cid = f"{sample_id}-s{seed}"
            candidate_dir = sample_dir / f"seed-{seed}"
            frames = _write_frames(candidate_dir, seed)
            video = candidate_dir / "video.mp4"
            _write_video(video, base=seed)
            frame_checksums = [sha256_file(path) for path in frames]

            plan_candidates.append(
                {
                    "candidate_id": cid,
                    "sample_id": sample_id,
                    "generation_key": "0" * 64,
                    "input": input_record,
                    "config": {"seed": seed},
                    "artifact_dir": f"candidates/{sample_id}/seed-{seed}",
                    "code_snapshot": "snap",
                }
            )
            candidates.append(
                {
                    "candidate_id": cid,
                    "sample_id": sample_id,
                    "generation_key": "0" * 64,
                    "config": {"seed": seed},
                    "status": "succeeded",
                    "artifact_dir": f"candidates/{sample_id}/seed-{seed}",
                    "video_path": str(video),
                    "frame_paths": [str(path) for path in frames],
                    "video_checksum": sha256_file(video),
                    "frame_checksums": frame_checksums,
                    "runtime_seconds": 1.0,
                    "peak_vram_mb": 100.0,
                    "code_snapshot": "snap",
                    "error": None,
                }
            )

    plan_path = root / "plan.json"
    candidates_path = root / "candidates.json"
    plan_data = {"inversions": inversions, "candidates": plan_candidates}
    plan_path.write_text(json.dumps(plan_data), encoding="utf-8")
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")

    return {
        "root": root,
        "plan": plan_path,
        "candidates": candidates_path,
        "plan_data": plan_data,
        "candidates_data": candidates,
    }


@pytest.fixture(scope="session")
def built_audit(e0_fixture, tmp_path_factory):
    out = tmp_path_factory.mktemp("audit") / "E0-visual-audit-v01"
    build_audit(e0_fixture["plan"], e0_fixture["candidates"], out, "snap")
    return out


def _probe_mp4(path: Path):
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
            "-of", "csv=p=0", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    width, height, rate, frames = out.split(",")
    return int(width), int(height), rate, int(frames)


def test_spot_check_set_is_22(e0_fixture):
    ids = spot_check_ids(e0_fixture["plan_data"]["candidates"])
    assert len(ids) == 22
    assert len(set(ids)) == 22
    # 3 samples x 5 seeds (full) + 7 samples x seed 303 = 15 + 7 = 22.
    assert sum(1 for cid in ids if int(cid.rsplit("-s", 1)[1]) == 303) == 10


def test_build_rejects_existing_output(e0_fixture, tmp_path):
    out = tmp_path / "audit"
    out.mkdir()
    with pytest.raises(AuditError, match="already exists"):
        build_audit(e0_fixture["plan"], e0_fixture["candidates"], out, "snap")


def test_build_rejects_non50_candidates(e0_fixture, tmp_path):
    bad = tmp_path / "candidates-49.json"
    bad.write_text(json.dumps(e0_fixture["candidates_data"][:49]), encoding="utf-8")
    with pytest.raises(AuditError, match="50"):
        build_audit(e0_fixture["plan"], bad, tmp_path / "audit", "snap")


def test_build_produces_decodable_contact_sheets_and_proxies(e0_fixture, built_audit):
    plan_sha_before = sha256_file(e0_fixture["plan"])
    candidates_sha_before = sha256_file(e0_fixture["candidates"])

    # E0 inputs are unchanged by the build (read-only derivative).
    assert sha256_file(e0_fixture["plan"]) == plan_sha_before
    assert sha256_file(e0_fixture["candidates"]) == candidates_sha_before

    sheets = sorted((built_audit / "contact-sheets").glob("*.jpg"))
    assert len(sheets) == 50
    for path in sheets:
        with Image.open(path) as image:
            image.load()
            assert image.size[0] > 0 and image.size[1] > 0

    proxies = sorted((built_audit / "proxies").glob("*.mp4"))
    assert len(proxies) == 22
    for path in proxies:
        width, height, rate, frames = _probe_mp4(path)
        assert (width, height) == (512, 256)
        assert rate == "8/1"
        assert frames == 16


def test_sha256sums_excludes_self_and_verifies(built_audit):
    sums = (built_audit / "SHA256SUMS").read_text(encoding="utf-8")
    assert "SHA256SUMS" not in sums
    result = subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS"],
        cwd=built_audit,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _fill_audit_csv(audit_dir: Path, spot_ids, *, bad_tag: bool = False, omit_reviewer: bool = False):
    csv_path = audit_dir / "audit.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        row["reviewer"] = "" if omit_reviewer else "reviewer-01"
        row["reviewed_at"] = "2026-08-23T00:00:00+08:00"
        row["usable_for_e1"] = "yes"
        row["failure_tags"] = "bad-tag" if bad_tag else ""
        if row["candidate_id"] in spot_ids:
            row["faithfulness"] = "2"
            row["preservation"] = "2"
            row["temporal_consistency"] = "1"
            row["visual_quality"] = "2"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def test_verify_existing_accepts_valid_sheet(e0_fixture, built_audit, tmp_path):
    audit = tmp_path / "audit"
    _copy_tree(built_audit, audit)
    spot_ids = set(json.loads((audit / "audit-manifest.json").read_text())["spot_check_ids"])
    _fill_audit_csv(audit, spot_ids)
    result = verify_existing(audit)
    assert result["valid"] is True
    assert result["rows"] == 50


def test_verify_existing_rejects_unknown_failure_tag(e0_fixture, built_audit, tmp_path):
    audit = tmp_path / "audit"
    _copy_tree(built_audit, audit)
    spot_ids = set(json.loads((audit / "audit-manifest.json").read_text())["spot_check_ids"])
    _fill_audit_csv(audit, spot_ids, bad_tag=True)
    with pytest.raises(AuditError, match="unknown failure tags"):
        verify_existing(audit)


def test_verify_existing_rejects_missing_reviewer(e0_fixture, built_audit, tmp_path):
    audit = tmp_path / "audit"
    _copy_tree(built_audit, audit)
    spot_ids = set(json.loads((audit / "audit-manifest.json").read_text())["spot_check_ids"])
    _fill_audit_csv(audit, spot_ids, omit_reviewer=True)
    with pytest.raises(AuditError, match="missing reviewer"):
        verify_existing(audit)


def test_cli_help_and_verify_entry(tmp_path, built_audit):
    script = Path("scripts/build_e0_audit.py")
    help_result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert help_result.returncode == 0
    assert "--verify-existing" in help_result.stdout

    # Fill a copy so --verify-existing succeeds end to end.
    audit = tmp_path / "audit"
    _copy_tree(built_audit, audit)
    spot_ids = set(json.loads((audit / "audit-manifest.json").read_text())["spot_check_ids"])
    _fill_audit_csv(audit, spot_ids)
    verify_result = subprocess.run(
        [sys.executable, str(script), "--verify-existing", str(audit)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert verify_result.returncode == 0, verify_result.stderr
    assert "audit verified" in verify_result.stdout


def _copy_tree(src: Path, dst: Path) -> None:
    import shutil

    shutil.copytree(src, dst)