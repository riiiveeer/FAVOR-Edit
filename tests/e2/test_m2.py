from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from e1_judge.hashing import canonical_sha256
from e1_judge.models import (
    AdjudicatedLabelV2, FrozenProtocolV2, JudgeResultV2, PairRecordV2,
    load_runtime_config,
)
from e1_judge.prompts import load_prompt
from e1_judge.runner import frozen_protocol_fingerprint, runtime_fingerprint
from e2_bon.models import E2JudgeRequestV1
from e2_bon.pool import build_candidate_pool, plan_generation_extension
from e2_bon.preparation import E2PreparationError, prepare_e2
from e2_bon.qualification import qualify_auxiliary_rubric
from e2_bon.runner import run_e2_judge
from w1_pipeline.hashing import sha256_file
from w1_pipeline.models import CandidateRecord, CandidateStatus


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, values) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def _extension_records(fixture, plan_path: Path):
    records = []
    for task in json.loads(plan_path.read_text(encoding="utf-8"))["candidates"]:
        candidate_id = task["candidate_id"]
        video = fixture["root"] / "extension-media" / candidate_id / "video.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(candidate_id.encode())
        frames = []
        for index in range(16):
            frame = video.parent / f"{index:05d}.png"
            Image.new("RGB", (8, 8), (index, int(task["config"]["seed"]) % 255, 100)).save(frame)
            frames.append(frame)
        records.append(CandidateRecord(
            candidate_id=candidate_id, sample_id=task["sample_id"], generation_key=task["generation_key"],
            config=task["config"], status=CandidateStatus.SUCCEEDED, artifact_dir=task["artifact_dir"],
            video_path=str(video), frame_paths=[str(item) for item in frames], video_checksum=sha256_file(video),
            frame_checksums=[sha256_file(item) for item in frames], runtime_seconds=2.0, peak_vram_mb=0.0,
            code_snapshot=task["code_snapshot"],
        ).model_dump(mode="json"))
    return records


def _pool(fixture):
    extension_plan = fixture["root"] / "extension-plan-m2.json"
    plan_generation_extension(fixture["e0_plan"], fixture["config"], extension_plan, "extension-snapshot")
    records = _extension_records(fixture, extension_plan)
    extension_candidates = fixture["root"] / "extension-candidates-m2.json"
    extension_audit = fixture["root"] / "extension-audit-m2.csv"
    fixture["write_json"](extension_candidates, records)
    fixture["write_audit"](extension_audit, [item["candidate_id"] for item in records], "usable_for_e2")
    output = fixture["root"] / "candidate-pool-m2.json"
    build_candidate_pool(
        fixture["e0_plan"], fixture["e0_candidates"], fixture["e0_audit"], extension_plan,
        extension_candidates, extension_audit, fixture["config"], output,
    )
    return output


def _e1_dependencies(root: Path, selected_method="rubric-swap-v1"):
    source_dir = Path("configs/e1").resolve()
    frozen_dir = root / "frozen-protocol"
    frozen_dir.mkdir()
    config_data = yaml.safe_load((source_dir / "pilot.yaml").read_text(encoding="utf-8"))
    config_data["bootstrap_iterations"] = 50
    config_data["frozen_selection"] = {
        "selected_method": selected_method, "confidence_threshold": 0.5, "absolute_delta_threshold": 0.0,
    }
    for prompt in source_dir.glob("prompt-*-v1.yaml"):
        shutil.copy2(prompt, frozen_dir / prompt.name)
    frozen_config = frozen_dir / "pilot-frozen.yaml"
    frozen_config.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    runtime = Path("configs/e1/runtime-mock.yaml").resolve()
    runtime_model = load_runtime_config(runtime)
    prompt_checksums = {}
    for method, item in config_data["methods"].items():
        _, prompt_checksums[method] = load_prompt(frozen_dir / item["prompt"])
    protocol_fingerprint = frozen_protocol_fingerprint(
        frozen_config, config_data, prompt_checksums, runtime_fingerprint(runtime_model), "frozen-test",
    )
    assert protocol_fingerprint is not None
    protocol = FrozenProtocolV2(
        created_at="2026-08-29T00:00:00+00:00", code_snapshot="frozen-test",
        selected_method=selected_method, confidence_threshold=0.5, absolute_delta_threshold=0.0,
        config_checksum=sha256_file(frozen_config), runtime_fingerprint=runtime_fingerprint(runtime_model),
        prompt_checksums=prompt_checksums, plan_checksum="1" * 64, protocol_fingerprint=protocol_fingerprint,
    )
    protocol_path = frozen_dir / "protocol.lock.json"
    _write_json(protocol_path, protocol.model_dump(mode="json"))
    decision = root / "decision.json"
    _write_json(decision, {"schema_version": "2", "decision": "PASS_PROVISIONAL", "selected_method": selected_method,
                           "gates": {"accuracy": True, "swap_consistency": True, "coverage": True, "categories": True}})
    spec, prompt_sha = load_prompt(frozen_dir / config_data["methods"][selected_method]["prompt"])
    reward = root / "reward-v0.yaml"
    reward.write_text(yaml.safe_dump({
        "schema_version": "2", "provisional": True, "method": selected_method,
        "model_revision": runtime_model.model.revision, "prompt_version": spec.prompt_version,
        "prompt_checksum": prompt_sha, "parser_version": spec.parser_version,
        "confidence_threshold": 0.5, "absolute_delta_threshold": 0.0,
    }, sort_keys=False), encoding="utf-8")
    return decision, reward, frozen_config, protocol_path, runtime


