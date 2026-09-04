"""D4 protocol tests use synthetic values only, never formal annotation answers."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from defense_mvp.aggregation import aggregate_choice, aggregate_verified_records
from defense_mvp.analysis import (
    analyze_aggregate,
    agreement_statistics,
    annotation_descriptives,
    cluster_bootstrap,
    cohen_kappa,
    fit_bradley_terry,
    outcome_metrics,
    proposed_outcome,
    rate_statistics,
)
from defense_mvp.analysis_models import CATEGORIES, FAMILIES, FIELDS, load_analysis_config
from defense_mvp.annotation_bundle import source_evidence, write_sums
from defense_mvp.annotation_models import Answers, canonical_answers
from defense_mvp.analysis_verification import verify_analysis_artifacts
from defense_mvp.cli import app
from defense_mvp.design import create_design
from defense_mvp.ingest import ingest_delivery
from defense_mvp.io import write_json
from defense_mvp.selection import select_design
from w1_pipeline.hashing import canonical_sha256, sha256_file


CONFIG = Path("configs/defense_mvp/analysis-v1.yaml")


def _comparison(family: str, sample: str, replicate: int, identical: bool = False, swap: bool = False) -> dict:
    comparator = "constrained-pareto-n1" if family == FAMILIES[0] else "equal-linear-n4"
    roles = (comparator, "constrained-pareto-n4") if swap else ("constrained-pareto-n4", comparator)
    digest_x = ("a" if identical else "b") * 64
    digest_y = digest_x if identical else "c" * 64
    return {
        "comparison_id": f"defense:{family}:{sample}:r{replicate}",
        "family": family,
        "trial_id": f"defense:{sample}:r{replicate}",
        "sample_id": sample,
        "replicate": replicate,
        "identical_selection": identical,
        "candidate_x": {"role": roles[0], "candidate_id": f"{sample}-x-{replicate}",
                        "video": {"relative_path": "x.mp4", "sha256": digest_x}},
        "candidate_y": {"role": roles[1], "candidate_id": f"{sample}-y-{replicate}",
                        "video": {"relative_path": "y.mp4", "sha256": digest_y}},
    }


def _observation(comparison_id: str, annotator: str, values=None, confidence=0.75, elapsed=2.0):
    canonical = dict(values or {field: "X" for field in FIELDS})
    return SimpleNamespace(
        comparison_id=comparison_id,
        annotator_id=annotator,
        canonical=canonical,
        screen=SimpleNamespace(confidence=confidence),
        current_view_elapsed_seconds=elapsed,
    )


def _aggregate_fixture(swap_every_other: bool = False) -> list[dict]:
    cfg = load_analysis_config(CONFIG)
    samples = [f"sample-{index}" for index in range(7)]
    comparisons = []
    for sample in samples:
        comparisons.extend(_comparison(FAMILIES[0], sample, replicate, swap=swap_every_other and replicate % 2 == 0)
                           for replicate in range(1, 5))
        comparisons.extend(_comparison(FAMILIES[1], sample, replicate, swap=swap_every_other and replicate % 2 == 0)
                           for replicate in range(1, 3))
    auto_ids = {
        item["comparison_id"]
        for item in [
            *[comparison for comparison in comparisons if comparison["family"] == FAMILIES[0]][:6],
            *[comparison for comparison in comparisons if comparison["family"] == FAMILIES[1]][:4],
        ]
    }
    for comparison in comparisons:
        if comparison["comparison_id"] in auto_ids:
            comparison["identical_selection"] = True
            comparison["candidate_y"]["video"]["sha256"] = comparison["candidate_x"]["video"]["sha256"]
    manual = [comparison for comparison in comparisons if comparison["comparison_id"] not in auto_ids]
    records_a, records_b = [], []
    values = ["X", "Y", "tie", "uncertain"]
    for index, comparison in enumerate(manual):
        left = {field: values[(index + field_index) % 4] for field_index, field in enumerate(FIELDS)}
        right = {field: values[(index + field_index + (index % 2)) % 4] for field_index, field in enumerate(FIELDS)}
        records_a.append(_observation(comparison["comparison_id"], "annotator-a", left, 0.5, index + 1.0))
        records_b.append(_observation(comparison["comparison_id"], "annotator-b", right, 0.75, index + 2.0))
    automatic = [
        {"comparison_id": comparison["comparison_id"], "source": "automatic_tie",
         "reason": "media_identity", "media_sha256": comparison["candidate_x"]["video"]["sha256"],
         "outcome": "tie"}
        for comparison in comparisons if comparison["comparison_id"] in auto_ids
    ]
    return aggregate_verified_records(comparisons, list(reversed(records_a)), records_b, automatic, cfg)


def test_analysis_config_is_strict_and_result_independent(tmp_path: Path) -> None:
    cfg = load_analysis_config(CONFIG)
    assert cfg.bootstrap.seed == 20260901
    assert cfg.bootstrap.iterations == 2000
    assert cfg.bootstrap.fields == list(FIELDS)
    assert cfg.families[FAMILIES[0]].total == 28
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    payload["bootstrap"]["iterations"] = 1999
    changed = tmp_path / "changed.yaml"
    changed.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="2000"):
        load_analysis_config(changed)
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    payload["unknown"] = "result-dependent"
    changed.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="Extra inputs"):
        load_analysis_config(changed)


@pytest.mark.parametrize("left", CATEGORIES)
@pytest.mark.parametrize("right", CATEGORIES)
def test_all_16_aggregation_combinations_are_symmetric(left: str, right: str) -> None:
    expected = (
        "uncertain" if "uncertain" in (left, right)
        else left if left == right
        else "tie" if "tie" in (left, right)
        else "uncertain"
    )
    assert aggregate_choice(left, right) == expected
    assert aggregate_choice(left, right) == aggregate_choice(right, left)


def test_aggregate_joins_by_id_once_and_resolves_roles() -> None:
    rows = _aggregate_fixture(swap_every_other=True)
    assert len(rows) == 42
    assert len({row["comparison_id"] for row in rows}) == 42
    assert sum(row["source"] == "human_pair" for row in rows) == 32
    assert sum(row["source"] == "automatic_tie" for row in rows) == 10
    assert {family: sum(row["family"] == family for row in rows) for family in FAMILIES} == {
        FAMILIES[0]: 28, FAMILIES[1]: 14,
    }
    assert all(row["human"] is None and set(row["aggregate"].values()) == {"tie"}
               for row in rows if row["source"] == "automatic_tie")
    assert {row["proposed_side"] for row in rows} == {"X", "Y"}


def test_screen_direction_flip_restores_the_same_canonical_method_choice() -> None:
    screen_a = Answers(overall="A", faithfulness="A", preservation="tie",
                       temporal_consistency="uncertain", visual_quality="B", confidence=0.75)
    screen_b = Answers(overall="B", faithfulness="B", preservation="tie",
                       temporal_consistency="uncertain", visual_quality="A", confidence=0.75)
    assert canonical_answers(screen_a, "A") == canonical_answers(screen_b, "B") == {
        "overall": "X", "faithfulness": "X", "preservation": "tie",
        "temporal_consistency": "uncertain", "visual_quality": "Y",
    }


def test_aggregate_rejects_missing_overlap_and_role_drift() -> None:
    cfg = load_analysis_config(CONFIG)
    samples = [f"sample-{index}" for index in range(7)]
    comparisons = [
        *[_comparison(FAMILIES[0], sample, replicate) for sample in samples for replicate in range(1, 5)],
        *[_comparison(FAMILIES[1], sample, replicate) for sample in samples for replicate in range(1, 3)],
    ]
    auto_comparisons = comparisons[:6] + comparisons[28:32]
    for comparison in auto_comparisons:
        comparison["identical_selection"] = True
        comparison["candidate_y"]["video"]["sha256"] = comparison["candidate_x"]["video"]["sha256"]
    automatic = [{"comparison_id": item["comparison_id"], "source": "automatic_tie", "reason": "media_identity",
                  "media_sha256": item["candidate_x"]["video"]["sha256"], "outcome": "tie"}
                 for item in auto_comparisons]
    manual = [item for item in comparisons if item not in auto_comparisons]
    a = [_observation(item["comparison_id"], "annotator-a") for item in manual]
    b = [_observation(item["comparison_id"], "annotator-b") for item in manual]
    with pytest.raises(ValueError, match="same manual"):
        aggregate_verified_records(comparisons, a[:-1], b, automatic, cfg)
    with pytest.raises(ValueError, match="duplicate manual"):
        aggregate_verified_records(comparisons, a + [a[0]], b, automatic, cfg)
    extra = _observation("defense:unexpected:sample:r1", "annotator-a")
    with pytest.raises(ValueError, match="same manual"):
        aggregate_verified_records(comparisons, a + [extra], b, automatic, cfg)
    overlapping = deepcopy(automatic)
    overlapping[0]["comparison_id"] = manual[0]["comparison_id"]
    with pytest.raises(ValueError, match="overlap"):
        aggregate_verified_records(comparisons, a, b, overlapping, cfg)
    comparisons[10]["candidate_x"]["role"] = "random-n4"
    with pytest.raises(ValueError, match="role"):
        aggregate_verified_records(comparisons, a, b, automatic, cfg)


def test_agreement_kappa_exact_and_automatic_exclusion() -> None:
    rows = _aggregate_fixture()
    agreement = agreement_statistics(rows)
    assert agreement["n"] == 32
    assert agreement["exact_five_field_agreement"]["denominator"] == 32
    for field in FIELDS:
        item = agreement["fields"][field]
        assert sum(sum(line) for line in item["confusion_matrix_rows_a_columns_b"]) == 32
        assert sum(item["marginal_a"].values()) == 32
        assert sum(item["marginal_b"].values()) == 32
        assert item["observed_agreement"] == pytest.approx(item["diagonal"] / 32)
    assert cohen_kappa([], [])["reason"] == "no_samples"
    degenerate = cohen_kappa(["tie", "tie"], ["tie", "tie"])
    assert degenerate["status"] == "undefined"
    assert degenerate["reason"] == "expected_agreement_is_one"
    assert cohen_kappa(["X", "X", "Y", "Y"], ["Y", "Y", "X", "X"])["value"] == -1.0


def test_rates_conserve_counts_and_role_swap_is_invariant() -> None:
    cfg = load_analysis_config(CONFIG)
    normal = _aggregate_fixture(False)
    swapped = _aggregate_fixture(True)
    # Make canonical decisive values follow the proposed side in both fixtures.
    for rows in (normal, swapped):
        for row in rows:
            if row["source"] == "human_pair":
                row["aggregate"]["overall"] = row["proposed_side"]
    for rows in (normal, swapped):
        rates = rate_statistics(rows, cfg)
        for family in FAMILIES:
            item = rates["all-42"][family]["overall"]
            assert item["wins"] + item["losses"] + item["ties"] + item["uncertain"] == item["total"]
            assert item["total"] == cfg.families[family].total
            assert item["tie_aware_win_rate"]["value"] == pytest.approx(
                (item["wins"] + 0.5 * item["ties"] + 0.5 * item["uncertain"]) / item["total"]
            )
    assert proposed_outcome(normal[-1], "overall") == proposed_outcome(swapped[-1], "overall") == "win"
    empty = outcome_metrics([], "overall")
    assert empty["decisive_win_rate"]["reason"] == "no_decisive"


def _edge(winner: str, loser: str, family: str) -> dict:
    return {"winner": winner, "loser": loser, "family": family}


def test_bradley_terry_states_and_centered_fit() -> None:
    p, n1, linear = "p", "n1", "linear"
    no_edges = fit_bradley_terry([p, n1, linear], [], 1e-10, 100, 60)
    assert no_edges["status"] == "no_decisive"
    only_one_family = [_edge(p, n1, FAMILIES[0]), _edge(n1, p, FAMILIES[0])]
    assert fit_bradley_terry([p, n1, linear], only_one_family, 1e-10, 100, 60)["status"] == "family_no_decisive"
    disconnected = [
        _edge(p, n1, FAMILIES[0]), _edge(n1, p, FAMILIES[0]),
        _edge(p, n1, FAMILIES[1]), _edge(n1, p, FAMILIES[1]),
    ]
    assert fit_bradley_terry([p, n1, linear], disconnected, 1e-10, 100, 60)["status"] == "insufficient_connectivity"
    separated = [
        _edge(p, n1, FAMILIES[0]), _edge(n1, p, FAMILIES[0]),
        _edge(p, linear, FAMILIES[1]),
    ]
    assert fit_bradley_terry([p, n1, linear], separated, 1e-10, 100, 60)["status"] == "separation"
    identifiable = [
        _edge(p, n1, FAMILIES[0]), _edge(p, n1, FAMILIES[0]), _edge(n1, p, FAMILIES[0]),
        _edge(p, linear, FAMILIES[1]), _edge(p, linear, FAMILIES[1]),
        _edge(p, linear, FAMILIES[1]), _edge(linear, p, FAMILIES[1]),
    ]
    fitted = fit_bradley_terry([p, n1, linear], identifiable, 1e-10, 100, 60)
    assert fitted["status"] == "ok"
    assert sum(fitted["abilities"].values()) == pytest.approx(0.0, abs=1e-12)
    assert fitted["abilities"][p] > fitted["abilities"][n1]
    assert fitted == fit_bradley_terry([p, n1, linear], identifiable, 1e-10, 100, 60)
    assert fit_bradley_terry([p, n1, linear], identifiable, 1e-30, 0, 60)["status"] == "not_converged"


def test_cluster_bootstrap_uses_whole_clusters_and_is_reproducible() -> None:
    rows = _aggregate_fixture()
    raw_a, summary_a = cluster_bootstrap(rows, ["overall"], FAMILIES, 20260901, 2000, 7)
    raw_b, summary_b = cluster_bootstrap(rows, ["overall"], FAMILIES, 20260901, 2000, 7)
    assert raw_a == raw_b
    assert summary_a == summary_b
    assert len(raw_a) == 2000
    assert all(len(item["draw"]) == 7 for item in raw_a)
    assert any(len(set(item["draw"])) < 7 for item in raw_a)
    for family in FAMILIES:
        metric = summary_a["metrics"][family]["overall"]
        assert metric["valid_replicates"] + metric["invalid_replicates"] == 2000
    with pytest.raises(ValueError, match="cluster cardinality"):
        cluster_bootstrap(
            [row for row in rows if row["sample_id"] != "sample-6"],
            ["overall"], FAMILIES, 1, 10, 7,
        )
    raw_missing, summary_missing = cluster_bootstrap(rows, ["overall"], ["missing-family"], 1, 10, 7)
    assert len(raw_missing) == 10
    missing = summary_missing["metrics"]["missing-family"]["overall"]
    assert missing["valid_replicates"] == 0
    assert missing["invalid_replicates"] == 10
    assert missing["invalid_reasons"] == {"no_samples": 10}
    assert missing["percentile_95_ci"]["status"] == "undefined"


def test_annotation_descriptives_never_claim_active_labor() -> None:
    result = annotation_descriptives(_aggregate_fixture())
    assert result["confidence"]["pooled"]["count"] == 64
    assert result["confidence"]["annotator-a"]["weighted_answers"] is False
    for annotator in ("annotator-a", "annotator-b"):
        assert result["elapsed"][annotator]["count"] == 32
        assert result["elapsed"][annotator]["semantics"] == "current-view-server-elapsed-not-active-labor"


def test_aggregate_loader_rejects_tamper_and_unknown_file(tmp_path: Path) -> None:
    from defense_mvp.aggregation import load_aggregate

    cfg = load_analysis_config(CONFIG)
    rows = _aggregate_fixture()
    root = tmp_path / "aggregate"
    root.mkdir()
    (root / "aggregate.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    manual = [{"comparison_id": row["comparison_id"], "family": row["family"], "sample_id": row["sample_id"],
               "annotator-a": row["human"]["annotator-a"]["canonical"],
               "annotator-b": row["human"]["annotator-b"]["canonical"]}
              for row in rows if row["source"] == "human_pair"]
    write_json(root / "agreement-input.json", {"schema_version": "1", "protocol": cfg.protocol,
                                                "scope": "manual-only", "records": manual})
    write_json(root / "input-manifest.json", {"schema_version": "1", "protocol": cfg.protocol, "inputs": {}})
    write_json(root / "aggregation-receipt.json", {
        "status": "passed", "protocol": cfg.protocol, "aggregate_records": 42,
        "human_pairs": 32, "automatic_ties": 10, "aggregate_canonical_sha256": canonical_sha256(rows),
        "environment": source_evidence(),
    })
    write_sums(root)
    assert load_aggregate(root, cfg) == rows
    (root / "unknown.txt").write_text("unexpected", encoding="utf-8")
    (root / "SHA256SUMS").unlink()
    write_sums(root)
    with pytest.raises(ValueError, match="unexpected aggregate inventory"):
        load_aggregate(root, cfg)


def _write_named_sums(root: Path, name: str) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != name)
    (root / name).write_text(
        "".join(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in paths),
        encoding="utf-8", newline="\n",
    )


def _synthetic_pipeline(handoff_factory, tmp_path: Path) -> dict[str, Path]:
    pilot = Path("configs/defense_mvp/pilot.yaml")
    root = tmp_path / "pipeline"
    ingest = root / "ingest"
    ingest_delivery(handoff_factory(), pilot, ingest)
    manifest_path = ingest / "normalized-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics = root / "metrics"
    metrics.mkdir()
    rows = []
    for candidate in manifest["candidates"]:
        primary = candidate["sample_id"] in manifest["primary_sample_ids"]
        value = [101, 202, 303, 404, 505].index(candidate["seed"]) / 4
        rows.append({
            "candidate_id": candidate["candidate_id"], "sample_id": candidate["sample_id"],
            "seed": candidate["seed"], "candidate_video_sha256": candidate["video"]["sha256"],
            "measurement_status": "scored" if primary else "qualitative_only",
            "scores": {"F": value, "P": 1 - value, "T": value, "Q": 1 - value} if primary else None,
        })
    (metrics / "metrics.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    write_json(metrics / "metrics-config-lock.json", {"fixture": True})
    write_json(metrics / "scoring-runtime.json", {
        "schema_version": "1", "cpu_only": True, "candidate_seconds": {}, "total_cpu_seconds": 5.0,
    })
    _write_named_sums(metrics, "METRICS_SHA256SUMS")
    design = root / "design"
    create_design(metrics / "metrics.jsonl", manifest_path, pilot, design)
    selection = root / "selection"
    select_design(design / "design.json", metrics / "metrics.jsonl", pilot, selection)
    return {"root": root, "ingest": manifest_path, "metrics": metrics, "design": design, "selection": selection}


def _write_synthetic_aggregate(root: Path, rows: list[dict], paths: dict[str, Path]) -> Path:
    cfg = load_analysis_config(CONFIG)
    aggregate = root / "aggregate"
    aggregate.mkdir()
    (aggregate / "aggregate.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8", newline="\n",
    )
    manual = [{"comparison_id": row["comparison_id"], "family": row["family"], "sample_id": row["sample_id"],
               "annotator-a": row["human"]["annotator-a"]["canonical"],
               "annotator-b": row["human"]["annotator-b"]["canonical"]}
              for row in rows if row["source"] == "human_pair"]
    write_json(aggregate / "agreement-input.json", {
        "schema_version": "1", "protocol": cfg.protocol, "scope": "manual-only", "records": manual,
    })
    current = {
        "analysis_config": CONFIG.resolve(),
        "comparisons": paths["selection"] / "comparisons.json",
        "selection_lock": paths["selection"] / "selection-lock.json",
        "selection_inventory": paths["selection"] / "SELECTION_SHA256SUMS",
        "metrics": paths["metrics"] / "metrics.jsonl",
        "metrics_lock": paths["metrics"] / "metrics-config-lock.json",
        "metrics_inventory": paths["metrics"] / "METRICS_SHA256SUMS",
        "design": paths["design"] / "design.json",
        "design_lock": paths["design"] / "design-lock.json",
        "design_inventory": paths["design"] / "DESIGN_SHA256SUMS",
        "ingest": paths["ingest"],
        "ingest_inventory": paths["ingest"].parent / "INGEST_SHA256SUMS",
    }
    write_json(aggregate / "input-manifest.json", {
        "schema_version": "1", "protocol": cfg.protocol,
        "inputs": {name: {"sha256": sha256_file(path)} for name, path in current.items()},
    })
    write_json(aggregate / "aggregation-receipt.json", {
        "status": "passed", "protocol": cfg.protocol, "aggregate_records": 42, "human_pairs": 32,
        "automatic_ties": 10, "aggregate_canonical_sha256": canonical_sha256(rows),
        "environment": source_evidence(),
    })
    write_sums(aggregate)
    return aggregate


def test_synthetic_analysis_output_no_replace_and_verifier_tamper(
    handoff_factory, tmp_path: Path, monkeypatch,
) -> None:
    pipeline = _synthetic_pipeline(handoff_factory, tmp_path)
    rows = _aggregate_fixture(swap_every_other=True)
    aggregate = _write_synthetic_aggregate(pipeline["root"], rows, pipeline)
    output = pipeline["root"] / "analysis"
    receipt = analyze_aggregate(
        aggregate, pipeline["selection"], pipeline["metrics"], pipeline["design"],
        pipeline["ingest"], CONFIG, output,
    )
    assert receipt["status"] == "passed"
    assert len((output / "bootstrap.jsonl").read_text(encoding="utf-8").splitlines()) == 2000
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["records"] == 42
    assert summary["human_pairs"] == 32
    assert summary["automatic_ties"] == 10
    assert summary["sample_clusters"] == 7
    with pytest.raises(FileExistsError, match="already exists"):
        analyze_aggregate(
            aggregate, pipeline["selection"], pipeline["metrics"], pipeline["design"],
            pipeline["ingest"], CONFIG, output,
        )
    replay = pipeline["root"] / "analysis-replay"
    analyze_aggregate(
        aggregate, pipeline["selection"], pipeline["metrics"], pipeline["design"],
        pipeline["ingest"], CONFIG, replay,
    )
    for name in (
        "summary.json", "main-table.csv", "agreement.csv", "confusion-matrices.json",
        "bootstrap.jsonl", "bt.json", "failure-cases.json", "input-manifest.json",
    ):
        assert (output / name).read_bytes() == (replay / name).read_bytes()
    assert json.loads((output / "costs.json").read_text(encoding="utf-8"))["entries"]["d2_selection_elapsed"] == {
        "reason": "no trusted timer in D2 receipt", "semantics": "selection algorithm elapsed",
        "source_path": None, "source_sha256": None, "status": "unavailable", "unit": "seconds", "value": None,
    }

    monkeypatch.setattr(
        "defense_mvp.analysis_verification.validate_formal_sources",
        lambda *args, **kwargs: ({"mode": "formal"}, rows, {"status": "complete"}),
    )
    verification = pipeline["root"] / "verification.json"
    result = verify_analysis_artifacts(
        pipeline["root"] / "bundle", pipeline["root"] / "left", pipeline["root"] / "right",
        pipeline["root"] / "dual.json", aggregate, output, pipeline["selection"], pipeline["metrics"],
        pipeline["design"], pipeline["ingest"], CONFIG, verification,
    )
    assert result["status"] == "passed"
    assert result["families"] == {FAMILIES[0]: 28, FAMILIES[1]: 14}
    with pytest.raises(FileExistsError, match="already exists"):
        verify_analysis_artifacts(
            pipeline["root"] / "bundle", pipeline["root"] / "left", pipeline["root"] / "right",
            pipeline["root"] / "dual.json", aggregate, output, pipeline["selection"], pipeline["metrics"],
            pipeline["design"], pipeline["ingest"], CONFIG, verification,
        )

    summary["records"] = 41
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "SHA256SUMS").unlink()
    write_sums(output)
    with pytest.raises(ValueError, match="summary recomputation mismatch"):
        verify_analysis_artifacts(
            pipeline["root"] / "bundle", pipeline["root"] / "left", pipeline["root"] / "right",
            pipeline["root"] / "dual.json", aggregate, output, pipeline["selection"], pipeline["metrics"],
            pipeline["design"], pipeline["ingest"], CONFIG, pipeline["root"] / "verification-tamper.json",
        )


def test_formal_source_gate_rejects_sha_practice_mixed_single_and_same_identity(monkeypatch, tmp_path: Path) -> None:
    import defense_mvp.aggregation as module

    cfg = load_analysis_config(CONFIG)
    bundle, left, right = (tmp_path / name for name in ("bundle", "left", "right"))
    dual, selection, metrics, design, ingest = (
        tmp_path / "dual.json", tmp_path / "selection", tmp_path / "metrics",
        tmp_path / "design", tmp_path / "ingest.json",
    )
    path_to_pin = {
        (bundle / "bundle.json").resolve(): cfg.input_pins["bundle"],
        (left / "SHA256SUMS").resolve(): cfg.input_pins["annotator_a_inventory"],
        (right / "SHA256SUMS").resolve(): cfg.input_pins["annotator_b_inventory"],
        dual.resolve(): cfg.input_pins["dual_verification"],
        Path("configs/defense_mvp/pilot.yaml").resolve(): cfg.input_pins["pilot"],
        (selection / "comparisons.json").resolve(): cfg.input_pins["comparisons"],
        (selection / "selection-lock.json").resolve(): cfg.input_pins["selection_lock"],
    }
    monkeypatch.setattr(module, "sha256_file", lambda path: path_to_pin.get(Path(path).resolve(), "f" * 64))
    monkeypatch.setattr(module, "verify_sums", lambda *args, **kwargs: {})
    locations = {"selection": str(selection.resolve()), "metrics": str(metrics.resolve()),
                 "design": str(design.resolve()), "ingest": str(ingest.resolve()),
                 "pilot": str(Path("configs/defense_mvp/pilot.yaml").resolve())}
    monkeypatch.setattr(module, "load_bundle", lambda path: {"mode": "practice", "input_locations": locations})
    with pytest.raises(ValueError, match="formal annotation bundles only"):
        module.validate_formal_sources(bundle, left, right, dual, selection, metrics, design, ingest, cfg)

    mixed = dict(locations)
    mixed["metrics"] = str((tmp_path / "other-metrics").resolve())
    monkeypatch.setattr(module, "load_bundle", lambda path: {"mode": "formal", "input_locations": mixed})
    with pytest.raises(ValueError, match="input location mismatch"):
        module.validate_formal_sources(bundle, left, right, dual, selection, metrics, design, ingest, cfg)

    formal_bundle = {"mode": "formal", "input_locations": locations, "comparisons": []}
    monkeypatch.setattr(module, "load_bundle", lambda path: formal_bundle)
    single = {"status": "complete", "mode": "formal", "scope": "single", "exported_answers": 32,
              "manual_per_annotator": 32, "automatic_ties_shared": 10}
    monkeypatch.setattr(module, "verify_annotations", lambda *args, **kwargs: single)
    monkeypatch.setattr(module, "read_json", lambda path: single)
    with pytest.raises(ValueError, match="completeness gate"):
        module.validate_formal_sources(bundle, left, right, dual, selection, metrics, design, ingest, cfg)

    complete = {"status": "complete", "mode": "formal", "scope": "dual", "exported_answers": 64,
                "manual_per_annotator": 32, "automatic_ties_shared": 10}
    monkeypatch.setattr(module, "verify_annotations", lambda *args, **kwargs: complete)
    monkeypatch.setattr(module, "read_json", lambda path: complete)
    same = SimpleNamespace(annotator_id="annotator-a")
    monkeypatch.setattr(module, "_read_export_records", lambda *args, **kwargs: (same, []))
    with pytest.raises(ValueError, match="identities"):
        module.validate_formal_sources(bundle, left, right, dual, selection, metrics, design, ingest, cfg)

    bad_hash = dict(path_to_pin)
    bad_hash[(bundle / "bundle.json").resolve()] = "0" * 64
    monkeypatch.setattr(module, "sha256_file", lambda path: bad_hash.get(Path(path).resolve(), "f" * 64))
    with pytest.raises(ValueError, match="frozen formal input drift: bundle"):
        module.validate_formal_sources(bundle, left, right, dual, selection, metrics, design, ingest, cfg)


@pytest.mark.parametrize("command", ["aggregate", "analyze", "verify-analysis"])
def test_d4_cli_help(command: str) -> None:
    result = CliRunner().invoke(app, [command, "--help"])
    assert result.exit_code == 0, result.output
