"""Build a lightweight E0 visual audit package from E0 plan/candidates outputs.

The audit package is a read-only derivative of the E0 inputs. It produces
contact sheets (4x4 grids of the 16 candidate frames) for all 50 candidates,
side-by-side source/candidate proxies for a fixed 22-candidate spot-check set,
an audit manifest, an empty human-audit CSV, a SHA256SUMS file, and a README.

This module never writes into the E0 input directories.
"""

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from PIL import Image

from .hashing import sha256_file
from .media_tools import ffmpeg_version, resolve_ffmpeg


class AuditError(Exception):
    """Raised when an audit package cannot be built or verified."""


# Fixed spot-check set from the execution manual (section 4.3).
FULL_SEED_SAMPLES: tuple = ("bear-white", "dog-tiger", "hiker-backpack")
SPOT_CHECK_SEED: int = 303

DIMENSIONS: tuple = (
    "faithfulness",
    "preservation",
    "temporal_consistency",
    "visual_quality",
)

FAILURE_TAGS: Set[str] = {
    "under_edit",
    "over_edit",
    "identity_loss",
    "background_change",
    "flicker",
    "motion_break",
    "artifact",
    "crop_failure",
    "cannot_judge",
}

CSV_HEADER: List[str] = [
    "candidate_id",
    "faithfulness",
    "preservation",
    "temporal_consistency",
    "visual_quality",
    "failure_tags",
    "systematic_failure",
    "usable_for_e1",
    "reviewer",
    "reviewed_at",
    "notes",
]


def spot_check_ids(plan_candidates: Iterable[Dict[str, Any]]) -> List[str]:
    """Return the fixed 22 candidate IDs for the side-by-side proxy set."""
    ids: Set[str] = set()
    for cand in plan_candidates:
        sample_id = cand["sample_id"]
        seed = int(cand["config"]["seed"])
        if sample_id in FULL_SEED_SAMPLES or seed == SPOT_CHECK_SEED:
            ids.add(cand["candidate_id"])
    return sorted(ids)


def _run_checked(cmd: List[str], what: str) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = tail[-5:] if tail else ["(no output)"]
        raise AuditError(f"{what} failed: {' | '.join(detail)}")


def _make_contact_sheet(ffmpeg_exe: str, video_path: Path, out_jpg: Path) -> None:
    _run_checked(
        [
            ffmpeg_exe, "-y", "-i", str(video_path),
            "-vf", "scale=160:160:flags=lanczos,tile=4x4:padding=2:margin=2",
            "-frames:v", "1", str(out_jpg),
        ],
        f"contact sheet {out_jpg.name}",
    )
    with Image.open(out_jpg) as img:
        img.load()
        if img.size[0] == 0 or img.size[1] == 0:
            raise AuditError(f"contact sheet {out_jpg.name} decoded to empty image")


def _make_proxy(ffmpeg_exe: str, source_path: Path, candidate_path: Path, out_mp4: Path) -> None:
    _run_checked(
        [
            ffmpeg_exe, "-y",
            "-i", str(source_path),
            "-i", str(candidate_path),
            "-filter_complex",
            (
                "[0:v]scale=256:256:flags=lanczos,setpts=PTS-STARTPTS[l];"
                "[1:v]scale=256:256:flags=lanczos,setpts=PTS-STARTPTS[r];"
                "[l][r]hstack[out]"
            ),
            "-map", "[out]",
            "-an",
            "-c:v", "libx264",
            "-crf", "30",
            "-r", "8",
            "-movflags", "+faststart",
            str(out_mp4),
        ],
        f"proxy {out_mp4.name}",
    )