def test_atomic_prepare_builds_280_pairs_80_trials_and_560_plan(e2_m1_fixture):
    pool = _pool(e2_m1_fixture)
    decision, reward, frozen_config, protocol, runtime = _e1_dependencies(e2_m1_fixture["root"])
    output = e2_m1_fixture["root"] / "E2-bon-pilot-v01"
    summary = prepare_e2(
        pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime,
        output, "m2-happy",
    )
    assert summary["status"] == "passed" and output.is_dir()
    assert summary["counts"] == {
        "pairs": 280, "trials": 80, "sources": 10, "candidates": 80,
        "packets": 280, "primary_requests": 560, "auxiliary_requests": 0,
    }
    pairs = (output / "inputs/pairs.jsonl").read_text(encoding="utf-8").splitlines()
    plan = [E2JudgeRequestV1.model_validate(json.loads(line)) for line in (output / "plans/judge-plan-primary.jsonl").read_text(encoding="utf-8").splitlines()]
    design = json.loads((output / "bon-design.json").read_text(encoding="utf-8"))["trials"]
    assert len(pairs) == 280 and len(plan) == 560 and len(design) == 80
    assert {item.method for item in plan} == {"rubric-swap-v1"}
    assert all(".prepare-" not in json.dumps(item.model_dump(mode="json")) for item in plan)
    assert (output / "PREPARATION_SHA256SUMS").is_file()
    with pytest.raises(FileExistsError):
        prepare_e2(pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime, output, "retry")


def test_mock_runner_uses_cache_and_marks_zero_research(e2_m1_fixture):
    pool = _pool(e2_m1_fixture)
    decision, reward, frozen_config, protocol, runtime = _e1_dependencies(e2_m1_fixture["root"])
    output = e2_m1_fixture["root"] / "prepared-run"
    prepare_e2(pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime, output, "run")
    experiment = e2_m1_fixture["root"] / "run"
    cache = e2_m1_fixture["root"] / "e2.sqlite3"
    first = run_e2_judge(output / "plans/judge-plan-primary.jsonl", runtime, experiment, cache)
    second = run_e2_judge(output / "plans/judge-plan-primary.jsonl", runtime, experiment, cache)
    assert first == {"selected": 560, "cache_hits": 0, "attempted": 560, "succeeded": 560, "failed": 0, "research_measurements": 0}
    assert second["cache_hits"] == 560 and second["attempted"] == 0 and second["research_measurements"] == 0
    assert len((experiment / "results.jsonl").read_text(encoding="utf-8").splitlines()) == 560


def test_pairwise_primary_requires_qualified_auxiliary_for_rubric_plan(e2_m1_fixture):
    pool = _pool(e2_m1_fixture)
    decision, reward, frozen_config, protocol, runtime = _e1_dependencies(
        e2_m1_fixture["root"], selected_method="pairwise-swap-v1"
    )
    output_without = e2_m1_fixture["root"] / "pairwise-no-aux"
    summary_without = prepare_e2(
        pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime,
        output_without, "pairwise-no-aux",
    )
    assert summary_without["auxiliary_rubric"] == "NOT_APPLICABLE"
    assert not (output_without / "plans/judge-plan-auxiliary-rubric.jsonl").exists()

    auxiliary = e2_m1_fixture["root"] / "auxiliary-rubric-v0.json"
    protocol_payload = json.loads(protocol.read_text(encoding="utf-8"))
    _write_json(auxiliary, {
        "schema_version": "1", "decision": "PASS_AUXILIARY_RUBRIC", "method": "rubric-swap-v1",
        "e1_protocol_fingerprint": protocol_payload["protocol_fingerprint"], "gates": {
            "accuracy": True, "swap_consistency": True, "coverage": True, "categories": True,
        },
    })
    output_with = e2_m1_fixture["root"] / "pairwise-with-aux"
    summary_with = prepare_e2(
        pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime,
        output_with, "pairwise-with-aux", auxiliary,
    )
    primary = [E2JudgeRequestV1.model_validate(json.loads(line)) for line in (output_with / "plans/judge-plan-primary.jsonl").read_text(encoding="utf-8").splitlines()]
    rubric = [E2JudgeRequestV1.model_validate(json.loads(line)) for line in (output_with / "plans/judge-plan-auxiliary-rubric.jsonl").read_text(encoding="utf-8").splitlines()]
    assert summary_with["counts"]["auxiliary_requests"] == 560
    assert {item.method for item in primary} == {"pairwise-swap-v1"}
    assert {item.method for item in rubric} == {"rubric-swap-v1"}
    assert {item.stage for item in rubric} == {"auxiliary-rubric"}


