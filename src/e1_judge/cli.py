"""CLI for the E1 schema-v2 judge reliability pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer

app = typer.Typer(no_args_is_help=True, help="E1 schema-v2 judge reliability pipeline")


@app.callback()
def main() -> None:
    """Build pairs, label media, run judges, freeze, analyze, and report."""


@app.command("validate")
def validate_command(
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    runtime: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .models import load_runtime_config, validate_config

    validate_config(config.resolve())
    if runtime:
        load_runtime_config(runtime.resolve())
    typer.echo(f"e1 schema-v2 config valid: {config.resolve()}")


@app.command("build-pairs")
def build_pairs_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    audit: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .pairs import build_pairs

    records = build_pairs(plan.resolve(), candidates.resolve(), audit.resolve(), config.resolve(), output.resolve())
    typer.echo(json.dumps({"pairs": len(records), "output": str(output.resolve())}))


@app.command("build-packets")
def build_packets_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    from .packets import build_packets

    manifest = build_packets(pairs.resolve(), output_dir.resolve())
    typer.echo(json.dumps({"pairs": len(manifest["pairs"]), "output": str(output_dir.resolve())}))


@app.command("annotate")
def annotate_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    packets: Path = typer.Option(..., exists=True, file_okay=False),
    annotator_id: str = typer.Option(...),
    output: Path = typer.Option(...),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765),
    pair_filter: Optional[Path] = typer.Option(
        None, exists=True, dir_okay=False,
        help="Optional JSON disputed_pair_ids report for third-party adjudication",
    ),
) -> None:
    from .annotations import run_annotation_server

    run_annotation_server(
        pairs.resolve(), packets.resolve(), annotator_id, output.resolve(), host, port,
        pair_filter.resolve() if pair_filter else None,
    )


@app.command("adjudicate")
def adjudicate_command(
    annotations: List[Path] = typer.Option(..., "--annotations", exists=True, dir_okay=False),
    third: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    report: Path = typer.Option(...),
) -> None:
    from .annotations import adjudicate

    records = adjudicate(
        [path.resolve() for path in annotations], third.resolve() if third else None,
        output.resolve(), report.resolve(),
    )
    typer.echo(json.dumps({"labels": len(records), "output": str(output.resolve())}))


@app.command("plan")
def plan_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    packets: Path = typer.Option(..., exists=True),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    runtime: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .runner import build_judge_plan

    requests = build_judge_plan(
        pairs.resolve(), packets.resolve(), config.resolve(), runtime.resolve(), output.resolve()
    )
    typer.echo(json.dumps({"requests": len(requests), "output": str(output.resolve())}))


@app.command("run")
def run_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    runtime: Path = typer.Option(..., exists=True, dir_okay=False),
    experiment_dir: Path = typer.Option(...),
    cache: Path = typer.Option(...),
    split: Optional[str] = typer.Option(None),
    request_id: Optional[List[str]] = typer.Option(None, "--request-id"),
) -> None:
    from .runner import run_judge

    summary = run_judge(
        plan.resolve(), runtime.resolve(), experiment_dir.resolve(), cache.resolve(), split, request_id
    )
    typer.echo(json.dumps(summary, sort_keys=True))


@app.command("unlock")
def unlock_command(experiment_dir: Path = typer.Option(...), reason: str = typer.Option(...)) -> None:
    from .runner import unlock

    unlock(experiment_dir.resolve(), reason)
    typer.echo(f"lock released for {experiment_dir.resolve()}")


@app.command("merge-results")
def merge_results_command(
    inputs: List[Path] = typer.Option(..., "--input", exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .runner import merge_results

    records = merge_results([path.resolve() for path in inputs], output.resolve())
    typer.echo(json.dumps({"results": len(records), "output": str(output.resolve())}))


@app.command("analyze")
def analyze_command(
    mode: str = typer.Option(..., help="dev or final"),
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    human: Path = typer.Option(..., exists=True, dir_okay=False),
    results: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
    frozen_protocol: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    from .metrics import analyze

    metrics = analyze(
        pairs.resolve(), human.resolve(), results.resolve(), config.resolve(), output_dir.resolve(),
        mode=mode, frozen_protocol=frozen_protocol.resolve() if frozen_protocol else None,
    )
    typer.echo(json.dumps({"mode": mode, "methods": len(metrics.get("methods", {}))}))


@app.command("freeze")
def freeze_command(
    dev_selection: Path = typer.Option(..., exists=True, dir_okay=False),
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    packets: Path = typer.Option(..., exists=True),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    runtime: Path = typer.Option(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    from .reporting import freeze_protocol

    protocol = freeze_protocol(
        dev_selection.resolve(), pairs.resolve(), packets.resolve(), config.resolve(),
        runtime.resolve(), output_dir.resolve(),
    )
    typer.echo(json.dumps(protocol, sort_keys=True))


@app.command("verify")
def verify_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    results: Path = typer.Option(..., exists=True, dir_okay=False),
    human: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    expect_requests: Optional[int] = typer.Option(None),
    strict: bool = typer.Option(False),
) -> None:
    from .verification import verify_results

    verify_results(plan.resolve(), results.resolve(), human.resolve() if human else None, expect_requests, strict)
    typer.echo("verify passed")


@app.command("report")
def report_command(
    analysis: Path = typer.Option(..., exists=True, file_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    from .reporting import generate_report

    report = generate_report(analysis.resolve(), output_dir.resolve())
    typer.echo(str(report))


if __name__ == "__main__":
    app()
