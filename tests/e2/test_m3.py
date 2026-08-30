from __future__ import annotations

import json
import math
import shutil
from itertools import combinations
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from e1_judge.hashing import canonical_sha256
from w1_pipeline.hashing import sha256_file

from e2_bon.analysis import analyze_e2
from e2_bon.annotations import (
    adjudicate_e2,
    canonical_preference,
    display_direction,
    render_annotation_page,
)
from e2_bon.cli import app
from e2_bon.config import load_config
from e2_bon.io import read_json
from e2_bon.models import (
    BonTrialV1,
    CandidatePoolV1,
    E2HumanAnnotationV1,
    E2JudgeResultV1,
    E2PairV1,
    E2SelectionBundleV1,
    PoolCandidateV1,
)
from e2_bon.reporting import report_e2
from e2_bon.selection import (
    fit_bradley_terry,
    pareto_maxmin_choice,
    select_candidates,
    swap_predictions,
)
from e2_bon.verification import verify_e2


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in records), encoding="utf-8")


def _candidate_id(sample_id: str, seed: int) -> str:
    return f"{sample_id}-s{seed:04d}"


def _synthetic_inputs(root: Path, method: str = "pairwise-swap-v1") -> dict:
    root.mkdir(parents=True, exist_ok=True)
    config = Path("configs/e2/pilot.yaml").resolve()
    cfg = load_config(config)
    reward = root / "reward-v0.yaml"
    reward.write_text(yaml.safe_dump({
        "schema_version": "2", "provisional": True, "method": method,
        "model_revision": "mock", "prompt_version": method,
        "prompt_checksum": "1" * 64, "parser_version": "2",
        "confidence_threshold": 0.5, "absolute_delta_threshold": 0.0,
    }, sort_keys=False), encoding="utf-8")
    reward_sha = sha256_file(reward)
    pairs = []
    results = []
    trials = []
    pool_candidates = []
    candidate_sha = {}
    for sample_index, sample_id in enumerate(cfg.sample_ids):
        task_type = ("attribute", "object", "local")[sample_index % 3]
        candidates = []
        for seed in cfg.all_seeds:
            candidate_id = _candidate_id(sample_id, seed)
            video_sha = canonical_sha256(candidate_id)
            candidate_sha[candidate_id] = video_sha
            candidates.append((seed, candidate_id, video_sha))
            pool_candidates.append(PoolCandidateV1(
                candidate_id=candidate_id, sample_id=sample_id, seed=seed,
                origin="e0" if seed in cfg.base_seeds else "extension",
                generation_key=canonical_sha256({"candidate": candidate_id, "generation": True}),
                generation_config={"seed": seed}, input={"sample_id": sample_id},
                artifact_dir=f"/synthetic/{candidate_id}", video_path=f"/synthetic/{candidate_id}.mp4",
                video_sha256=video_sha, frame_paths=[f"/synthetic/{candidate_id}/{i:05d}.png" for i in range(16)],
                frame_sha256=[canonical_sha256({"candidate": candidate_id, "frame": i}) for i in range(16)],
                code_snapshot="synthetic", runtime_seconds=0.0, peak_vram_mb=0.0,
            ))
        for number, (left, right) in enumerate(combinations(candidates, 2), start=1):
            pair = E2PairV1(
                experiment_id=cfg.experiment_id, pair_id=f"{sample_id}-e2-p{number:03d}",
                sample_id=sample_id, task_type=task_type, instruction="perform the fixed edit",
                target_caption="edited target", source_video_path=f"/synthetic/{sample_id}-source.mp4",
                source_video_sha256=canonical_sha256({"source": sample_id}),
                source_frame_paths=[f"/synthetic/{sample_id}/source/{i:05d}.png" for i in range(16)],
                mask_frame_paths=[],
                candidate_a={"candidate_id": left[1], "seed": left[0], "video_path": f"/synthetic/{left[1]}.mp4", "video_sha256": left[2]},
                candidate_b={"candidate_id": right[1], "seed": right[0], "video_path": f"/synthetic/{right[1]}.mp4", "video_sha256": right[2]},
            )
            pairs.append(pair)
            winner = pair.candidate_b.candidate_id
            for direction in ("a_vs_b", "b_vs_a"):
                screen = (
                    (pair.candidate_a.candidate_id, pair.candidate_b.candidate_id)
                    if direction == "a_vs_b"
                    else (pair.candidate_b.candidate_id, pair.candidate_a.candidate_id)
                )
                preference = "a" if screen[0] == winner else "b"
                if method == "rubric-swap-v1":
                    dimension = {"preference": preference, "confidence": 1.0, "evidence": "synthetic"}
                    parsed = {
                        "faithfulness": dimension, "preservation": dimension,
                        "temporal_consistency": dimension, "visual_quality": dimension,
                        "overall_preference": preference, "overall_confidence": 1.0,
                        "failure_tags_a": [], "failure_tags_b": [],
                    }
                else:
                    parsed = {"overall_preference": preference, "confidence": 1.0, "evidence": "synthetic"}
                request_id = f"primary:{method}:{pair.pair_id}:{direction}"
                results.append(E2JudgeResultV1(
                    experiment_id=cfg.experiment_id, stage="primary", split="e2-pilot",
                    request_id=request_id, judge_key=canonical_sha256(request_id), pair_id=pair.pair_id,
                    sample_id=sample_id, method=method, backend="mock", comparison_direction=direction,
                    candidate_a_id=screen[0], candidate_b_id=screen[1], status="succeeded",
                    parsed=parsed, raw_response={"backend": "mock"}, runtime_seconds=0.0, peak_vram_mb=0.0,
                    prompt_version=method, prompt_checksum="1" * 64, parser_version="2",
                    generation_parameters={}, model_name="mock", model_revision="mock",
                    model_manifest_sha256="2" * 64, runtime_fingerprint="3" * 64,
                    e1_protocol_fingerprint="4" * 64, reward_artifact_sha256=reward_sha,
                    created_at="2026-08-30T00:00:00Z",
                ).model_dump(mode="json"))
        base_order = [_candidate_id(sample_id, seed) for seed in cfg.all_seeds]
        for replicate in range(8):
            order = base_order[replicate:] + base_order[:replicate]
            trials.append(BonTrialV1(
                experiment_id=cfg.experiment_id, trial_id=f"{sample_id}-r{replicate + 1:02d}",
                sample_id=sample_id, replicate=replicate, candidate_order=order,
                subsets={str(n): order[:n] for n in cfg.n_values},
            ).model_dump(mode="json"))
    pairs_path = root / "pairs.jsonl"
    design_path = root / "bon-design.json"
    results_path = root / "primary-results.jsonl"
    pool_path = root / "candidate-pool.json"
    _write_jsonl(pairs_path, [item.model_dump(mode="json") for item in pairs])
    _write_json(design_path, {"schema_version": "1", "trials": trials})
    _write_jsonl(results_path, results)
    pool = CandidatePoolV1(
        experiment_id=cfg.experiment_id, config_sha256=sha256_file(config),
        e0_plan_sha256="5" * 64, e0_candidates_sha256="6" * 64, e0_audit_sha256="7" * 64,
        extension_plan_sha256="8" * 64, extension_candidates_sha256="9" * 64,
        extension_audit_sha256="a" * 64, pool_fingerprint="b" * 64,
        candidate_count=80, sample_count=10, candidates=pool_candidates,
    )
    _write_json(pool_path, pool.model_dump(mode="json"))
    return {
        "config": config, "pairs": pairs_path, "design": design_path, "results": results_path,
        "reward": reward, "pool": pool_path, "pair_models": pairs,
    }


