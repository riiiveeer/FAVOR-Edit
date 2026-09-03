"""Safe, checksum-gated extraction of the server E0 handoff tar."""

from __future__ import annotations

import json
import os
import re
import shutil
import tarfile
import uuid
from pathlib import Path, PurePosixPath
from typing import List, Optional, Tuple

from w1_pipeline.hashing import sha256_file

from .compat import CompatibilityInput, CompatibilityProfile, resolve_compatibility_profile
from .ingest import verify_delivery
from .io import rename_noreplace, write_json


PACKAGE_ID = "DEFENSE-MVP-E0-HANDOFF-v01"
MAX_MEMBERS = 5000
MAX_TOTAL_BYTES = 20 * 1024 * 1024 * 1024
SIDECAR_LINE = re.compile(r"^([0-9a-f]{64})  ([^/\\]+)$")


def verify_archive_checksum(archive: Path, checksum_file: Path) -> str:
    archive, checksum_file = Path(archive), Path(checksum_file)
    if not archive.is_file() or archive.is_symlink():
        raise ValueError("archive must be a regular file")
    if not checksum_file.is_file() or checksum_file.is_symlink():
        raise ValueError("archive checksum must be a regular file")
    lines = checksum_file.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1:
        raise ValueError("archive checksum sidecar must contain exactly one line")
    match = SIDECAR_LINE.fullmatch(lines[0])
    if match is None:
        raise ValueError("archive checksum sidecar must use '<sha256>  <filename>'")
    expected, name = match.groups()
    if name != archive.name:
        raise ValueError("archive checksum filename does not match archive")
    actual = sha256_file(archive)
    if actual != expected:
        raise ValueError("archive checksum mismatch")
    return actual


def _safe_member_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise ValueError(f"unsafe tar member path: {name!r}")
    normalized = name.rstrip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe tar member path: {name!r}")
    if "//" in normalized or path.as_posix() != normalized:
        raise ValueError(f"non-canonical tar member path: {name!r}")
    return path


def _inspect_archive(
    archive: Path, profile: Optional[CompatibilityProfile]
) -> Tuple[List[tarfile.TarInfo], int, bool]:
    with tarfile.open(Path(archive), mode="r:") as handle:
        members = handle.getmembers()
    if not members or len(members) > MAX_MEMBERS:
        raise ValueError(f"archive member count must be 1..{MAX_MEMBERS}")
    names, total = [], 0
    for member in members:
        path = _safe_member_name(member.name)
        if profile is None and path.parts[0] != PACKAGE_ID:
            raise ValueError("archive must contain exactly the fixed package top directory")
        if not (member.isdir() or member.isfile()):
            raise ValueError(f"tar links/devices/fifos are forbidden: {member.name}")
        names.append(path.as_posix())
        if member.isfile():
            total += member.size
    if len(names) != len(set(names)):
        raise ValueError("archive member paths must be unique")
    if total <= 0 or total > MAX_TOTAL_BYTES:
        raise ValueError(f"archive expanded bytes must be 1..{MAX_TOTAL_BYTES}")
    root_flat = profile is not None
    if profile is not None:
        if len(members) != profile.archive_members or total != profile.archive_expanded_bytes:
            raise ValueError("compatibility archive cardinality/size drifted")
        if any(not member.isfile() for member in members):
            raise ValueError("compatibility archive must contain only regular root-flat files")
        required = {
            "PACKAGE_MANIFEST.json", "PACKAGE_VERIFICATION.json", "PACKAGE_SHA256SUMS",
            "PACKAGE_BUILD_LOG.txt", "PACKAGE_BUILD_SCRIPT.py", "README.md",
        }
        if not required.issubset(names) or any(name == PACKAGE_ID or name.startswith(f"{PACKAGE_ID}/") for name in names):
            raise ValueError("compatibility archive is not the pinned root-flat layout")
    return members, total, root_flat


def inspect_archive(archive: Path) -> Tuple[List[tarfile.TarInfo], int]:
    members, total, _ = _inspect_archive(archive, None)
    return members, total


def extract_delivery_archive(
    archive: Path, checksum_file: Path, config_path: Path, output: Path,
    compatibility_profile: CompatibilityInput = None,
) -> dict:
    archive = Path(archive).resolve()
    checksum_file = Path(checksum_file).resolve()
    output = Path(output).resolve()
    if os.path.lexists(output):
        raise FileExistsError(f"extraction output already exists: {output}")
    profile = resolve_compatibility_profile(compatibility_profile)
    compatibility_receipt = output.with_name(f"{output.name}.compatibility-receipt.json")
    if profile is not None and os.path.lexists(compatibility_receipt):
        raise FileExistsError(f"compatibility receipt already exists: {compatibility_receipt}")
    archive_sha = verify_archive_checksum(archive, checksum_file)
    if profile is not None and archive_sha != profile.archive_sha256:
        raise ValueError("compatibility archive fingerprint drifted")
    members, total_bytes, root_flat = _inspect_archive(archive, profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging = output.parent / f".{output.name}.extract-{token}.staging"
    failed = output.parent / f".{output.name}.extract-{token}.failed"
    receipt_staging = output.parent / f".{output.name}.compat-{token}.staging.json"
    if os.path.lexists(staging) or os.path.lexists(failed):
        raise FileExistsError("unique extraction staging/failure path already exists")
    staging.mkdir()
    try:
        with tarfile.open(archive, mode="r:") as handle:
            by_name = {member.name: member for member in handle.getmembers()}
            for inspected in members:
                member = by_name[inspected.name]
                path = _safe_member_name(member.name)
                relative_parts = path.parts if root_flat else path.parts[1:]
                if not relative_parts:
                    continue
                target = staging.joinpath(*relative_parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = handle.extractfile(member)
                if source is None:
                    raise ValueError(f"unable to read regular tar member: {member.name}")
                with source, target.open("xb") as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                if target.stat().st_size != member.size:
                    raise ValueError(f"extracted size mismatch: {member.name}")
        _, report = verify_delivery(staging, config_path, profile)
        if sha256_file(archive) != archive_sha:
            raise RuntimeError("archive changed during extraction")
        receipt = {
            "status": "passed", "ready_for_ingest": True,
            "archive_sha256": archive_sha, "archive_members": len(members),
            "expanded_bytes": total_bytes, "output": str(output),
            "package_manifest_sha256": report["package_manifest_sha256"],
            "package_sums_sha256": report["package_sums_sha256"],
        }
        if profile is not None:
            receipt["compatibility_profile"] = profile.profile_id
            receipt["compatibility_warnings"] = report["compatibility"]["deviations"]
            write_json(receipt_staging, {
                "schema_version": "1",
                "status": "accepted-with-pinned-compatibility",
                "package_id": PACKAGE_ID,
                "archive_sha256": archive_sha,
                "archive_members": len(members),
                "expanded_bytes": total_bytes,
                "external_archive_unchanged": True,
                **report["compatibility"],
            })
        rename_noreplace(staging, output)
        if profile is not None:
            rename_noreplace(receipt_staging, compatibility_receipt)
            receipt["compatibility_receipt"] = str(compatibility_receipt)
        return receipt
    except Exception as exc:
        if receipt_staging.exists():
            receipt_staging.unlink()
        if staging.exists():
            (staging / "ARCHIVE_EXTRACTION_FAILED.json").write_text(
                json.dumps({"status": "failed", "error": str(exc)}, indent=2) + "\n",
                encoding="utf-8",
            )
            rename_noreplace(staging, failed)
        raise
