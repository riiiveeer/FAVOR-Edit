import json
import io
import tarfile
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple

import pytest

from defense_mvp.archive import extract_delivery_archive, inspect_archive, verify_archive_checksum
from defense_mvp.compat import CompatibilityProfile, resolve_compatibility_profile
from defense_mvp.ingest import ingest_delivery, verify_delivery
from w1_pipeline.hashing import sha256_file


CONFIG = Path("configs/defense_mvp/pilot.yaml")
PACKAGE_ID = "DEFENSE-MVP-E0-HANDOFF-v01"


def _sidecar(archive: Path, *, digest: Optional[str] = None) -> Path:
    path = archive.with_suffix(archive.suffix + ".sha256")
    path.write_text(f"{digest or sha256_file(archive)}  {archive.name}\n", encoding="utf-8")
    return path


def _rewrite_sums(root: Path) -> None:
    rows = []
    for path in sorted(
        (value for value in root.rglob("*")
         if value.is_file() and value.name != "PACKAGE_SHA256SUMS"),
        key=lambda value: value.relative_to(root).as_posix(),
    ):
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "PACKAGE_SHA256SUMS").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )


def _legacy_archive(delivery: Path, tmp_path: Path) -> Tuple[Path, Path, CompatibilityProfile]:
    manifest_path = delivery / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_order = [
        "bear-white", "bus-red", "elephant-pink", "classic-car-blue",
        "dog-tiger", "horse-zebra", "mallard-swan",
        "hiker-backpack", "rider-helmet", "car-headlights",
    ]
    samples = {item["sample_id"]: item for item in manifest["samples"]}
    candidates = {
        (item["sample_id"], item["seed"]): item for item in manifest["candidates"]
    }
    manifest["samples"] = [samples[sample_id] for sample_id in raw_order]
    manifest["candidates"] = [
        candidates[(sample_id, seed)] for sample_id in raw_order
        for seed in [101, 202, 303, 404, 505]
    ]
    manifest["role_counts"] = dict(Counter(item["role"] for item in manifest["files"]))
    for sample in manifest["samples"]:
        source = sample["source_frames"]
        masks = sample["masks"]
        sample["source_frames"] = [
            {"relative_path": path, "sha256": digest}
            for path, digest in zip(source["relative_paths"], source["sha256"])
        ]
        sample["source_combined_checksum"] = source["combined_sha256"]
        sample["masks"] = [
            {"relative_path": path, "sha256": digest}
            for path, digest in zip(masks["relative_paths"], masks["sha256"])
        ]
        sample["mask_combined_checksum"] = masks["combined_sha256"]
    for candidate in manifest["candidates"]:
        frames = candidate["frames"]
        candidate["frames"] = [
            {"relative_path": path, "sha256": digest}
            for path, digest in zip(frames["relative_paths"], frames["sha256"])
        ]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    verification_path = delivery / "PACKAGE_VERIFICATION.json"
    verification = {
        "package_id": PACKAGE_ID, "ready_for_transfer": True,
        "checks": [
            {"id": f"v{index}", "status": "pass", "summary": f"check {index}"}
            for index in range(1, 16)
        ],
        "warnings": [], "failures": [], "published_at": None,
    }
    verification_path.write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    _rewrite_sums(delivery)
    declared_verification = sha256_file(verification_path)
    verification["published_at"] = "2026-09-02T00:00:00Z"
    verification_path.write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    actual_verification = sha256_file(verification_path)
    archive = tmp_path / f"{PACKAGE_ID}.tar"
    with tarfile.open(archive, mode="w:") as handle:
        for path in sorted(value for value in delivery.rglob("*") if value.is_file()):
            handle.add(path, arcname=path.relative_to(delivery).as_posix(), recursive=False)
    checksum = _sidecar(archive)
    with tarfile.open(archive, mode="r:") as handle:
        members = handle.getmembers()
    profile = CompatibilityProfile(
        profile_id="fixture-compat-v01",
        archive_sha256=sha256_file(archive),
        manifest_sha256=sha256_file(manifest_path),
        package_sums_sha256=sha256_file(delivery / "PACKAGE_SHA256SUMS"),
        verification_declared_sha256=declared_verification,
        verification_actual_sha256=actual_verification,
        archive_members=len(members),
        archive_expanded_bytes=sum(item.size for item in members),
        checksum_rows=len((delivery / "PACKAGE_SHA256SUMS").read_text(encoding="utf-8").splitlines()),
    )
    return archive, checksum, profile


