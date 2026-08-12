"""Artifact and reproducibility verification."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import imageio.v2 as imageio

from .hashing import sha256_file
from .models import CandidateRecord


def _probe_candidate(candidate: CandidateRecord) -> List[str]:
    errors: List[str] = []
    if candidate.status.value != "succeeded":
        return [f"status={candidate.status.value}: {candidate.error or 'no error recorded'}"]
    video = Path(candidate.video_path or "")
    frames = [Path(value) for value in candidate.frame_paths]
    if not video.is_file():
        errors.append("video missing")
    if len(frames) != 16 or not all(path.is_file() for path in frames):
        errors.append("expected 16 existing frame PNGs")
    if not errors:
        if sha256_file(video) != candidate.video_checksum:
            errors.append("video checksum mismatch")
        if [sha256_file(path) for path in frames] != candidate.frame_checksums:
            errors.append("frame checksum mismatch")
        reader = imageio.get_reader(video)
        try:
            metadata = reader.get_meta_data()
            decoded_count = 0
            first_shape = None
            for decoded_frame in reader:
                decoded_count += 1
                if first_shape is None:
                    first_shape = decoded_frame.shape[:2]
                if decoded_count > 16:
                    break
            if decoded_count != 16:
                errors.append(f"decoded frame count={decoded_count}{'+' if decoded_count > 16 else ''}")
            if first_shape != (512, 512):
                errors.append(f"decoded dimensions={first_shape}")
            if abs(float(metadata.get("fps", 0)) - 8.0) > 0.01:
                errors.append(f"fps={metadata.get('fps')}")
        finally:
            reader.close()
    return errors


def verify_candidates(candidates_path: Path, expected: int = 50, compare_path: Optional[Path] = None) -> Dict[str, Any]:
    candidates = [CandidateRecord.model_validate(value) for value in json.loads(candidates_path.read_text(encoding="utf-8"))]
    errors: Dict[str, List[str]] = {}
    if len(candidates) != expected:
        errors["__count__"] = [f"expected {expected}, got {len(candidates)}"]
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        errors["__ids__"] = ["candidate IDs are not unique"]
    for candidate in candidates:
        found = _probe_candidate(candidate)
        if found:
            errors[candidate.candidate_id] = found
    reproducible = None
    if compare_path is not None:
        other = {
            item.candidate_id: item
            for item in [CandidateRecord.model_validate(value) for value in json.loads(compare_path.read_text(encoding="utf-8"))]
        }
        mismatches = [
            candidate.candidate_id for candidate in candidates
            if candidate.candidate_id not in other or candidate.frame_checksums != other[candidate.candidate_id].frame_checksums
        ]
        reproducible = not mismatches
        if mismatches:
            errors["__reproducibility__"] = mismatches
    return {"valid": not errors, "count": len(candidates), "errors": errors, "reproducible": reproducible}
