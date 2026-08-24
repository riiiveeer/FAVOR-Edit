"""End-to-end analysis, freeze, gate, report, and verification tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from e1_judge.metrics import build_predictions
from e1_judge.models import JudgeRequestV2, JudgeResultV2, PairRecordV2
from e1_judge.prompts import parse_response
from e1_judge.reporting import freeze_protocol, generate_report
from e1_judge.runner import build_judge_plan
from e1_judge.verification import verify_results


def _write_jsonl(path: Path, records) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _labels(pairs):
    return [
        {
            "schema_version": "2", "pair_id": pair.pair_id,
            "annotator_ids": ["primary-1", "primary-2"], "agreement": True,
            "third_annotator_id": None,
            "faithfulness_preference": "a", "preservation_preference": "a",
            "temporal_consistency_preference": "a", "visual_quality_preference": "a",
            "overall_preference": "a", "human_tie": False, "human_uncertain": False,
            "adjudicated_at": "2026-08-24T00:00:00+00:00", "protocol_version": "2",
        }
        for pair in pairs
    ]


def _payload(request: JudgeRequestV2, pair_map, wrong_task=None):
    if request.method == "absolute-v1":
        seed = int(request.candidate_id.rsplit("-s", 1)[1])
        score = {101: 4.0, 202: 3.5, 303: 3.0, 404: 2.5, 505: 2.0}[seed]
        return {
            "scores": {
                "faithfulness": score, "preservation": score,
                "temporal_consistency": score, "visual_quality": score,
            },
            "overall_score": score, "confidence": 0.9, "evidence": "synthetic oracle",
        }
    pair = pair_map[request.pair_id]
    canonical_winner = pair.candidate_b.candidate_id if pair.task_type == wrong_task else pair.candidate_a.candidate_id
    preference = "a" if request.candidate_a_id == canonical_winner else "b"
    if request.method in {"pairwise-single-v1", "pairwise-swap-v1"}:
        return {"overall_preference": preference, "confidence": 0.9, "evidence": "synthetic oracle"}
    dimension = {"preference": preference, "confidence": 0.9, "evidence": "synthetic oracle"}
    return {
        "faithfulness": dimension, "preservation": dimension,
        "temporal_consistency": dimension, "visual_quality": dimension,
        "overall_preference": preference, "overall_confidence": 0.9,
        "failure_tags_a": [], "failure_tags_b": [],
    }


def _synthetic_results(requests, pairs, wrong_task=None):
    pair_map = {pair.pair_id: pair for pair in pairs}
    results = []
    for request_data in requests:
        request = JudgeRequestV2.model_validate(request_data)
        payload = _payload(request, pair_map, wrong_task)
        raw_text = json.dumps(payload, sort_keys=True)
        results.append(JudgeResultV2(
            request_id=request.request_id, judge_key=request.judge_key,
            pair_id=request.pair_id, candidate_id=request.candidate_id,
            sample_id=request.sample_id, split=request.split, method=request.method,
            comparison_direction=request.comparison_direction,
            candidate_a_id=request.candidate_a_id, candidate_b_id=request.candidate_b_id,
            status="succeeded", parsed=parse_response(request.method, raw_text),
            raw_response={"text": raw_text, "backend": "synthetic-oracle"},
            parse_error=None, runtime_seconds=0, peak_vram_mb=0,
            prompt_version=request.prompt_version, prompt_checksum=request.prompt_checksum,
            parser_version=request.parser_version,
            generation_parameters=request.generation_parameters,
            model_name=request.model_name, model_revision=request.model_revision,
            model_manifest_sha256=request.model_manifest_sha256,
            runtime_fingerprint=request.runtime_fingerprint,
            frozen_protocol_fingerprint=request.frozen_protocol_fingerprint,
            created_at="2026-08-24T00:00:00+00:00",
        ).model_dump(mode="json"))
    return results


@pytest.fixture(scope="module")
def analysis_bundle(e1_v2_fixture, tmp_path_factory):
    from e1_judge.metrics import analyze

    root = tmp_path_factory.mktemp("e1-analysis")
    pairs = [
        PairRecordV2.model_validate(json.loads(line))
        for line in e1_v2_fixture["pairs_path"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    labels_path = root / "human-adjudicated.jsonl"
    _write_jsonl(labels_path, _labels(pairs))
    runtime = Path(__file__).parents[2] / "configs" / "e1" / "runtime-mock.yaml"
    development_plan = root / "judge-plan-development.jsonl"
    development_requests = build_judge_plan(
        e1_v2_fixture["pairs_path"], e1_v2_fixture["packets_dir"], e1_v2_fixture["config"],
        runtime, development_plan, snapshot="development-test-snapshot",
    )
    development_results = root / "results-development.jsonl"
    _write_jsonl(development_results, _synthetic_results(development_requests, pairs))

    fast_config = root / "pilot-fast-analysis.yaml"
    config_data = yaml.safe_load(e1_v2_fixture["config"].read_text(encoding="utf-8"))
    config_data["bootstrap_iterations"] = 50
    fast_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    dev_analysis = root / "dev-analysis"
    dev_metrics = analyze(
        e1_v2_fixture["pairs_path"], labels_path, development_results, fast_config,
        dev_analysis, mode="dev",
    )
    frozen = root / "frozen"
    protocol = freeze_protocol(
        dev_analysis / "dev-selection.json", e1_v2_fixture["pairs_path"],
        e1_v2_fixture["packets_dir"], e1_v2_fixture["config"], runtime, frozen,
        snapshot="frozen-test-snapshot",
    )
    frozen_plan = frozen / "judge-plan-frozen.jsonl"
    frozen_requests = [json.loads(line) for line in frozen_plan.read_text(encoding="utf-8").splitlines()]
    frozen_results = root / "results-frozen.jsonl"
    _write_jsonl(frozen_results, _synthetic_results(frozen_requests, pairs))
    return {
        "root": root, "pairs": pairs, "labels": labels_path, "runtime": runtime,
        "dev_metrics": dev_metrics, "dev_analysis": dev_analysis,
        "protocol": protocol, "frozen": frozen, "frozen_plan": frozen_plan,
        "frozen_requests": frozen_requests, "frozen_results": frozen_results,
        "config": frozen / "protocol" / "pilot-frozen.yaml",
        "pairs_path": e1_v2_fixture["pairs_path"],
    }


def test_dev_selects_rubric_after_threshold_scan(analysis_bundle):
    selection = json.loads(
        (analysis_bundle["dev_analysis"] / "dev-selection.json").read_text(encoding="utf-8")
    )
    assert selection["selected_method"] == "rubric-swap-v1"
    assert selection["confidence_threshold"] == 0.5
    assert selection["absolute_delta_threshold"] == 0.0
    assert selection["blocked"] is False
    assert set(analysis_bundle["dev_metrics"]["methods"]) == {
        "absolute-v1", "pairwise-single-v1", "pairwise-swap-v1", "rubric-swap-v1"
    }
    assert analysis_bundle["dev_metrics"]["pairs"] == 30


def test_freeze_locks_fingerprints_and_verifier(analysis_bundle):
    protocol = analysis_bundle["protocol"]
    assert protocol["selected_method"] == "rubric-swap-v1"
    assert len(protocol["protocol_fingerprint"]) == 64
    requests = [JudgeRequestV2.model_validate(record) for record in analysis_bundle["frozen_requests"]]
    assert len(requests) == 550
    assert {request.frozen_protocol_fingerprint for request in requests} == {
        protocol["protocol_fingerprint"]
    }
    verify_results(
        analysis_bundle["frozen_plan"], analysis_bundle["frozen_results"],
        analysis_bundle["labels"], expect_requests=550, strict=True,
    )


def test_final_gate_passes_and_writes_reward_and_report(analysis_bundle):
    from e1_judge.metrics import analyze

    output = analysis_bundle["root"] / "final-pass"
    metrics = analyze(
        analysis_bundle["pairs_path"], analysis_bundle["labels"],
        analysis_bundle["frozen_results"], analysis_bundle["config"], output,
        mode="final", frozen_protocol=analysis_bundle["frozen"] / "protocol.lock.json",
    )
    decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "PASS_PROVISIONAL"
    assert all(decision["gates"].values())
    assert set(metrics["methods"]) == {"rubric-swap-v1"}
    assert metrics["pairs"] == 70
    reward = yaml.safe_load((output / "reward-v0.yaml").read_text(encoding="utf-8"))
    assert reward["method"] == "rubric-swap-v1" and reward["provisional"] is True
    report = generate_report(output, analysis_bundle["root"] / "report")
    assert report.is_file()
    assert (report.parent / "figures" / "reliability.svg").is_file()


def test_final_gate_fails_category_and_emits_no_reward(analysis_bundle):
    from e1_judge.metrics import analyze

    bad_results = analysis_bundle["root"] / "results-frozen-bad-local.jsonl"
    _write_jsonl(
        bad_results,
        _synthetic_results(analysis_bundle["frozen_requests"], analysis_bundle["pairs"], wrong_task="local"),
    )
    output = analysis_bundle["root"] / "final-fail"
    analyze(
        analysis_bundle["pairs_path"], analysis_bundle["labels"], bad_results,
        analysis_bundle["config"], output, mode="final",
        frozen_protocol=analysis_bundle["frozen"] / "protocol.lock.json",
    )
    decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "FAIL_REVISE_JUDGE"
    assert decision["gates"]["categories"] is False
    assert not (output / "reward-v0.yaml").exists()


def test_swap_normalization_rejects_directional_disagreement(analysis_bundle):
    pair = next(pair for pair in analysis_bundle["pairs"] if pair.split == "frozen-eval")
    records = [
        JudgeResultV2.model_validate(record)
        for record in _synthetic_results(analysis_bundle["frozen_requests"], analysis_bundle["pairs"])
        if record["pair_id"] == pair.pair_id and record["method"] == "rubric-swap-v1"
    ]
    reverse = next(record for record in records if record.comparison_direction == "b_vs_a")
    reverse.parsed["overall_preference"] = "a" if reverse.parsed["overall_preference"] == "b" else "b"
    predictions = build_predictions([pair], records, "rubric-swap-v1")
    assert predictions[pair.pair_id]["consistent"] is False
    assert predictions[pair.pair_id]["preference"] == "uncertain"
