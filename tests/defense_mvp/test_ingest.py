import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from defense_mvp.cli import app
from defense_mvp.ingest import ingest_delivery, verify_delivery


CONFIG = Path("configs/defense_mvp/pilot.yaml")


def _rewrite_sums(root: Path) -> None:
    from w1_pipeline.hashing import sha256_file

    rows = []
    for path in sorted((value for value in root.rglob("*")
                        if value.is_file() and value.name != "PACKAGE_SHA256SUMS"),
                       key=lambda value: value.relative_to(root).as_posix()):
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "PACKAGE_SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_verify_and_ingest_complete_delivery(handoff_factory, tmp_path: Path) -> None:
    delivery = handoff_factory()
    manifest, report = verify_delivery(delivery, CONFIG)
    assert len(manifest.samples) == 10 and len(manifest.candidates) == 50
    assert report["ready_for_ingest"] is True
    output = tmp_path / "ingested"
    receipt = ingest_delivery(delivery, CONFIG, output)
    assert receipt["ready_for_scoring"] is True
    normalized = json.loads((output / "normalized-manifest.json").read_text(encoding="utf-8"))
    assert len(normalized["samples"]) == 10 and len(normalized["candidates"]) == 50
    assert (output / "INGEST_SHA256SUMS").is_file()


def test_delivery_tamper_is_rejected(handoff_factory) -> None:
    delivery = handoff_factory()
    target = next((delivery / "media/candidates").rglob("video.mp4"))
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="package checksum mismatch"):
        verify_delivery(delivery, CONFIG)


def test_unsafe_manifest_path_is_rejected(handoff_factory) -> None:
    delivery = handoff_factory()
    path = delivery / "PACKAGE_MANIFEST.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["samples"][0]["source_video"]["relative_path"] = "../escape.mp4"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _rewrite_sums(delivery)
    with pytest.raises(ValueError, match="unsafe package relative path"):
        verify_delivery(delivery, CONFIG)


def test_ingest_rejects_existing_output(handoff_factory, tmp_path: Path) -> None:
    delivery = handoff_factory()
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        ingest_delivery(delivery, CONFIG, output)


def test_manifest_semantic_drift_is_rejected(handoff_factory) -> None:
    delivery = handoff_factory()
    path = delivery / "PACKAGE_MANIFEST.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["samples"][0]["instruction"] = "drifted instruction"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _rewrite_sums(delivery)
    with pytest.raises(ValueError, match="sample metadata mismatch"):
        verify_delivery(delivery, CONFIG)


def test_verify_delivery_cli(handoff_factory) -> None:
    delivery = handoff_factory()
    result = CliRunner().invoke(app, [
        "verify-delivery", "--delivery", str(delivery), "--config", str(CONFIG),
    ])
    assert result.exit_code == 0, result.output
    assert '"ready_for_ingest": true' in result.output
