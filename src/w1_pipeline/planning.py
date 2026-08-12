"""Deterministic inversion and candidate task planning."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .data import validate_prepared_manifest
from .hashing import canonical_sha256
from .models import GenerationConfig, InputRecord


def code_snapshot() -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, check=True, text=True).stdout
        return value + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unversioned"


def generation_key(record: InputRecord, config: GenerationConfig, snapshot: str) -> str:
    return canonical_sha256(
        {
            "source_checksum": record.source_checksum,
            "instruction": record.instruction,
            "target_caption": record.target_caption,
            "model_commit": config.model_commit,
            "anyv2v_commit": config.anyv2v_commit,
            "config": config.model_dump(mode="json"),
            "seed": config.seed,
            "code_snapshot": snapshot,
        }
    )


def build_plan(
    prepared_manifest: Path,
    seeds: List[int],
    backend: str,
    model_commit: str,
    anyv2v_commit: str,
    snapshot: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    records = validate_prepared_manifest(prepared_manifest)
    if backend == "anyv2v" and (len(anyv2v_commit) != 40 or len(model_commit) != 40):
        raise ValueError("AnyV2V execution requires exact 40-character AnyV2V and model commits")
    inversions, candidates = [], []
    for record in records:
        inversions.append(
            {
                "inversion_id": f"inv-{record.sample_id}",
                "sample_id": record.sample_id,
                "source_video_path": record.source_video_path,
                "source_checksum": record.source_checksum,
                "steps": 500,
                "artifact_dir": f"inversions/{record.sample_id}",
            }
        )
        for seed in seeds:
            config = GenerationConfig(
                backend=backend,
                model_commit=model_commit,
                anyv2v_commit=anyv2v_commit,
                seed=seed,
            )
            key = generation_key(record, config, snapshot)
            candidates.append(
                {
                    "candidate_id": f"{record.sample_id}-s{seed}",
                    "sample_id": record.sample_id,
                    "generation_key": key,
                    "input": record.model_dump(mode="json"),
                    "config": config.model_dump(mode="json"),
                    "artifact_dir": f"candidates/{record.sample_id}/seed-{seed}",
                    "code_snapshot": snapshot,
                }
            )
    return inversions, candidates


def write_plan(path: Path, inversions: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps({"inversions": inversions, "candidates": candidates}, indent=2), encoding="utf-8")
    temp.replace(path)