def _select(synthetic: dict, output: Path) -> E2SelectionBundleV1:
    payload = select_candidates(
        synthetic["config"], synthetic["design"], synthetic["pairs"], synthetic["results"],
        synthetic["reward"], output, "mock",
    )
    return E2SelectionBundleV1.model_validate(payload)


def _annotation(comparison, annotator_id: str, preference: str = "a") -> dict:
    direction = display_direction(comparison.comparison_id, annotator_id, comparison.randomization_seed)
    return E2HumanAnnotationV1(
        annotation_id=canonical_sha256({"comparison": comparison.comparison_id, "annotator": annotator_id})[:20],
        comparison_id=comparison.comparison_id, annotator_id=annotator_id, display_direction=direction,
        faithfulness_preference=preference, preservation_preference=preference,
        temporal_consistency_preference=preference, visual_quality_preference=preference,
        overall_preference=preference, confidence=1.0, notes="synthetic",
        started_at="2026-08-30T00:00:00Z", submitted_at="2026-08-30T00:00:01Z",
    ).model_dump(mode="json")


def test_bradley_terry_known_order_and_pareto_tie_break():
    abilities = fit_bradley_terry(
        ["a", "b", "c"],
        [("c", "a"), ("c", "b"), ("c", "a"), ("b", "a")],
    )
    assert abilities["c"] > abilities["b"] > abilities["a"]
    assert math.isclose(sum(abilities.values()), 0.0, abs_tol=1e-8)
    utilities = {
        "a": {dimension: 0.8 for dimension in ("faithfulness", "preservation", "temporal_consistency", "visual_quality")},
        "b": {dimension: 0.8 for dimension in ("faithfulness", "preservation", "temporal_consistency", "visual_quality")},
        "c": {dimension: 0.7 for dimension in ("faithfulness", "preservation", "temporal_consistency", "visual_quality")},
    }
    assert pareto_maxmin_choice(["c", "b", "a"], utilities) == "a"