def test_prepare_preserves_failed_artifact_when_e1_gate_fails(e2_m1_fixture):
    pool = _pool(e2_m1_fixture)
    decision, reward, frozen_config, protocol, runtime = _e1_dependencies(e2_m1_fixture["root"])
    payload = json.loads(decision.read_text(encoding="utf-8"))
    payload["decision"] = "FAIL_REVISE_JUDGE"
    decision.write_text(json.dumps(payload), encoding="utf-8")
    output = e2_m1_fixture["root"] / "failed-final"
    with pytest.raises(E2PreparationError) as found:
        prepare_e2(pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime, output, "bad-gate")
    assert not output.exists()
    assert found.value.failure_root and (found.value.failure_root / "PREPARATION_FAILED.json").is_file()


@pytest.mark.parametrize(
    ("field", "drifted"),
    (("confidence_threshold", 0.75), ("absolute_delta_threshold", 0.25)),
)
def test_prepare_rejects_e1_frozen_threshold_drift(e2_m1_fixture, field, drifted):
    pool = _pool(e2_m1_fixture)
    decision, reward, frozen_config, protocol, runtime = _e1_dependencies(e2_m1_fixture["root"])
    reward_payload = yaml.safe_load(reward.read_text(encoding="utf-8"))
    reward_payload[field] = drifted
    reward.write_text(yaml.safe_dump(reward_payload, sort_keys=False), encoding="utf-8")
    output = e2_m1_fixture["root"] / f"threshold-drift-{field}"
    with pytest.raises(E2PreparationError, match="frozen threshold mismatch") as found:
        prepare_e2(
            pool, e2_m1_fixture["config"], decision, reward, frozen_config, protocol, runtime,
            output, f"bad-{field}",
        )
    assert not output.exists()
    assert found.value.failure_root and (found.value.failure_root / "PREPARATION_FAILED.json").is_file()


