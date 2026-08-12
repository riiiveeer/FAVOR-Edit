"""Helpers for preparing guarded offline delivery experiments."""

import json
from pathlib import Path


def make_smoke_plan(input_path: Path, output_path: Path) -> None:
    """Select the first candidate and its matching inversion from a full plan."""
    plan = json.loads(input_path.read_text(encoding="utf-8"))
    candidates = plan.get("candidates", [])
    inversions = plan.get("inversions", [])
    if not candidates or not inversions:
        raise ValueError("input plan must contain candidates and inversions")
    candidate = candidates[0]
    inversion = next((item for item in inversions if item["sample_id"] == candidate["sample_id"]), None)
    if inversion is None:
        raise ValueError("matching inversion not found for first candidate")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps({"inversions": [inversion], "candidates": [candidate]}, indent=2), encoding="utf-8")
    temporary.replace(output_path)