def test_safe_archive_extracts_and_reverifies(handoff_factory, tmp_path: Path) -> None:
    delivery = handoff_factory()
    archive = tmp_path / f"{PACKAGE_ID}.tar"
    with tarfile.open(archive, mode="w:") as handle:
        handle.add(delivery, arcname=PACKAGE_ID, recursive=True)
    checksum = _sidecar(archive)
    output = tmp_path / "extracted"
    receipt = extract_delivery_archive(archive, checksum, CONFIG, output)
    assert receipt["ready_for_ingest"] is True
    assert (output / "PACKAGE_MANIFEST.json").is_file()


def test_archive_checksum_mismatch_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / f"{PACKAGE_ID}.tar"
    with tarfile.open(archive, mode="w:"):
        pass
    checksum = _sidecar(archive, digest="0" * 64)
    with pytest.raises(ValueError, match="archive checksum mismatch"):
        verify_archive_checksum(archive, checksum)


def test_archive_path_escape_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / f"{PACKAGE_ID}.tar"
    payload = b"escape"
    with tarfile.open(archive, mode="w:") as handle:
        member = tarfile.TarInfo(f"{PACKAGE_ID}/../escape.txt")
        member.size = len(payload)
        handle.addfile(member, io.BytesIO(payload))
    with pytest.raises(ValueError, match="unsafe tar member path"):
        inspect_archive(archive)


def test_archive_symlink_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / f"{PACKAGE_ID}.tar"
    with tarfile.open(archive, mode="w:") as handle:
        member = tarfile.TarInfo(f"{PACKAGE_ID}/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "/outside"
        handle.addfile(member)
    with pytest.raises(ValueError, match="links/devices/fifos are forbidden"):
        inspect_archive(archive)


def test_pinned_compatibility_extracts_normalizes_and_ingests(
    handoff_factory, tmp_path: Path
) -> None:
    delivery = handoff_factory()
    archive, checksum, profile = _legacy_archive(delivery, tmp_path)
    with pytest.raises(ValueError, match="fixed package top directory"):
        inspect_archive(archive)
    output = tmp_path / "compat-extracted"
    receipt = extract_delivery_archive(
        archive, checksum, CONFIG, output, profile
    )
    assert receipt["compatibility_profile"] == "fixture-compat-v01"
    assert Path(receipt["compatibility_receipt"]).is_file()
    manifest, report = verify_delivery(output, CONFIG, profile)
    assert [item.sample_id for item in manifest.samples][-3:] == [
        "dog-tiger", "horse-zebra", "mallard-swan",
    ]
    assert len(report["compatibility"]["package_sum_mismatches"]) == 1
    ingest = tmp_path / "compat-ingest"
    ingest_receipt = ingest_delivery(output, CONFIG, ingest, profile)
    assert ingest_receipt["ready_for_scoring"] is True
    assert (ingest / "compatibility-receipt.json").is_file()


def test_compatibility_rejects_fingerprint_or_payload_drift(
    handoff_factory, tmp_path: Path
) -> None:
    delivery = handoff_factory()
    archive, checksum, profile = _legacy_archive(delivery, tmp_path)
    wrong = replace(profile, archive_sha256="0" * 64)
    with pytest.raises(ValueError, match="archive fingerprint drifted"):
        extract_delivery_archive(archive, checksum, CONFIG, tmp_path / "wrong", wrong)

    output = tmp_path / "compat-extracted"
    extract_delivery_archive(archive, checksum, CONFIG, output, profile)
    target = next((output / "media/candidates").rglob("video.mp4"))
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="package checksum mismatch"):
        verify_delivery(output, CONFIG, profile)


@pytest.mark.parametrize("mutation", ["candidate_id", "seed", "path", "count", "original", "verification", "sums"])
def test_pinned_compatibility_rejects_control_and_identity_mutation(
    handoff_factory, tmp_path: Path, mutation: str,
) -> None:
    delivery = handoff_factory()
    _, _, profile = _legacy_archive(delivery, tmp_path)
    manifest_path = delivery / "PACKAGE_MANIFEST.json"
    if mutation in {"candidate_id", "seed", "path", "count"}:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if mutation == "candidate_id":
            payload["candidates"][0]["candidate_id"] = "changed-id"
        elif mutation == "seed":
            payload["candidates"][0]["seed"] = 999
        elif mutation == "path":
            payload["candidates"][0]["video"]["relative_path"] = "../outside.mp4"
        else:
            payload["counts"]["candidates"] = 49
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    elif mutation == "original":
        target = delivery / "metadata/original-candidates.json"
        target.write_bytes(target.read_bytes() + b"\n")
    else:
        target = delivery / ("PACKAGE_VERIFICATION.json" if mutation == "verification" else "PACKAGE_SHA256SUMS")
        target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="fingerprint drifted|package checksum mismatch"):
        verify_delivery(delivery, CONFIG, profile)


def test_unknown_compatibility_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown compatibility profile"):
        resolve_compatibility_profile("arbitrary-package-v01")
