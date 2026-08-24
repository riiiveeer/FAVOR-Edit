"""Strict, schema-aware verification for E1 plans, results, and human labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import AdjudicatedLabelV2, JudgeRequestV2, JudgeResultV2
from .prompts import parse_response


def _read_jsonl(path: Path) -> List[dict]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return records


def _unique(records: List, attribute: str, label: str) -> Dict[str, object]:
    values: Dict[str, object] = {}
    for record in records:
        value = getattr(record, attribute)
        if value in values:
            raise ValueError(f"duplicate {label}: {value}")
        values[value] = record
    return values


def _verify_result_identity(request: JudgeRequestV2, result: JudgeResultV2) -> None:
    fields = (
        "judge_key", "pair_id", "candidate_id", "sample_id", "split", "method",
        "comparison_direction", "candidate_a_id", "candidate_b_id", "prompt_version",
        "prompt_checksum", "parser_version", "generation_parameters", "model_name",
        "model_revision", "model_manifest_sha256", "runtime_fingerprint",
        "frozen_protocol_fingerprint",
    )
    mismatches = [field for field in fields if getattr(request, field) != getattr(result, field)]
    if mismatches:
        raise ValueError(
            f"result identity mismatch for {request.request_id}: {', '.join(mismatches)}"
        )


def verify_results(
    plan: Path,
    results: Path,
    human: Optional[Path],
    expect_requests: Optional[int],
    strict: bool,
) -> None:
    """Verify exact identities, strict parses, completeness, and optional human coverage."""
    requests = [JudgeRequestV2.model_validate(record) for record in _read_jsonl(plan)]
    result_records = [JudgeResultV2.model_validate(record) for record in _read_jsonl(results)]
    request_by_id = _unique(requests, "request_id", "plan request_id")
    _unique(requests, "judge_key", "plan judge_key")
    result_by_id = _unique(result_records, "request_id", "result request_id")
    _unique(result_records, "judge_key", "result judge_key")

    if expect_requests is not None and len(result_records) != expect_requests:
        raise ValueError(f"expected {expect_requests} results, got {len(result_records)}")

    missing = set(request_by_id) - set(result_by_id)
    extra = set(result_by_id) - set(request_by_id)
    if extra:
        raise ValueError(f"unexpected results not in plan: {len(extra)}")
    if strict and missing:
        raise ValueError(f"missing results for {len(missing)} planned requests")

    for request_id, result in result_by_id.items():
        request = request_by_id[request_id]
        _verify_result_identity(request, result)
        if not strict:
            continue
        if result.status != "succeeded" or result.parsed is None:
            raise ValueError(f"strict verification rejects failed result {request_id}")
        raw_text = result.raw_response.get("text")
        reparsed = parse_response(result.method, raw_text)
        if reparsed != result.parsed:
            raise ValueError(f"parsed payload does not match raw response for {request_id}")
        if result.parse_error is not None:
            raise ValueError(f"succeeded result has parse_error for {request_id}")

    if strict and len(requests) == 550:
        split_counts = {
            split: sum(request.split == split for request in requests)
            for split in ("dev", "frozen-eval")
        }
        if split_counts != {"dev": 165, "frozen-eval": 385}:
            raise ValueError(f"full plan split counts must be 165/385, got {split_counts}")
    frozen_ids = {request.frozen_protocol_fingerprint for request in requests}
    if strict and len(frozen_ids) > 1:
        raise ValueError("plan mixes frozen and development protocol fingerprints")

    if human is None:
        return
    labels = [AdjudicatedLabelV2.model_validate(record) for record in _read_jsonl(human)]
    label_by_pair = _unique(labels, "pair_id", "human pair_id")
    if len(labels) != 100:
        raise ValueError(f"expected exactly 100 human labels, got {len(labels)}")
    planned_pairs = {request.pair_id for request in requests if request.pair_id is not None}
    if strict and set(label_by_pair) != planned_pairs:
        raise ValueError("human labels do not exactly cover the 100 planned pairs")
