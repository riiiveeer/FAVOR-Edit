import io
import tarfile
from pathlib import Path
from typing import Optional

import pytest

from defense_mvp.archive import extract_delivery_archive, inspect_archive, verify_archive_checksum
from w1_pipeline.hashing import sha256_file


CONFIG = Path("configs/defense_mvp/pilot.yaml")
PACKAGE_ID = "DEFENSE-MVP-E0-HANDOFF-v01"


def _sidecar(archive: Path, *, digest: Optional[str] = None) -> Path:
    path = archive.with_suffix(archive.suffix + ".sha256")
    path.write_text(f"{digest or sha256_file(archive)}  {archive.name}\n", encoding="utf-8")
    return path


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
