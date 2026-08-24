"""E1 pair construction: 100 unordered pairs with deterministic display randomization."""

import csv
import json
from pathlib import Path
from typing import Dict, List

import yaml

from .hashing import canonical_sha256
from .models import PairRecord

SEEDS = [101, 202, 303, 404, 505]
PAIR_SCHEMA_VERSION = "1"


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_audit(path: Path) -> Dict[str, dict]:
    rows = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["candidate_id"]] = row
    return rows


def _display_direction(pair_id: str, annotator_id: str, seed: int) -> str:
    digest = canonical_sha256(f"{pair_id}|{annotator_id}|{seed}")
    return "a_vs_b" if int(digest, 16) % 2 == 0 else "b_vs_a"


def build_pairs(plan: Path, candidates: Path, audit: Path, config: Path, output: Path) -> List[dict]:
    """Build the 100 unordered pairs (30 dev + 70 frozen-eval)."""
    plan_data = _load_json(plan)
    cands = _load_json(candidates)
    audit_rows = _load_audit(audit)
    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))

    dev_samples = set(cfg["dev_samples"])
    frozen_samples = set(cfg["frozen_eval_samples"])

    by_id = {record["candidate_id"]: record for record in cands}
    by_sample: Dict[str, List[str]] = {}
    for record in cands:
        by_sample.setdefault(record["sample_id"], []).append(record["candidate_id"])

    plan_by_id = {task["candidate_id"]: task for task in plan_data["candidates"]}

    pairs: List[dict] = []
    for sample_id, candidate_ids in sorted(by_sample.items()):
        candidate_ids = sorted(candidate_ids)
        if len(candidate_ids) != 5:
            raise ValueError(f"sample {sample_id} has {len(candidate_ids)} candidates, expected 5")
        task_input = plan_by_id[candidate_ids[0]]["input"]
        task_type = task_input["task_type"]
        instruction = task_input["instruction"]
        target_caption = task_input["target_caption"]
        source_video_path = task_input["source_video_path"]
        source_checksum = task_input["source_checksum"]
        mask_paths = task_input.get("mask_frame_paths", [])

        split = "dev" if sample_id in dev_samples else "frozen-eval"
        if sample_id not in dev_samples and sample_id not in frozen_samples:
            raise ValueError(f"sample {sample_id} not assigned to dev or frozen-eval")

        for index in range(len(candidate_ids)):
            for jndex in range(index + 1, len(candidate_ids)):
                left_id = candidate_ids[index]
                right_id = candidate_ids[jndex]
                left = by_id[left_id]
                right = by_id[right_id]
                pair_id = f"{sample_id}-p{index}{jndex}"

                left_usable = audit_rows.get(left_id, {}).get("usable_for_e1", "") == "yes"
                right_usable = audit_rows.get(right_id, {}).get("usable_for_e1", "") == "yes"
                excluded_reason = None
                if not left_usable or not right_usable:
                    excluded_reason = "candidate_unusable_for_e1"

                identical_media = left.get("video_checksum") == right.get("video_checksum")

                pair = PairRecord(
                    pair_id=pair_id,
                    sample_id=sample_id,
                    task_type=task_type,
                    instruction=instruction,
                    target_caption=target_caption,
                    source_video_path=source_video_path,
                    source_checksum=source_checksum,
                    mask_paths=mask_paths,
                    candidate_left_id=left_id,
                    candidate_left_checksum=left["video_checksum"],
                    candidate_left_path=left["video_path"],
                    candidate_right_id=right_id,
                    candidate_right_checksum=right["video_checksum"],
                    candidate_right_path=right["video_path"],
                    canonical_candidate_a_id=min(left_id, right_id),
                    canonical_candidate_b_id=max(left_id, right_id),
                    display_direction=_display_direction(pair_id, "canonical", 0),
                    split=split,
                    randomization_seed=0,
                    pair_schema_version=PAIR_SCHEMA_VERSION,
                    identical_media=identical_media,
                    excluded_reason=excluded_reason,
                )
                pairs.append(pair.model_dump(mode="json"))

    if len(pairs) != 100:
        raise ValueError(f"expected 100 pairs, got {len(pairs)}")
    dev_count = sum(1 for p in pairs if p["split"] == "dev")
    frozen_count = sum(1 for p in pairs if p["split"] == "frozen-eval")
    if dev_count != 30 or frozen_count != 70:
        raise ValueError(f"expected 30 dev + 70 frozen, got {dev_count} + {frozen_count}")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with Path(output).open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair, ensure_ascii=False, sort_keys=True) + "\n")
    return pairs
