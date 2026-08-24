"""E1 result verification."""

import json
from pathlib import Path
from typing import Optional


def verify_results(
    plan: Path, results: Path, human: Optional[Path], expect_requests: Optional[int], strict: bool
) -> None:
    """Verify judge results against the plan; optional human labels and strict mode."""
    plan_records = [json.loads(line) for line in Path(plan).read_text(encoding="utf-8").splitlines() if line.strip()]
    result_records = [json.loads(line) for line in Path(results).read_text(encoding="utf-8").splitlines() if line.strip()]

    if expect_requests is not None and len(result_records) != expect_requests:
        raise ValueError(f"expected {expect_requests} results, got {len(result_records)}")

    plan_ids = {record["request_id"] for record in plan_records}
    result_ids = [record.get("request_id") or record.get("judge_key") for record in result_records]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("duplicate result request IDs")
    if strict:
        missing = plan_ids - set(result_ids)
        if missing:
            raise ValueError(f"missing results for {len(missing)} planned requests")
        extra = set(result_ids) - plan_ids
        if extra:
            raise ValueError(f"unexpected results not in plan: {len(extra)}")

    if human is not None:
        human_records = [json.loads(line) for line in Path(human).read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(human_records) < 100:
            raise ValueError(f"expected >=100 human labels, got {len(human_records)}")
