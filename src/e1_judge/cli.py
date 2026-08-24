"""Command-line entry point for the E1 judge reliability pipeline."""

from pathlib import Path
from typing import List, Optional

import typer

from .annotations import adjudicate, run_annotation_server
from .metrics import analyze
from .packets import build_packets
from .pairs import build_pairs
from .reporting import generate_report
from .runner import build_judge_plan, merge_results, run_judge, unlock

app = typer.Typer(no_args_is_help=True, help="E1 judge reliability pipeline")


@app.callback()
def main() -> None:
    """Build pairs, run judges, adjudicate human labels, and report reliability."""


@app.command("validate")
def validate_command(
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
) -> None:
    """Validate the E1 pilot configuration and prompt files."""
    from .models import validate_config

    validate_config(config)
    typer.echo(f"e1 config valid: {config}")


@app.command("build-pairs")
def build_pairs_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    audit: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    """Build the 100 unordered dev/frozen-eval pairs from the E0 outputs."""
    build_pairs(plan.resolve(), candidates.resolve(), audit.resolve(), config.resolve(), output.resolve())
    typer.echo(f"pairs written to {output.resolve()}")


@app.command("build-packets")
def build_packets_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    """Build per-pair media packets (symlinks + contact sheets + metadata)."""
    build_packets(pairs.resolve(), output_dir.resolve())
    typer.echo(f"packets written to {output_dir.resolve()}")


@app.command("annotate")
def annotate_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    packets: Path = typer.Option(..., exists=True, file_okay=False),
    annotator_id: str = typer.Option(...),
    output: Path = typer.Option(...),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765),
) -> None:
    """Run the single-user loopback human annotation service."""
    run_annotation_server(pairs.resolve(), packets.resolve(), annotator_id, output.resolve(), host, port)


@app.command("adjudicate")
def adjudicate_command(
    annotations: List[Path] = typer.Option(..., "--annotations", exists=True, dir_okay=False),
    third: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    """Adjudicate two annotators and apply a third for disputed pairs."""
    adjudicate([path.resolve() for path in annotations], third.resolve() if third else None, output.resolve())
    typer.echo(f"adjudicated labels written to {output.resolve()}")


@app.command("plan")
def plan_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    """Expand pairs into the 550 judge requests across four methods."""
    build_judge_plan(pairs.resolve(), config.resolve(), output.resolve())
    typer.echo(f"judge plan written to {output.resolve()}")


@app.command("run")
def run_command(
    backend: str = typer.Option(...),
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    experiment_dir: Path = typer.Option(...),
    cache: Path = typer.Option(...),
    split: Optional[str] = typer.Option(None),
    judge_python: Optional[str] = typer.Option(None),
    judge_script: Optional[str] = typer.Option(None),
) -> None:
    """Run pending judge requests with an exclusive lock and cache resume."""
    run_judge(backend, plan.resolve(), experiment_dir.resolve(), cache.resolve(), split, judge_python, judge_script)
    typer.echo(f"judge run complete in {experiment_dir.resolve()}")


@app.command("unlock")
def unlock_command(
    experiment_dir: Path = typer.Option(...),
    reason: str = typer.Option(...),
) -> None:
    """Explicitly remove a stale run lock after user confirmation."""
    unlock(experiment_dir.resolve(), reason)
    typer.echo(f"lock released for {experiment_dir.resolve()}")


@app.command("merge-results")
def merge_results_command(
    inputs: List[Path] = typer.Option(..., "--input", exists=True, dir_okay=False),
    output: Path = typer.Option(...),
) -> None:
    """Merge dev-final and frozen-eval results, rejecting duplicate request IDs."""
    merge_results([path.resolve() for path in inputs], output.resolve())
    typer.echo(f"merged results written to {output.resolve()}")


@app.command("analyze")
def analyze_command(
    pairs: Path = typer.Option(..., exists=True, dir_okay=False),
    human: Path = typer.Option(..., exists=True, dir_okay=False),
    results: Path = typer.Option(..., exists=True, dir_okay=False),
    config: Path = typer.Option(Path("configs/e1/pilot.yaml"), exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    """Compute reliability metrics, position bias, ranking, and categories."""
    analyze(pairs.resolve(), human.resolve(), results.resolve(), config.resolve(), output_dir.resolve())
    typer.echo(f"analysis written to {output_dir.resolve()}")


@app.command("verify")
def verify_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    results: Path = typer.Option(..., exists=True, dir_okay=False),
    human: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
    expect_requests: Optional[int] = typer.Option(None),
    strict: bool = typer.Option(False),
) -> None:
    """Verify judge results against the plan and optional human labels."""
    from .verification import verify_results

    verify_results(plan.resolve(), results.resolve(), human.resolve() if human else None, expect_requests, strict)
    typer.echo("verify passed")


@app.command("report")
def report_command(
    analysis: Path = typer.Option(..., exists=True, file_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    """Generate the E1 report and figures."""
    generate_report(analysis.resolve(), output_dir.resolve())
    typer.echo(f"report written to {output_dir.resolve()}")


if __name__ == "__main__":
    app()