def test_swap_inconsistency_and_confidence_filter(tmp_path: Path):
    synthetic = _synthetic_inputs(tmp_path)
    pair = synthetic["pair_models"][0]
    all_results = [E2JudgeResultV1.model_validate(item) for item in _read_jsonl(synthetic["results"])]
    records = [item for item in all_results if item.pair_id == pair.pair_id]
    predictions, audit = swap_predictions([pair], records, 0.5)
    assert predictions[pair.pair_id]["preference"] == "b" and audit["decisive_high_confidence"] == 1
    second = records[1].model_copy(deep=True)
    second.parsed["overall_preference"] = "b" if second.parsed["overall_preference"] == "a" else "a"
    predictions, audit = swap_predictions([pair], [records[0], second], 0.5)
    assert predictions[pair.pair_id]["preference"] == "uncertain" and audit["inconsistent"] == 1
    low = [item.model_copy(deep=True) for item in records]
    for item in low:
        item.parsed["confidence"] = 0.2
    predictions, audit = swap_predictions([pair], low, 0.5)
    assert predictions[pair.pair_id]["preference"] == "uncertain" and audit["uncertain_or_low_confidence"] == 1


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_selection_counts_rubric_availability_and_no_overwrite(tmp_path: Path):
    pairwise = _synthetic_inputs(tmp_path / "pairwise")
    pairwise_output = tmp_path / "pairwise-selection.json"
    bundle = _select(pairwise, pairwise_output)
    assert len(bundle.selections) == 640 and len(bundle.human_comparisons) == 80
    assert bundle.method_status["equal-linear"] == "NOT_APPLICABLE"
    assert bundle.research_measurements == 0
    with pytest.raises(FileExistsError):
        _select(pairwise, pairwise_output)
    rubric = _synthetic_inputs(tmp_path / "rubric", method="rubric-swap-v1")
    rubric_bundle = _select(rubric, tmp_path / "rubric-selection.json")
    assert len(rubric_bundle.selections) == 1280
    assert rubric_bundle.method_status["equal-linear"] == "AVAILABLE"
    assert rubric_bundle.method_status["pareto-maxmin"] == "AVAILABLE"


def test_selection_rejects_mock_as_formal_and_mixed_execution_identity(tmp_path: Path):
    synthetic = _synthetic_inputs(tmp_path / "provenance")
    with pytest.raises(ValueError, match="backend provenance"):
        select_candidates(
            synthetic["config"], synthetic["design"], synthetic["pairs"], synthetic["results"],
            synthetic["reward"], tmp_path / "false-formal.json", "formal-command",
        )
    mixed_records = _read_jsonl(synthetic["results"])
    mixed_records[0]["model_revision"] = "different-revision"
    mixed_path = tmp_path / "mixed-results.jsonl"
    _write_jsonl(mixed_path, mixed_records)
    with pytest.raises(ValueError, match="mix backend/model/runtime/prompt identities"):
        select_candidates(
            synthetic["config"], synthetic["design"], synthetic["pairs"], mixed_path,
            synthetic["reward"], tmp_path / "mixed-selection.json", "mock",
        )


