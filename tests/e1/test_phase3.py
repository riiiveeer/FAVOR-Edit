"""Atomic phase-3 preparation wrapper tests with production-semantics tiny media."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from w1_pipeline.hashing import sha256_file

from e1_judge.cli import app
from e1_judge.hashing import canonical_sha256
from e1_judge.phase3 import (
    FAILURE_MARKER_NAME,
    PREPARATION_CHECKSUMS_NAME,
    PREPARATION_RECEIPT_NAME,
    PREPARATION_REPORT_NAME,
    Phase3PreparationError,
    _external_input_inventory,
    _rename_noreplace,
    _write_preparation_checksums,
    prepare_phase3,
    verify_preparation_checksums,
)
from e1_judge.preparation import verify_preparation
from e1_judge.runner import judge_key


def _model_manifest(path: Path) -> Path:
    path.write_text(
        "0" * 64 + "  config.json\n" + "1" * 64 + "  model.safetensors\n",
        encoding="utf-8",
    )
    return path


def _runtime_template() -> Path:
    return Path(__file__).parents[2] / "configs" / "e1" / "runtime-qwen25-vl-7b.example.yaml"


def _direct_args(bundle, tmp_path: Path, *, output_name: str, prepare_id: str):
    return {
        "e0_plan": bundle["plan"],
        "e0_candidates": bundle["candidates"],
        "e0_audit": bundle["audit"],
        "config": bundle["config"],
        "runtime_template": _runtime_template(),
        "model_manifest": _model_manifest(tmp_path / f"{prepare_id}-MODEL_SHA256SUMS"),
        "output_root": tmp_path / output_name,
        "prepare_id": prepare_id,
        "snapshot": "2" * 40,
    }


@pytest.fixture(scope="module")
def atomic_phase3_bundle(e1_v2_fixture, tmp_path_factory):
    root = tmp_path_factory.mktemp("atomic-phase3")
    output = root / "E1-judge-pilot-v02"
    model_manifest = _model_manifest(root / "MODEL_SHA256SUMS")
    before = _external_input_inventory(
        e1_v2_fixture["plan"], e1_v2_fixture["candidates"], e1_v2_fixture["audit"]
    )
    args = [
        "prepare-phase3",
        "--e0-plan", str(e1_v2_fixture["plan"]),
        "--e0-candidates", str(e1_v2_fixture["candidates"]),
        "--e0-audit", str(e1_v2_fixture["audit"]),
        "--config", str(e1_v2_fixture["config"]),
        "--runtime-template", str(_runtime_template()),
        "--model-manifest", str(model_manifest),
        "--output-root", str(output),
        "--prepare-id", "test-phase3-happy",
    ]
    with patch("e1_judge.phase3.code_snapshot", return_value="2" * 40):
        result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.stdout
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    after = _external_input_inventory(
        e1_v2_fixture["plan"], e1_v2_fixture["candidates"], e1_v2_fixture["audit"]
    )
    return {
        "root": output,
        "parent": root,
        "summary": summary,
        "model_manifest": model_manifest,
        "before": before,
        "after": after,
        "bundle": e1_v2_fixture,
    }


def test_atomic_happy_path_publishes_complete_verified_root(atomic_phase3_bundle):
    item = atomic_phase3_bundle
    root = item["root"]
    summary = item["summary"]
    staging = item["parent"] / ".E1-judge-pilot-v02.prepare-test-phase3-happy.staging"
    failure = item["parent"] / "E1-judge-pilot-v02.prepare-test-phase3-happy.failed"
    assert root.is_dir() and not staging.exists() and not failure.exists()
    assert summary["status"] == "passed" and summary["ready_for_smoke"] is True
    assert summary["counts"]["pairs"] == 100
    assert summary["counts"]["requests"] == 550
    for path in (
        root / "runtime-dev.yaml",
        root / "inputs" / "pairs.jsonl",
        root / "inputs" / "media-packets" / "media-manifest.json",
        root / "plans" / "judge-plan-development.jsonl",
        root / PREPARATION_REPORT_NAME,
        root / PREPARATION_RECEIPT_NAME,
        root / PREPARATION_CHECKSUMS_NAME,
    ):
        assert path.is_file()
    for directory in ("human", "runs", "logs"):
        assert (root / directory).is_dir()
        assert not any((root / directory).iterdir())


def test_published_identities_contain_no_staging_prefix_and_reverify(
    atomic_phase3_bundle,
):
    item = atomic_phase3_bundle
    root = item["root"]
    staging_text = str(
        item["parent"] / ".E1-judge-pilot-v02.prepare-test-phase3-happy.staging"
    )
    manifest_path = root / "inputs" / "media-packets" / "media-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked_text = [
        manifest_path.read_text(encoding="utf-8"),
        (root / "plans" / "judge-plan-development.jsonl").read_text(encoding="utf-8"),
        (root / PREPARATION_REPORT_NAME).read_text(encoding="utf-8"),
    ]
    checked_text.extend(
        Path(packet["metadata_path"]).read_text(encoding="utf-8")
        for packet in manifest["pairs"].values()
    )
    assert all(staging_text not in text for text in checked_text)
    assert all(
        str(root) in frame["path"]
        for asset in [*manifest["sources"].values(), *manifest["candidates"].values()]
        for frame in asset["frames"]
    )
    report = json.loads((root / PREPARATION_REPORT_NAME).read_text(encoding="utf-8"))
    assert report["verification_context"] == {
        "mode": "prepublish-staging",
        "declared_root": str(root),
        "physical_root_recorded_in": PREPARATION_RECEIPT_NAME,
    }
    direct = verify_preparation(
        root / "inputs" / "pairs.jsonl",
        root / "inputs" / "media-packets",
        root / "plans" / "judge-plan-development.jsonl",
        item["bundle"]["config"],
        root / "runtime-dev.yaml",
    )
    assert direct["status"] == "passed" and direct["ready_for_smoke"] is True


def test_packet_checksums_judge_keys_and_tree_checksums_recompute(atomic_phase3_bundle):
    root = atomic_phase3_bundle["root"]
    manifest = json.loads(
        (root / "inputs" / "media-packets" / "media-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    for pair_id, packet in manifest["pairs"].items():
        identity = {
            "schema_version": "2",
            "pair_id": pair_id,
            "source": manifest["sources"][packet["source_asset_id"]],
            "candidate_a": manifest["candidates"][packet["candidate_a_asset_id"]],
            "candidate_b": manifest["candidates"][packet["candidate_b_asset_id"]],
            "mask_overlay": packet["mask_overlay"],
        }
        assert packet["packet_checksum"] == canonical_sha256(identity)
        metadata = json.loads(Path(packet["metadata_path"]).read_text(encoding="utf-8"))
        assert metadata == {**identity, "packet_checksum": packet["packet_checksum"]}
    requests = [
        json.loads(line)
        for line in (root / "plans" / "judge-plan-development.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(requests) == 550
    assert all(request["judge_key"] == judge_key(request) for request in requests)
    assert verify_preparation_checksums(root) > 1200


def test_runtime_manifest_and_external_inputs_are_fixed(atomic_phase3_bundle):
    item = atomic_phase3_bundle
    root = item["root"]
    runtime = yaml.safe_load((root / "runtime-dev.yaml").read_text(encoding="utf-8"))
    receipt = json.loads((root / PREPARATION_RECEIPT_NAME).read_text(encoding="utf-8"))
    expected_manifest_sha = sha256_file(item["model_manifest"])
    assert runtime["model"]["manifest_sha256"] == expected_manifest_sha
    assert receipt["inputs"]["model_manifest"]["sha256"] == expected_manifest_sha
    assert receipt["inputs"]["external_inventory"]["file_count"] == 223
    assert receipt["external_inputs_unchanged"] is True
    assert item["before"] == item["after"]


@pytest.mark.parametrize("existing_kind", ["final", "staging", "failure"])
def test_existing_final_staging_or_failure_is_never_overwritten(
    e1_v2_fixture, tmp_path, existing_kind
):
    prepare_id = f"existing-{existing_kind}"
    output = tmp_path / "E1-existing"
    staging = tmp_path / f".E1-existing.prepare-{prepare_id}.staging"
    failure = tmp_path / f"E1-existing.prepare-{prepare_id}.failed"
    existing = {"final": output, "staging": staging, "failure": failure}[existing_kind]
    existing.mkdir()
    sentinel = existing / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    args = _direct_args(
        e1_v2_fixture, tmp_path, output_name="E1-existing", prepare_id=prepare_id
    )
    with pytest.raises(FileExistsError, match="already exists"):
        prepare_phase3(**args)
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_runtime_identity_drift_preserves_explicit_failed_artifact(
    e1_v2_fixture, tmp_path
):
    prepare_id = "runtime-drift"
    args = _direct_args(
        e1_v2_fixture, tmp_path, output_name="E1-runtime-drift", prepare_id=prepare_id
    )
    payload = yaml.safe_load(_runtime_template().read_text(encoding="utf-8"))
    payload["model"]["revision"] = "drifted-revision"
    bad_template = tmp_path / "runtime-drift.yaml"
    bad_template.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    args["runtime_template"] = bad_template
    with pytest.raises(Phase3PreparationError) as caught:
        prepare_phase3(**args)
    failure = tmp_path / f"E1-runtime-drift.prepare-{prepare_id}.failed"
    assert caught.value.stage == "materialize-runtime"
    assert caught.value.failure_root == failure and failure.is_dir()
    marker = json.loads((failure / FAILURE_MARKER_NAME).read_text(encoding="utf-8"))
    assert marker["status"] == "failed" and marker["ready_for_smoke"] is False
    assert not (tmp_path / "E1-runtime-drift").exists()


def test_packet_build_failure_preserves_partial_and_same_id_cannot_retry(
    e1_v2_fixture, tmp_path
):
    prepare_id = "packet-failure"
    args = _direct_args(
        e1_v2_fixture, tmp_path, output_name="E1-packet-failure", prepare_id=prepare_id
    )
    candidates = json.loads(e1_v2_fixture["candidates"].read_text(encoding="utf-8"))
    candidates[0]["video_checksum"] = "f" * 64
    bad_candidates = tmp_path / "candidates-bad-sha.json"
    bad_candidates.write_text(json.dumps(candidates), encoding="utf-8")
    args["e0_candidates"] = bad_candidates
    with pytest.raises(Phase3PreparationError) as caught:
        prepare_phase3(**args)
    failure = tmp_path / f"E1-packet-failure.prepare-{prepare_id}.failed"
    assert caught.value.stage == "build-packets"
    assert failure.is_dir() and (failure / FAILURE_MARKER_NAME).is_file()
    assert (failure / "inputs" / "media-packets").is_dir()
    assert not (tmp_path / "E1-packet-failure").exists()
    with pytest.raises(FileExistsError, match="failure root already exists"):
        prepare_phase3(**args)


@pytest.mark.parametrize("nonempty", [False, True])
def test_atomic_rename_noreplace_rejects_existing_target(tmp_path, nonempty):
    source = tmp_path / f"source-{nonempty}"
    target = tmp_path / f"target-{nonempty}"
    source.mkdir()
    (source / "source.txt").write_text("source", encoding="utf-8")
    target.mkdir()
    if nonempty:
        (target / "target.txt").write_text("target", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        _rename_noreplace(source, target)
    assert source.is_dir() and (source / "source.txt").is_file()
    assert target.is_dir()


def test_checksum_manifest_is_sorted_complete_and_rejects_tamper(tmp_path):
    root = tmp_path / "checksums"
    root.mkdir()
    (root / "b.txt").write_text("b", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    _write_preparation_checksums(root)
    lines = (root / PREPARATION_CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines()
    assert [line.split("  ", 1)[1] for line in lines] == ["a.txt", "b.txt"]
    assert verify_preparation_checksums(root) == 2
    (root / "a.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_preparation_checksums(root)


def test_cli_failure_is_nonzero_and_structured(e1_v2_fixture, tmp_path):
    output = tmp_path / "E1-cli-existing"
    output.mkdir()
    model_manifest = _model_manifest(tmp_path / "cli-MODEL_SHA256SUMS")
    result = CliRunner().invoke(
        app,
        [
            "prepare-phase3",
            "--e0-plan", str(e1_v2_fixture["plan"]),
            "--e0-candidates", str(e1_v2_fixture["candidates"]),
            "--e0-audit", str(e1_v2_fixture["audit"]),
            "--config", str(e1_v2_fixture["config"]),
            "--runtime-template", str(_runtime_template()),
            "--model-manifest", str(model_manifest),
            "--output-root", str(output),
            "--prepare-id", "cli-existing",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stderr.strip().splitlines()[-1])
    assert payload["status"] == "failed" and payload["ready_for_smoke"] is False
    assert payload["error_type"] == "FileExistsError"
