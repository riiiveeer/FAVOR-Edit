"""Command-line entry point for the CPU-first E2 Best-of-N pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer

from .config import load_config

app = typer.Typer(help="E2 Best-of-N CPU-first engineering pipeline")


@app.command("validate")
def validate_command(
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    w1_manifest: Path = typer.Option(Path("configs/w1_manifest.yaml"), exists=True, dir_okay=False),
) -> None:
    value = load_config(config.resolve(), w1_manifest.resolve())
    typer.echo(json.dumps({"valid": True, "experiment_id": value.experiment_id, "candidates": 80}, sort_keys=True))


@app.command("plan-generation")
def plan_generation_command(
    e0_plan: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    snapshot: str = typer.Option(...),
) -> None:
    from .pool import plan_generation_extension

    payload = plan_generation_extension(e0_plan.resolve(), config.resolve(), output.resolve(), snapshot)
    typer.echo(json.dumps({"inversions": len(payload["inversions"]), "candidates": 30, "output": str(output.resolve())}, sort_keys=True))


@app.command("build-pool")
def build_pool_command(
    e0_plan: Path = typer.Option(..., exists=True, dir_okay=False),
    e0_candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    e0_audit: Path = typer.Option(..., exists=True, dir_okay=False),
    extension_plan: Path = typer.Option(..., exists=True, dir_okay=False),
    extension_candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    extension_audit: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .pool import build_candidate_pool

    payload = build_candidate_pool(
        e0_plan.resolve(), e0_candidates.resolve(), e0_audit.resolve(),
        extension_plan.resolve(), extension_candidates.resolve(), extension_audit.resolve(),
        config.resolve(), output.resolve(), verify_files=True,
    )
    typer.echo(json.dumps({"candidates": payload["candidate_count"], "samples": payload["sample_count"], "output": str(output.resolve())}, sort_keys=True))


@app.command("prepare")
def prepare_command(
    pool: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    e1_decision: Path = typer.Option(..., exists=True, dir_okay=False),
    reward_v0: Path = typer.Option(..., exists=True, dir_okay=False),
    frozen_config: Path = typer.Option(..., exists=True, dir_okay=False),
    frozen_protocol: Path = typer.Option(..., exists=True, dir_okay=False),
    runtime: Path = typer.Option(..., exists=True, dir_okay=False),
    output_root: Path = typer.Option(...),
    prepare_id: str = typer.Option(...),
    auxiliary_rubric: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .preparation import E2PreparationError, prepare_e2

    try:
        result = prepare_e2(
            pool.resolve(), config.resolve(), e1_decision.resolve(), reward_v0.resolve(),
            frozen_config.resolve(), frozen_protocol.resolve(), runtime.resolve(), output_root.resolve(),
            prepare_id, auxiliary_rubric.resolve() if auxiliary_rubric else None,
        )
    except E2PreparationError as exc:
        typer.echo(json.dumps({
            "status": "failed", "stage": exc.stage, "error": str(exc),
            "failure_root": str(exc.failure_root) if exc.failure_root else None,
            "staging_root": str(exc.staging_root) if exc.staging_root else None,
        }, sort_keys=True), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(result, sort_keys=True))


@app.command("run")
def run_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    runtime: Path = typer.Option(..., exists=True, dir_okay=False),
    experiment_dir: Path = typer.Option(...),
    cache: Path = typer.Option(...),
) -> None:
    from .runner import run_e2_judge

    typer.echo(json.dumps(run_e2_judge(plan.resolve(), runtime.resolve(), experiment_dir.resolve(), cache.resolve()), sort_keys=True))


@app.command("unlock")
def unlock_command(
    experiment_dir: Path = typer.Option(..., exists=True, file_okay=False),
    reason: str = typer.Option(...),
) -> None:
    from .runner import unlock

    unlock(experiment_dir.resolve(), reason)
    typer.echo(json.dumps({"unlocked": str(experiment_dir.resolve())}, sort_keys=True))


@app.command("qualify-rubric")
def qualify_rubric_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    human: Path = typer.Option(..., exists=True, dir_okay=False),
    results: Path = typer.Option(..., exists=True, dir_okay=False),
    dev_metrics: Path = typer.Option(..., exists=True, dir_okay=False),
    e1_config: Path = typer.Option(..., exists=True, dir_okay=False),
    frozen_protocol: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .qualification import qualify_auxiliary_rubric

    payload = qualify_auxiliary_rubric(
        pairs.resolve(), human.resolve(), results.resolve(), dev_metrics.resolve(),
        e1_config.resolve(), frozen_protocol.resolve(), output.resolve(),
    )
    typer.echo(json.dumps({"decision": payload["decision"], "output": str(output.resolve())}, sort_keys=True))
    if payload["decision"] != "PASS_AUXILIARY_RUBRIC":
        raise typer.Exit(code=1)


@app.command("select")
def select_command(
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    design: Path = typer.Option(..., exists=True, dir_okay=False),
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    primary_results: Path = typer.Option(..., exists=True, dir_okay=False),
    reward_v0: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    measurement_mode: str = typer.Option("mock", help="mock, replay, or formal-command"),
    rubric_results: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    auxiliary_rubric: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .selection import select_candidates

    payload = select_candidates(
        config.resolve(), design.resolve(), pairs.resolve(), primary_results.resolve(),
        reward_v0.resolve(), output.resolve(), measurement_mode,
        rubric_results.resolve() if rubric_results else None,
        auxiliary_rubric.resolve() if auxiliary_rubric else None,
    )
    typer.echo(json.dumps({
        "selections": len(payload["selections"]), "human_comparisons": 80,
        "output": str(output.resolve()), "research_measurements": payload["research_measurements"],
    }, sort_keys=True))


@app.command("annotate")
def annotate_command(
    selection: Path = typer.Option(..., exists=True, dir_okay=False),
    packets: Path = typer.Option(..., exists=True, file_okay=False),
    annotator_id: str = typer.Option(...),
    output: Path = typer.Option(...),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8766, min=1, max=65535),
    comparison_filter: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .annotations import run_annotation_server

    run_annotation_server(
        selection.resolve(), packets.resolve(), annotator_id, output.resolve(), host, port,
        comparison_filter.resolve() if comparison_filter else None,
    )


@app.command("adjudicate")
def adjudicate_command(
    selection: Path = typer.Option(..., exists=True, dir_okay=False),
    annotation: List[Path] = typer.Option(..., exists=True, dir_okay=False),
    third: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    report: Path = typer.Option(...),
) -> None:
    from .annotations import adjudicate_e2

    records = adjudicate_e2(
        selection.resolve(), [path.resolve() for path in annotation],
        third.resolve() if third else None, output.resolve(), report.resolve(),
    )
    typer.echo(json.dumps({"adjudicated": len(records), "output": str(output.resolve())}, sort_keys=True))


@app.command("analyze")
def analyze_command(
    config: Path = typer.Option(Path("configs/e2/pilot.yaml"), exists=True, dir_okay=False),
    selection: Path = typer.Option(..., exists=True, dir_okay=False),
    adjudicated: Path = typer.Option(..., exists=True, dir_okay=False),
    agreement_report: Path = typer.Option(..., exists=True, dir_okay=False),
    pool: Path = typer.Option(..., exists=True, dir_okay=False),
    primary_results: Path = typer.Option(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
    rubric_results: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .analysis import analyze_e2

    payload = analyze_e2(
        config.resolve(), selection.resolve(), adjudicated.resolve(), agreement_report.resolve(),
        pool.resolve(), primary_results.resolve(), output_dir.resolve(),
        rubric_results.resolve() if rubric_results else None,
    )
    typer.echo(json.dumps({
        "status": payload["status"],
        "tie_aware_win_rate": payload["metrics"]["overall"]["tie_aware_win_rate"],
        "output_dir": str(output_dir.resolve()),
    }, sort_keys=True))


@app.command("report")
def report_command(
    analysis_dir: Path = typer.Option(..., exists=True, file_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    from .reporting import report_e2

    payload = report_e2(analysis_dir.resolve(), output_dir.resolve())
    typer.echo(json.dumps({"status": payload["status"], "output_dir": str(output_dir.resolve())}, sort_keys=True))


@app.command("verify")
def verify_command(
    preparation_root: Path = typer.Option(..., exists=True, file_okay=False),
    selection: Path = typer.Option(..., exists=True, dir_okay=False),
    adjudicated: Path = typer.Option(..., exists=True, dir_okay=False),
    analysis_dir: Path = typer.Option(..., exists=True, file_okay=False),
    report_dir: Path = typer.Option(..., exists=True, file_okay=False),
    primary_results: Path = typer.Option(..., exists=True, dir_okay=False),
    reward_v0: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    rubric_results: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    auxiliary_rubric: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .verification import verify_e2

    payload = verify_e2(
        preparation_root.resolve(), selection.resolve(), adjudicated.resolve(),
        analysis_dir.resolve(), report_dir.resolve(), primary_results.resolve(), reward_v0.resolve(),
        output.resolve(), rubric_results.resolve() if rubric_results else None,
        auxiliary_rubric.resolve() if auxiliary_rubric else None,
    )
    typer.echo(json.dumps(payload, sort_keys=True))
    if payload["status"] != "passed":
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