def test_blind_page_direction_and_full_mock_e2e(tmp_path: Path):
    synthetic = _synthetic_inputs(tmp_path / "synthetic")
    selection_path = tmp_path / "selection.json"
    bundle = _select(synthetic, selection_path)
    non_identical = [item for item in bundle.human_comparisons if not item.identical_selection]
    identical = [item for item in bundle.human_comparisons if item.identical_selection]
    assert len(non_identical) == 70 and len(identical) == 10
    comparison = non_identical[0]
    direction = display_direction(comparison.comparison_id, "ann-one", comparison.randomization_seed)
    assert direction == display_direction(comparison.comparison_id, "ann-one", comparison.randomization_seed)
    assert canonical_preference("left", direction) == ("a" if direction == "a_vs_b" else "b")
    tokens = {(comparison.comparison_id, role): role for role in (
        "source-video", "source-contact", "left-video", "left-contact", "right-video", "right-contact",
    )}
    page = render_annotation_page(comparison, 0, len(non_identical), tokens, False)
    assert "N=4" not in page and "N=1" not in page
    assert comparison.n4_candidate_id not in page and comparison.n1_candidate_id not in page

    first_path = tmp_path / "ann-one.jsonl"
    second_path = tmp_path / "ann-two.jsonl"
    third_path = tmp_path / "ann-three.jsonl"
    first = [_annotation(item, "ann-one") for item in non_identical]
    second = [_annotation(item, "ann-two") for item in non_identical]
    second[0] = _annotation(non_identical[0], "ann-two", "b")
    third = [_annotation(non_identical[0], "ann-three", "a")]
    _write_jsonl(first_path, first)
    _write_jsonl(second_path, second)
    _write_jsonl(third_path, third)
    adjudicated_path = tmp_path / "adjudicated.jsonl"
    agreement_path = tmp_path / "agreement.json"
    adjudicated = adjudicate_e2(
        selection_path, [first_path, second_path], third_path, adjudicated_path, agreement_path,
    )
    assert len(adjudicated) == 80
    assert sum(item["automatic_tie"] for item in adjudicated) == 10
    assert read_json(agreement_path)["third_annotator_labels"] == 1

    analysis_dir = tmp_path / "analysis"
    analysis = analyze_e2(
        synthetic["config"], selection_path, adjudicated_path, agreement_path,
        synthetic["pool"], synthetic["results"], analysis_dir,
    )
    assert analysis["metrics"]["overall"]["tie_aware_win_rate"] == pytest.approx(0.9375)
    assert analysis["metrics"]["overall"]["bootstrap_95_ci"]["iterations"] == 2000
    assert analysis["metrics"]["overall"]["bootstrap_95_ci"]["clusters"] == 10
    assert analysis["metrics"]["research_measurements"] == 0
    with pytest.raises(FileExistsError):
        analyze_e2(
            synthetic["config"], selection_path, adjudicated_path, agreement_path,
            synthetic["pool"], synthetic["results"], analysis_dir,
        )
    report_dir = tmp_path / "report"
    report_e2(analysis_dir, report_dir)
    for name in ("E2_REPORT.md", "win-rate.svg", "cost-curve.svg", "cost-curve.csv", "report-manifest.json"):
        assert (report_dir / name).is_file()
    assert "no research measurements" in (report_dir / "E2_REPORT.md").read_text(encoding="utf-8")

    preparation = tmp_path / "preparation"
    (preparation / "inputs").mkdir(parents=True)
    shutil.copy2(synthetic["design"], preparation / "bon-design.json")
    shutil.copy2(synthetic["pairs"], preparation / "inputs" / "pairs.jsonl")
    shutil.copy2(synthetic["pool"], preparation / "inputs" / "candidate-pool.json")
    _write_json(preparation / "e2-preparation-v01.json", {"schema_version": "1", "status": "passed"})
    _write_json(preparation / "preparation-verification-v01.json", {"schema_version": "1", "status": "passed"})
    checksum_rows = []
    for path in sorted(item for item in preparation.rglob("*") if item.is_file()):
        checksum_rows.append(f"{sha256_file(path)}  {path.relative_to(preparation).as_posix()}")
    (preparation / "PREPARATION_SHA256SUMS").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    verification_path = tmp_path / "verification.json"
    verification = verify_e2(
        preparation, selection_path, adjudicated_path, analysis_dir, report_dir,
        synthetic["results"], synthetic["reward"], verification_path,
    )
    assert verification["status"] == "passed"
    assert verification["ready_for_research_interpretation"] is False
    assert verification["research_measurements"] == 0


def test_cli_milestone3_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("select", "annotate", "adjudicate", "analyze", "report", "verify"):
        assert command in result.stdout
