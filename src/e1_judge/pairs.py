"""Build canonical schema-v2 E1 candidate pairs from immutable E0 outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

import yaml

from .models import CandidateRefV2, PairRecordV2, SourceRefV2


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_audit(path: Path) -> Dict[str, dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 50 or len({row["candidate_id"] for row in rows}) != 50:
        raise ValueError("E0 audit must contain 50 unique candidate rows")
    return {row["candidate_id"]: row for row in rows}


def build_pairs(plan: Path, candidates: Path, audit: Path, config: Path, output: Path) -> List[dict]:
    """Build 100 canonical pairs: 30 dev and 70 frozen-eval."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"pair output already exists: {output}")

    plan_data = _load_json(plan)
    candidate_records = _load_json(candidates)
    if not isinstance(candidate_records, list) or len(candidate_records) != 50:
        raise ValueError("E0 candidates must contain exactly 50 records")
    audit_rows = _load_audit(audit)
    cfg = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    if str(cfg.get("protocol_schema_version")) != "2":
        raise ValueError("E1 pair construction requires protocol schema v2")

    dev_samples = set(cfg["dev_samples"])
    frozen_samples = set(cfg["frozen_eval_samples"])
    randomization_seed = int(cfg["randomization_seed"])
    if dev_samples & frozen_samples or len(dev_samples) != 3 or len(frozen_samples) != 7:
        raise ValueError("E1 split must contain 3 disjoint dev and 7 frozen samples")

    plan_candidates = plan_data.get("candidates") or []
    if len(plan_candidates) != 50:
        raise ValueError("E0 plan must contain exactly 50 candidate tasks")
    plan_by_id = {task["candidate_id"]: task for task in plan_candidates}
    by_id = {record["candidate_id"]: record for record in candidate_records}
    if len(plan_by_id) != 50 or len(by_id) != 50 or set(plan_by_id) != set(by_id):
        raise ValueError("E0 plan/candidate IDs must be unique and identical")

    by_sample: Dict[str, List[str]] = {}
    for candidate_id, record in by_id.items():
        if record.get("status", "succeeded") != "succeeded":
            raise ValueError(f"candidate {candidate_id} is not succeeded")
        by_sample.setdefault(record["sample_id"], []).append(candidate_id)

    pairs: List[dict] = []
    for sample_id, candidate_ids in sorted(by_sample.items()):
        candidate_ids = sorted(candidate_ids)
        if len(candidate_ids) != 5:
            raise ValueError(f"sample {sample_id} has {len(candidate_ids)} candidates, expected 5")
        if sample_id not in dev_samples | frozen_samples:
            raise ValueError(f"sample {sample_id} is not assigned to an E1 split")
        first_input = plan_by_id[candidate_ids[0]]["input"]
        for candidate_id in candidate_ids[1:]:
            candidate_input = plan_by_id[candidate_id]["input"]
            identity_fields = ("sample_id", "task_type", "instruction", "target_caption", "source_checksum")
            for field in identity_fields:
                expected = sample_id if field == "sample_id" else first_input[field]
                actual = sample_id if field == "sample_id" else candidate_input[field]
                if actual != expected:
                    raise ValueError(f"sample {sample_id} has inconsistent {field}")

        source = SourceRefV2(
            sample_id=sample_id,
            video_path=str(first_input["source_video_path"]),
            video_sha256=str(first_input["source_checksum"]),
            mask_frame_paths=[str(path) for path in first_input.get("mask_frame_paths", [])],
        )
        split = "dev" if sample_id in dev_samples else "frozen-eval"
        pair_number = 0
        for left_index in range(5):
            for right_index in range(left_index + 1, 5):
                pair_number += 1
                a_id = candidate_ids[left_index]
                b_id = candidate_ids[right_index]
                a = by_id[a_id]
                b = by_id[b_id]
                unusable = (
                    audit_rows[a_id].get("usable_for_e1") != "yes"
                    or audit_rows[b_id].get("usable_for_e1") != "yes"
                )
                pair = PairRecordV2(
                    pair_id=f"{sample_id}-p{pair_number:02d}",
                    sample_id=sample_id,
                    task_type=first_input["task_type"],
                    instruction=first_input["instruction"],
                    target_caption=first_input["target_caption"],
                    source=source,
                    candidate_a=CandidateRefV2(
                        candidate_id=a_id,
                        video_path=str(a["video_path"]),
                        video_sha256=str(a["video_checksum"]),
                    ),
                    candidate_b=CandidateRefV2(
                        candidate_id=b_id,
                        video_path=str(b["video_path"]),
                        video_sha256=str(b["video_checksum"]),
                    ),
                    split=split,
                    randomization_seed=randomization_seed,
                    identical_media=a["video_checksum"] == b["video_checksum"],
                    excluded_reason="candidate_unusable_for_e1" if unusable else None,
                ).model_dump(mode="json")
                pairs.append(pair)

    if len(pairs) != 100:
        raise ValueError(f"expected 100 pairs, got {len(pairs)}")
    counts = {split: sum(pair["split"] == split for pair in pairs) for split in ("dev", "frozen-eval")}
    if counts != {"dev": 30, "frozen-eval": 70}:
        raise ValueError(f"expected dev/frozen counts 30/70, got {counts}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair, ensure_ascii=False, sort_keys=True) + "\n")
    return pairs
