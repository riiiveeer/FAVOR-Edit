"""Production-semantics tests for the phase-3 preparation verifier."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from e1_judge.cli import app
from e1_judge.preparation import (
    PreparationPathMapping,
    PreparationVerificationError,
    verify_preparation,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _write_jsonl(path: Path, records) -> Path:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _manifest_copy(bundle, tmp_path: Path) -> dict:
    return json.loads(
        (bundle["packets_dir"] / "media-manifest.json").read_text(encoding="utf-8")
    )


def _run(bundle, **overrides):
    return verify_preparation(
        overrides.get("pairs", bundle["pairs_path"]),
        overrides.get("packets", bundle["packets_dir"]),
        overrides.get("plan", bundle["judge_plan"]),
        overrides.get("config", bundle["config"]),
        overrides.get("runtime", bundle["runtime"]),
        overrides.get("output"),
    )


def _failure_text(exc: PreparationVerificationError) -> str:
    return json.dumps(exc.report["failures"], ensure_ascii=False, sort_keys=True)


def test_path_mapping_round_trips_final_and_staging_paths(tmp_path):
    declared = tmp_path / "E1-final"
    physical = tmp_path / ".E1-final.prepare-test.staging"
    mapping = PreparationPathMapping(declared, physical)
    assert mapping.physical_path(declared / "inputs" / "pairs.jsonl") == (
        physical / "inputs" / "pairs.jsonl"
    )
    assert mapping.declared_path(physical / "plans" / "plan.jsonl") == (
        declared / "plans" / "plan.jsonl"
    )
    external = tmp_path / "E0" / "plan.json"
    assert mapping.physical_path(external) == external
    assert mapping.declared_path(external) == external


def test_happy_path_100_pairs_550_requests_and_production_masks(
    e1_preparation_fixture, tmp_path
):
    bundle = e1_preparation_fixture
    report_path = tmp_path / "preparation-verification.json"
    report = _run(bundle, output=report_path)

    assert report["status"] == "passed"
    assert report["ready_for_smoke"] is True
    assert report["counts"]["pairs"] == 100
    assert report["counts"]["samples"] == 10
    assert report["counts"]["source_assets"] == 10
    assert report["counts"]["candidate_assets"] == 50
    assert report["counts"]["pair_packets"] == 100
    assert report["counts"]["asset_frames"] == 60 * 16
    assert report["counts"]["mask_overlays"] == 100
    assert report["counts"]["requests"] == 550
    assert report["split_counts"]["pairs"] == {"dev": 30, "frozen-eval": 70}
    assert report["split_counts"]["requests"] == {"dev": 165, "frozen-eval": 385}
    assert report["method_counts"] == {
        "absolute-v1": 50,
        "pairwise-single-v1": 100,
        "pairwise-swap-v1": 200,
        "rubric-swap-v1": 200,
    }
    assert all(check["status"] == "passed" for check in report["checks"])
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
    assert not list(tmp_path.glob(".*.tmp"))

    e0_plan = json.loads(bundle["plan"].read_text(encoding="utf-8"))
    input_by_sample = {
        row["sample_id"]: row["input"] for row in e0_plan["candidates"]
    }
    assert all(
        pair["source"]["video_sha256"] == input_by_sample[pair["sample_id"]]["video_checksum"]
        and pair["source"]["video_sha256"]
        != input_by_sample[pair["sample_id"]]["source_checksum"]
        for pair in bundle["pairs"]
    )


def test_source_frame_set_checksum_cannot_replace_mp4_checksum(
    e1_preparation_fixture, tmp_path
):
    bundle = e1_preparation_fixture
    e0_plan = json.loads(bundle["plan"].read_text(encoding="utf-8"))
    frame_set_sha = {
        row["sample_id"]: row["input"]["source_checksum"]
        for row in e0_plan["candidates"]
    }
    rows = [
        json.loads(line)
        for line in bundle["pairs_path"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        assert frame_set_sha[row["sample_id"]] != row["source"]["video_sha256"]
        row["source"]["video_sha256"] = frame_set_sha[row["sample_id"]]
    bad_pairs = _write_jsonl(tmp_path / "pairs-frame-set-sha.jsonl", rows)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, pairs=bad_pairs)
    assert "original SHA does not match pairs" in _failure_text(caught.value)


def test_tampered_source_original_file_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    source = next(iter(manifest["sources"].values()))
    corrupted = tmp_path / "corrupted-source.mp4"
    shutil.copy2(source["original_path"], corrupted)
    with corrupted.open("ab") as handle:
        handle.write(b"tampered")
    source["original_path"] = str(corrupted)
    manifest_path = _write_json(tmp_path / "manifest-source-tampered.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    text = _failure_text(caught.value)
    assert "source asset" in text and "original file SHA mismatch" in text


def test_tampered_candidate_sha_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    candidate = next(iter(manifest["candidates"].values()))
    candidate["original_sha256"] = "f" * 64
    manifest_path = _write_json(tmp_path / "manifest-candidate-sha.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "candidate asset" in _failure_text(caught.value)


def test_missing_frame_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    asset = next(iter(manifest["sources"].values()))
    asset["frames"][3]["path"] = str(tmp_path / "missing-frame.png")
    manifest_path = _write_json(tmp_path / "manifest-missing-frame.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "frame 3 is missing" in _failure_text(caught.value)


def test_tampered_frame_sha_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    asset = next(iter(manifest["candidates"].values()))
    asset["frames"][7]["sha256"] = "e" * 64
    manifest_path = _write_json(tmp_path / "manifest-frame-sha.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "frame 7 SHA mismatch" in _failure_text(caught.value)


def test_missing_contact_sheet_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    asset = next(iter(manifest["candidates"].values()))
    asset["contact_sheet"]["path"] = str(tmp_path / "missing-contact.jpg")
    manifest_path = _write_json(tmp_path / "manifest-missing-contact.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "contact sheet is missing" in _failure_text(caught.value)


@pytest.mark.parametrize("corruption", ["metadata", "checksum"])
def test_tampered_packet_metadata_or_checksum_is_rejected(
    e1_preparation_fixture, tmp_path, corruption
):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    packet = next(iter(manifest["pairs"].values()))
    if corruption == "metadata":
        metadata = json.loads(Path(packet["metadata_path"]).read_text(encoding="utf-8"))
        metadata["pair_id"] = "tampered-pair"
        packet["metadata_path"] = str(
            _write_json(tmp_path / "tampered-metadata.json", metadata)
        )
    else:
        packet["packet_checksum"] = "d" * 64
    manifest_path = _write_json(tmp_path / f"manifest-packet-{corruption}.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "packet" in _failure_text(caught.value)


def test_missing_mask_overlay_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    packet = next(iter(manifest["pairs"].values()))
    packet["mask_overlay"]["path"] = str(tmp_path / "missing-mask-overlay.jpg")
    manifest_path = _write_json(tmp_path / "manifest-missing-mask.json", manifest)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path)
    assert "mask overlay is missing" in _failure_text(caught.value)


def test_partial_manifest_missing_asset_writes_structured_failed_report(
    e1_preparation_fixture, tmp_path
):
    bundle = e1_preparation_fixture
    manifest = _manifest_copy(bundle, tmp_path)
    missing_source = next(iter(manifest["sources"]))
    del manifest["sources"][missing_source]
    manifest_path = _write_json(tmp_path / "manifest-missing-asset.json", manifest)
    output = tmp_path / "missing-asset-report.json"
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, packets=manifest_path, output=output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == caught.value.report
    assert report["status"] == "failed" and report["ready_for_smoke"] is False
    assert "manifest source keys do not exactly match" in _failure_text(caught.value)
    plan_check = next(
        check for check in report["checks"]
        if check["check_id"] == "plan.identities-counts-and-swap"
    )
    assert plan_check["status"] == "skipped"


def test_plan_request_and_method_split_counts_are_strict(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    rows = [json.loads(json.dumps(row)) for row in bundle["requests"]][:-1]
    bad_plan = _write_jsonl(tmp_path / "plan-549.jsonl", rows)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, plan=bad_plan)
    text = _failure_text(caught.value)
    assert "expected 550 requests, got 549" in text
    assert "method counts drifted" in text or "method/split counts drifted" in text


def test_duplicate_judge_key_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    rows = [json.loads(json.dumps(row)) for row in bundle["requests"]]
    rows[1]["judge_key"] = rows[0]["judge_key"]
    bad_plan = _write_jsonl(tmp_path / "plan-duplicate-key.jsonl", rows)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, plan=bad_plan)
    assert "judge keys are not unique" in _failure_text(caught.value)


def test_mixed_runtime_model_identity_is_rejected(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    rows = [json.loads(json.dumps(row)) for row in bundle["requests"]]
    rows[10]["model_revision"] = "mixed-revision"
    bad_plan = _write_jsonl(tmp_path / "plan-mixed-model.jsonl", rows)
    with pytest.raises(PreparationVerificationError) as caught:
        _run(bundle, plan=bad_plan)
    text = _failure_text(caught.value)
    assert "model identity differs from runtime" in text
    assert "plan mixes model_revision" in text


def test_existing_report_is_never_overwritten(e1_preparation_fixture, tmp_path):
    output = tmp_path / "existing-report.json"
    output.write_text("sentinel", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        _run(e1_preparation_fixture, output=output)
    assert output.read_text(encoding="utf-8") == "sentinel"


def _referenced_files(bundle) -> set[Path]:
    manifest = _manifest_copy(bundle, Path("."))
    paths = {
        bundle["pairs_path"],
        bundle["packets_dir"] / "media-manifest.json",
        bundle["judge_plan"],
        bundle["config"],
        bundle["runtime"],
    }
    for asset in [*manifest["sources"].values(), *manifest["candidates"].values()]:
        paths.add(Path(asset["original_path"]))
        paths.add(Path(asset["video"]["path"]))
        paths.add(Path(asset["contact_sheet"]["path"]))
        paths.update(Path(frame["path"]) for frame in asset["frames"])
    for packet in manifest["pairs"].values():
        paths.add(Path(packet["metadata_path"]))
        paths.add(Path(packet["mask_overlay"]["path"]))
    return {path.resolve() for path in paths}


def test_verifier_does_not_modify_any_input_checksum(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    paths = _referenced_files(bundle)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = _run(bundle, output=tmp_path / "readonly-report.json")
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert report["ready_for_smoke"] is True
    assert after == before


def test_cli_success_and_failed_report_exit_codes(e1_preparation_fixture, tmp_path):
    bundle = e1_preparation_fixture
    runner = CliRunner()
    output = tmp_path / "cli-pass.json"
    base = [
        "--pairs", str(bundle["pairs_path"]),
        "--packets", str(bundle["packets_dir"]),
        "--plan", str(bundle["judge_plan"]),
        "--config", str(bundle["config"]),
        "--runtime", str(bundle["runtime"]),
    ]
    passed = runner.invoke(app, ["verify-preparation", *base, "--output", str(output)])
    assert passed.exit_code == 0, passed.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["ready_for_smoke"] is True

    rows = [json.loads(json.dumps(row)) for row in bundle["requests"]][:-1]
    bad_plan = _write_jsonl(tmp_path / "cli-bad-plan.jsonl", rows)
    failed_output = tmp_path / "cli-failed.json"
    failed_args = [
        "--pairs", str(bundle["pairs_path"]),
        "--packets", str(bundle["packets_dir"]),
        "--plan", str(bad_plan),
        "--config", str(bundle["config"]),
        "--runtime", str(bundle["runtime"]),
        "--output", str(failed_output),
    ]
    failed = runner.invoke(app, ["verify-preparation", *failed_args])
    assert failed.exit_code == 1
    diagnostic = json.loads(failed_output.read_text(encoding="utf-8"))
    assert diagnostic["status"] == "failed"
    assert diagnostic["ready_for_smoke"] is False
