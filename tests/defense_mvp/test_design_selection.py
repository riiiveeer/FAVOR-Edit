import json
from pathlib import Path

import pytest

from defense_mvp.design import create_design, cyclic_trials
from defense_mvp.ingest import ingest_delivery
from defense_mvp.selection import constrained_pareto_choice, rank_percentiles, select_design
from w1_pipeline.hashing import sha256_file


CONFIG = Path("configs/defense_mvp/pilot.yaml")


def test_five_cyclic_trials_are_balanced_and_nested() -> None:
    candidates = [f"sample-s{seed}" for seed in [101, 202, 303, 404, 505]]
    trials = cyclic_trials("sample", candidates)
    assert len(trials) == 5
    for position in range(5):
        assert {trial["candidate_order"][position] for trial in trials} == set(candidates)
    for trial in trials:
        order = trial["candidate_order"]
        assert trial["subsets"]["1"] == order[:1]
        assert trial["subsets"]["2"] == order[:2]
        assert trial["subsets"]["4"] == order[:4]


def test_rank_percentiles_use_stable_candidate_id_ties() -> None:
    scores = {
        "b": {dimension: 0.5 for dimension in "FPTQ"},
        "a": {dimension: 0.5 for dimension in "FPTQ"},
        "c": {dimension: 0.9 for dimension in "FPTQ"},
    }
    ranks = rank_percentiles(["b", "c", "a"], scores)
    assert ranks["a"]["F"] == 0.0
    assert ranks["b"]["F"] == 0.5
    assert ranks["c"]["F"] == 1.0


def test_constrained_pareto_uses_frontier_then_maxmin() -> None:
    utilities = {
        "a": {"F": 1.0, "P": 0.7, "T": 0.7, "Q": 0.7},
        "b": {"F": 0.8, "P": 0.8, "T": 0.8, "Q": 0.8},
        "c": {"F": 0.6, "P": 0.6, "T": 1.0, "Q": 1.0},
    }
    chosen, audit = constrained_pareto_choice(["c", "a", "b"], utilities)
    assert chosen == "b"
    assert audit["fallback"] is False
    assert set(audit["pareto_frontier_candidate_ids"]) == {"a", "b"}


def test_constrained_pareto_fallback_is_explicit_and_deterministic() -> None:
    utilities = {
        "a": {"F": 1.0, "P": 0.0, "T": 0.9, "Q": 0.9},
        "b": {"F": 0.0, "P": 1.0, "T": 0.8, "Q": 1.0},
    }
    chosen, audit = constrained_pareto_choice(["b", "a"], utilities)
    assert chosen == "a"
    assert audit["fallback"] is True
    assert audit["feasible_candidate_ids"] == []


def test_design_and_rank_reject_invalid_cardinality() -> None:
    with pytest.raises(ValueError, match="exactly five"):
        cyclic_trials("sample", ["a", "b"])
    with pytest.raises(ValueError, match="non-empty unique"):
        rank_percentiles([], {})


def test_pareto_removes_a_dominated_feasible_candidate() -> None:
    utilities = {
        "a": dict.fromkeys("FPTQ", 0.9),
        "b": dict.fromkeys("FPTQ", 0.8),
        "c": dict.fromkeys("FPTQ", 0.1),
    }
    chosen, audit = constrained_pareto_choice(["b", "c", "a"], utilities)
    assert set(audit["feasible_candidate_ids"]) == {"a", "b"}
    assert audit["pareto_frontier_candidate_ids"] == ["a"]
    assert chosen == "a"


def test_three_method_pipeline_is_deterministic_and_no_replace(
    handoff_factory, tmp_path: Path,
) -> None:
    # Synthetic scores exercise engineering only; they are never research results.
    ingest = tmp_path / "ingest"
    ingest_delivery(handoff_factory(), CONFIG, ingest)
    manifest = ingest / "normalized-manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    rows = []
    for candidate in payload["candidates"]:
        primary = candidate["sample_id"] in payload["primary_sample_ids"]
        value = [101, 202, 303, 404, 505].index(candidate["seed"]) / 4
        rows.append({
            "candidate_id": candidate["candidate_id"], "sample_id": candidate["sample_id"],
            "seed": candidate["seed"], "candidate_video_sha256": candidate["video"]["sha256"],
            "measurement_status": "scored" if primary else "qualitative_only",
            "scores": {"F": value, "P": 1 - value, "T": value, "Q": 1 - value}
            if primary else None,
        })
    metrics = tmp_path / "synthetic-metrics.jsonl"
    metrics.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    design = tmp_path / "design"
    replay_design = tmp_path / "design-replay"
    create_design(metrics, manifest, CONFIG, design)
    create_design(metrics, manifest, CONFIG, replay_design)
    assert sha256_file(design / "design.json") == sha256_file(replay_design / "design.json")
    selection = tmp_path / "selection"
    replay = tmp_path / "selection-replay"
    summary = select_design(design / "design.json", metrics, CONFIG, selection)
    select_design(design / "design.json", metrics, CONFIG, replay)
    assert summary["selection_records"] == 315
    assert summary["comparisons"] == 42
    for name in ["selections.jsonl", "comparisons.json", "selection-summary.json", "selection-lock.json"]:
        assert sha256_file(selection / name) == sha256_file(replay / name)
    selected = [json.loads(line) for line in (selection / "selections.jsonl").read_text().splitlines()]
    assert {row["method"] for row in selected} == {"random", "equal-linear", "constrained-pareto"}
    assert len({(row["trial_id"], row["n"], row["method"]) for row in selected}) == 315
    assert all(row["candidate_id"] in row["subset_candidate_ids"] for row in selected)
    with pytest.raises(FileExistsError, match="already exists"):
        create_design(metrics, manifest, CONFIG, design)
    with pytest.raises(FileExistsError, match="already exists"):
        select_design(design / "design.json", metrics, CONFIG, selection)
    metrics.write_text(metrics.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="design/metrics identity mismatch"):
        select_design(design / "design.json", metrics, CONFIG, tmp_path / "bad-identity")