def _qualification_inputs(root: Path, wrong_task: str | None = None):
    pairs = []
    labels = []
    results = []
    all_pair_ids = []
    sample_specs = [(f"frozen-{index}", "attribute" if index < 3 else ("object" if index < 5 else "local")) for index in range(7)]
    pair_number = 0
    for sample_id, task_type in sample_specs:
        for local_index in range(10):
            pair_number += 1
            pair_id = f"{sample_id}-p{local_index:02d}"
            all_pair_ids.append(pair_id)
            pair = PairRecordV2(
                pair_id=pair_id, sample_id=sample_id, task_type=task_type,
                instruction="edit", target_caption="target",
                source={"sample_id": sample_id, "video_path": "source.mp4", "video_sha256": "1" * 64, "mask_frame_paths": []},
                candidate_a={"candidate_id": f"{pair_id}-a", "video_path": "a.mp4", "video_sha256": "2" * 64},
                candidate_b={"candidate_id": f"{pair_id}-b", "video_path": "b.mp4", "video_sha256": "3" * 64},
                split="frozen-eval", randomization_seed=1,
            )
            pairs.append(pair.model_dump(mode="json"))
    for index in range(30):
        pair_id = f"dev-p{index:02d}"
        all_pair_ids.append(pair_id)
        pairs.append(PairRecordV2(
            pair_id=pair_id, sample_id="dev", task_type="attribute", instruction="edit", target_caption="target",
            source={"sample_id": "dev", "video_path": "source.mp4", "video_sha256": "1" * 64, "mask_frame_paths": []},
            candidate_a={"candidate_id": f"{pair_id}-a", "video_path": "a.mp4", "video_sha256": "2" * 64},
            candidate_b={"candidate_id": f"{pair_id}-b", "video_path": "b.mp4", "video_sha256": "3" * 64},
            split="dev", randomization_seed=1,
        ).model_dump(mode="json"))
    for pair_id in all_pair_ids:
        labels.append(AdjudicatedLabelV2(
            pair_id=pair_id, annotator_ids=["one", "two"], agreement=True,
            faithfulness_preference="a", preservation_preference="a", temporal_consistency_preference="a",
            visual_quality_preference="a", overall_preference="a", human_tie=False, human_uncertain=False,
            adjudicated_at="2026-08-29T00:00:00Z",
        ).model_dump(mode="json"))
    pair_models = [PairRecordV2.model_validate(item) for item in pairs if item["split"] == "frozen-eval"]
    for pair in pair_models:
        canonical_choice = "b" if pair.task_type == wrong_task else "a"
        for direction in ("a_vs_b", "b_vs_a"):
            screen_choice = canonical_choice if direction == "a_vs_b" else ("b" if canonical_choice == "a" else "a")
            screen_a = pair.candidate_a if direction == "a_vs_b" else pair.candidate_b
            screen_b = pair.candidate_b if direction == "a_vs_b" else pair.candidate_a
            dimension = {"preference": screen_choice, "confidence": 1.0, "evidence": "oracle"}
            parsed = {"faithfulness": dimension, "preservation": dimension, "temporal_consistency": dimension,
                      "visual_quality": dimension, "overall_preference": screen_choice, "overall_confidence": 1.0,
                      "failure_tags_a": [], "failure_tags_b": []}
            request_id = f"rubric:{pair.pair_id}:{direction}"
            results.append(JudgeResultV2(
                request_id=request_id, judge_key=canonical_sha256(request_id), pair_id=pair.pair_id,
                sample_id=pair.sample_id, split="frozen-eval", method="rubric-swap-v1",
                comparison_direction=direction, candidate_a_id=screen_a.candidate_id,
                candidate_b_id=screen_b.candidate_id, status="succeeded", parsed=parsed,
                raw_response={"oracle": True}, runtime_seconds=0, peak_vram_mb=0,
                prompt_version="rubric-swap-v1", prompt_checksum="4" * 64,
                parser_version="strict-json-v1", generation_parameters={}, model_name="mock",
                model_revision="mock", model_manifest_sha256="5" * 64, runtime_fingerprint="6" * 64,
                frozen_protocol_fingerprint="2" * 64, created_at="2026-08-29T00:00:00Z",
            ).model_dump(mode="json"))
    paths = {name: root / name for name in ("pairs.jsonl", "human.jsonl", "results.jsonl")}
    _write_jsonl(paths["pairs.jsonl"], pairs)
    _write_jsonl(paths["human.jsonl"], labels)
    _write_jsonl(paths["results.jsonl"], results)
    return paths


def test_auxiliary_rubric_qualification_pass_and_category_fail(tmp_path: Path):
    source_config = yaml.safe_load(Path("configs/e1/pilot.yaml").read_text(encoding="utf-8"))
    source_config["bootstrap_iterations"] = 50
    config = tmp_path / "e1-fast.yaml"
    config.write_text(yaml.safe_dump(source_config, sort_keys=False), encoding="utf-8")
    dev_metrics = tmp_path / "dev-metrics.json"
    _write_json(dev_metrics, {"methods": {"rubric-swap-v1": {"confidence_threshold": 0.5}}})
    protocol = tmp_path / "protocol.json"
    _write_json(protocol, FrozenProtocolV2(
        created_at="2026-08-29T00:00:00Z", code_snapshot="x", selected_method="pairwise-swap-v1",
        confidence_threshold=0.5, absolute_delta_threshold=0, config_checksum="1" * 64,
        runtime_fingerprint="6" * 64, prompt_checksums={"rubric-swap-v1": "4" * 64},
        plan_checksum="3" * 64, protocol_fingerprint="2" * 64,
    ).model_dump(mode="json"))
    good = _qualification_inputs(tmp_path / "good")
    passed = qualify_auxiliary_rubric(
        good["pairs.jsonl"], good["human.jsonl"], good["results.jsonl"], dev_metrics, config, protocol,
        tmp_path / "aux-pass.json",
    )
    assert passed["decision"] == "PASS_AUXILIARY_RUBRIC" and all(passed["gates"].values())
    bad = _qualification_inputs(tmp_path / "bad", wrong_task="local")
    failed = qualify_auxiliary_rubric(
        bad["pairs.jsonl"], bad["human.jsonl"], bad["results.jsonl"], dev_metrics, config, protocol,
        tmp_path / "aux-fail.json",
    )
    assert failed["decision"] == "FAIL_AUXILIARY_RUBRIC" and failed["gates"]["categories"] is False