def _validate_inputs(
    plan: Dict[str, Any], candidates: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    inversions = plan.get("inversions") or []
    plan_candidates = plan.get("candidates") or []
    if len(inversions) != 10:
        raise AuditError(f"plan must contain 10 inversions, got {len(inversions)}")
    if len(plan_candidates) != 50:
        raise AuditError(f"plan must contain 50 candidate tasks, got {len(plan_candidates)}")
    if len(candidates) != 50:
        raise AuditError(f"candidates must contain 50 records, got {len(candidates)}")

    if any(c.get("status") != "succeeded" for c in candidates):
        raise AuditError("all 50 candidates must be status=succeeded")

    plan_map: Dict[str, Dict[str, Any]] = {c["candidate_id"]: c for c in plan_candidates}
    if len(plan_map) != 50:
        raise AuditError("plan candidate IDs are not unique")

    ids = [c["candidate_id"] for c in candidates]
    if len(set(ids)) != 50:
        raise AuditError("candidates candidate IDs are not unique")

    for record in candidates:
        cid = record["candidate_id"]
        task = plan_map.get(cid)
        if task is None:
            raise AuditError(f"candidate {cid} not present in plan")
        if task["sample_id"] != record["sample_id"]:
            raise AuditError(f"candidate {cid}: sample_id mismatch between plan and candidates")
        if int(task["config"]["seed"]) != int(record["config"]["seed"]):
            raise AuditError(f"candidate {cid}: seed mismatch between plan and candidates")

        frames = record.get("frame_paths") or []
        checksums = record.get("frame_checksums") or []
        if len(frames) != 16 or len(checksums) != 16:
            raise AuditError(f"candidate {cid}: expected 16 frames/checksums")

        video = Path(record.get("video_path") or "")
        if not video.is_file():
            raise AuditError(f"candidate {cid}: video missing: {video}")
        if sha256_file(video) != record.get("video_checksum"):
            raise AuditError(f"candidate {cid}: video checksum mismatch")

        frame_paths = [Path(p) for p in frames]
        if not all(p.is_file() for p in frame_paths):
            raise AuditError(f"candidate {cid}: one or more frame files missing")
        if [sha256_file(p) for p in frame_paths] != list(checksums):
            raise AuditError(f"candidate {cid}: frame checksum mismatch")

    return plan_map


def build_audit(
    plan_path: Path,
    candidates_path: Path,
    output_dir: Path,
    code_snapshot: str,
) -> Dict[str, Any]:
    """Build the E0 audit package. Raises AuditError on any failure."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise AuditError(f"output directory already exists: {output_dir}")

    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    candidates = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    if not isinstance(candidates, list):
        raise AuditError("candidates file must contain a JSON list")

    plan_map = _validate_inputs(plan, candidates)
    try:
        ffmpeg_exe = resolve_ffmpeg()
    except (FileNotFoundError, RuntimeError) as exc:
        raise AuditError(f"ffmpeg unavailable: {exc}") from exc
    spot_ids = spot_check_ids(plan["candidates"])
    if len(spot_ids) != 22:
        raise AuditError(f"fixed spot-check set must be 22, got {len(spot_ids)}")

    contact_dir = output_dir / "contact-sheets"
    proxy_dir = output_dir / "proxies"
    contact_dir.mkdir(parents=True)
    proxy_dir.mkdir(parents=True)

    detected_ffmpeg_version = ffmpeg_version(ffmpeg_exe)
    generated_at = datetime.now().astimezone().isoformat()

    manifest_candidates: List[Dict[str, Any]] = []

    for record in candidates:
        cid = record["candidate_id"]
        task = plan_map[cid]
        task_input = task["input"]
        seed = int(record["config"]["seed"])

        contact_jpg = contact_dir / f"{cid}.jpg"
        _make_contact_sheet(ffmpeg_exe, Path(record["video_path"]), contact_jpg)

        entry: Dict[str, Any] = {
            "candidate_id": cid,
            "sample_id": record["sample_id"],
            "task_type": task_input["task_type"],
            "instruction": task_input["instruction"],
            "target_caption": task_input["target_caption"],
            "seed": seed,
            "edited_video": {
                "path": record["video_path"],
                "sha256": record["video_checksum"],
            },
            "contact_sheet": {
                "path": str(contact_jpg),
                "sha256": sha256_file(contact_jpg),
            },
            "proxy": None,
        }

        if cid in spot_ids:
            source_video = Path(task_input["source_video_path"])
            if not source_video.is_file():
                raise AuditError(f"candidate {cid}: source video missing: {source_video}")
            proxy_mp4 = proxy_dir / f"{cid}.mp4"
            _make_proxy(ffmpeg_exe, source_video, Path(record["video_path"]), proxy_mp4)
            entry["source_video"] = {
                "path": str(source_video),
                "sha256": sha256_file(source_video),
            }
            entry["proxy"] = {
                "path": str(proxy_mp4),
                "sha256": sha256_file(proxy_mp4),
            }

        manifest_candidates.append(entry)

    manifest = {
        "version": "E0-visual-audit-v01",
        "generated_at": generated_at,
        "ffmpeg_version": detected_ffmpeg_version,
        "code_snapshot": code_snapshot,
        "e0_inputs": {
            "plan_path": str(Path(plan_path).resolve()),
            "plan_sha256": sha256_file(Path(plan_path)),
            "candidates_path": str(Path(candidates_path).resolve()),
            "candidates_sha256": sha256_file(Path(candidates_path)),
        },
        "candidate_ids": sorted(c["candidate_id"] for c in candidates),
        "spot_check_ids": spot_ids,
        "candidates": manifest_candidates,
    }
    (output_dir / "audit-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Empty human-audit CSV: candidate_id pre-filled, score columns blank.
    with (output_dir / "audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADER)
        for record in candidates:
            writer.writerow([record["candidate_id"]] + [""] * (len(CSV_HEADER) - 1))

    _write_readme(output_dir, spot_ids)

    _write_sha256sums(output_dir)

    return {
        "output_dir": str(output_dir),
        "contact_sheets": len(candidates),
        "proxies": len(spot_ids),
        "spot_check_ids": spot_ids,
        "code_snapshot": code_snapshot,
    }


def _write_readme(output_dir: Path, spot_ids: List[str]) -> None:
    text = (
        "# E0 Visual Audit Package\n\n"
        "Read-only derivative of the E0 outputs. Do not modify E0 input directories.\n\n"
        "## Contents\n\n"
        "- `contact-sheets/<candidate_id>.jpg` — 4x4 grid of the 16 candidate frames (all 50 candidates).\n"
        f"- `proxies/<candidate_id>.mp4` — left=source, right=candidate, 512x256 @8fps (fixed 22 candidates: {', '.join(spot_ids)}).\n"
        "- `audit-manifest.json` — E0 input paths/checksums, code snapshot, candidate metadata and per-candidate media checksums.\n"
        "- `audit.csv` — human audit sheet. Header is fixed; score columns start empty.\n"
        "- `SHA256SUMS` — checksums of all package artifacts (excludes itself).\n\n"
        "## Human review protocol\n\n"
        "1. Browse all 50 contact sheets.\n"
        "2. Play all 22 side-by-side proxies in full (all 16 frames).\n"
        "3. For anomalies not in the 22-candidate set, open the original E0 `video.mp4`.\n"
        "4. Fill the four coarse dimensions (0/1/2), failure tags, and `usable_for_e1` (yes/no).\n"
        "5. Check whether all five seeds of a sample share the same systematic failure.\n\n"
        "The four dimensions use only `0` (clear failure), `1` (partial/slight), `2` (clearly good), "
        "or empty (not yet inspected). `usable_for_e1=no` is reserved for protocol-level problems "
        "(unjudgeable media, source/candidate mismatch, severe crop failure); under/over editing and "
        "low visual quality are real failures to keep, not reasons to exclude.\n\n"
        "Note: `SHA256SUMS` reflects the package at build time. After a human edits `audit.csv`, run "
        "`python scripts/build_e0_audit.py --verify-existing <audit-dir>` to validate the filled sheet; "
        "that command re-checks E0 input checksums rather than the stale package checksum.\n"
    )
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines: List[str] = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            rel = path.relative_to(output_dir).as_posix()
            lines.append(f"{sha256_file(path)}  {rel}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_existing(audit_dir: Path) -> Dict[str, Any]:
    """Validate a human-filled audit package. Raises AuditError on failure."""
    audit_dir = Path(audit_dir)
    if not audit_dir.is_dir():
        raise AuditError(f"audit dir does not exist: {audit_dir}")

    manifest_path = audit_dir / "audit-manifest.json"
    csv_path = audit_dir / "audit.csv"
    if not manifest_path.is_file():
        raise AuditError(f"audit manifest missing: {manifest_path}")
    if not csv_path.is_file():
        raise AuditError(f"audit.csv missing: {csv_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Re-check E0 input checksums (section 6).
    plan_path = Path(manifest["e0_inputs"]["plan_path"])
    candidates_path = Path(manifest["e0_inputs"]["candidates_path"])
    if not plan_path.is_file() or not candidates_path.is_file():
        raise AuditError("E0 input file referenced by manifest no longer exists")
    if sha256_file(plan_path) != manifest["e0_inputs"]["plan_sha256"]:
        raise AuditError("E0 plan checksum changed")
    if sha256_file(candidates_path) != manifest["e0_inputs"]["candidates_sha256"]:
        raise AuditError("E0 candidates checksum changed")

    rows = _read_csv(csv_path)
    expected_ids = set(manifest["candidate_ids"])
    spot_ids = set(manifest["spot_check_ids"])

    if len(rows) != 50 or len(expected_ids) != 50:
        raise AuditError("audit.csv must contain exactly 50 rows")
    row_ids = [row["candidate_id"] for row in rows]
    if len(set(row_ids)) != 50:
        raise AuditError("audit.csv candidate IDs are not unique")
    if set(row_ids) != expected_ids:
        raise AuditError("audit.csv candidate IDs do not match audit manifest")

    errors: List[str] = []
    for row in rows:
        cid = row["candidate_id"]
        if not row["reviewer"]:
            errors.append(f"{cid}: missing reviewer")
        if not row["reviewed_at"]:
            errors.append(f"{cid}: missing reviewed_at")
        if row["usable_for_e1"] not in {"yes", "no"}:
            errors.append(f"{cid}: usable_for_e1 must be yes/no")

        tags = [t.strip() for t in row["failure_tags"].split(";") if t.strip()]
        bad = [t for t in tags if t not in FAILURE_TAGS]
        if bad:
            errors.append(f"{cid}: unknown failure tags {bad}")

        if cid in spot_ids:
            for dim in DIMENSIONS:
                if row[dim] not in {"0", "1", "2"}:
                    errors.append(f"{cid}: {dim} must be 0/1/2 for spot-check candidate")

    if errors:
        raise AuditError("audit verification failed: " + "; ".join(errors))

    return {"valid": True, "rows": len(rows), "spot_check_ids": sorted(spot_ids)}


def _read_csv(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_HEADER:
            raise AuditError(f"audit.csv header mismatch: {reader.fieldnames}")
        return list(reader)
