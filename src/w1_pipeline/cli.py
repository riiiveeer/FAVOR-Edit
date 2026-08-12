"""Command-line entry point for the W1 pipeline."""

from pathlib import Path
from typing import List, Optional

import typer

from .data import load_spec, prepare_dataset, validate_prepared_manifest, validate_spec
from .backends import load_backend
from .planning import build_plan, code_snapshot, write_plan
from .runner import run_candidates
from .rewards import run_rewards
from .reporting import generate_report
from .verification import verify_candidates


app = typer.Typer(no_args_is_help=True, help="W1 reproducible video-editing pipeline")


@app.callback()
def main() -> None:
    """Prepare, execute, verify, and report the W1 experiment."""


@app.command()
def version() -> None:
    """Print the package version."""
    from . import __version__

    typer.echo(__version__)


@app.command("validate")
def validate_command(
    manifest: Path = typer.Option(Path("configs/w1_manifest.yaml"), exists=True, dir_okay=False),
    prepared: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    """Validate the W1 source specification and optionally a prepared manifest."""
    spec = load_spec(manifest)
    validate_spec(spec)
    typer.echo(f"source manifest valid: {len(spec.inputs)} inputs, {len(spec.seeds)} seeds")
    if prepared is not None:
        records = validate_prepared_manifest(prepared)
        typer.echo(f"prepared manifest valid: {len(records)} inputs")


@app.command("prepare")
def prepare_command(
    davis_root: Path = typer.Option(..., exists=True, file_okay=False),
    manifest: Path = typer.Option(Path("configs/w1_manifest.yaml"), exists=True, dir_okay=False),
    output_dir: Path = typer.Option(Path("data/processed/w1")),
) -> None:
    """Prepare the fixed DAVIS clips and masks used by W1."""
    records = prepare_dataset(load_spec(manifest), davis_root.resolve(), output_dir.resolve())
    typer.echo(f"prepared {len(records)} inputs at {output_dir.resolve()}")


@app.command("plan")
def plan_command(
    prepared: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(Path("artifacts/E0-anyv2v-w1-v01/plan.json")),
    backend: str = typer.Option("mock"),
    model_commit: str = typer.Option("mock-model-v1"),
    anyv2v_commit: str = typer.Option("mock-anyv2v-v1"),
    seed: List[int] = typer.Option([101, 202, 303, 404, 505], "--seed"),
) -> None:
    """Expand 10 prepared inputs into 10 inversions and 50 candidates."""
    inversions, candidates = build_plan(
        prepared.resolve(), seed, backend, model_commit, anyv2v_commit, code_snapshot()
    )
    write_plan(output.resolve(), inversions, candidates)
    typer.echo(f"planned {len(inversions)} inversions and {len(candidates)} candidates at {output.resolve()}")


@app.command("run")
def run_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    experiment_dir: Path = typer.Option(...),
    cache: Path = typer.Option(Path("artifacts/cache.sqlite3")),
    backend: str = typer.Option("mock"),
    anyv2v_root: Optional[Path] = typer.Option(None, file_okay=False),
    python_executable: str = typer.Option("python"),
    device: str = typer.Option("cuda:0"),
) -> None:
    """Run pending candidates and reuse successful cached results."""
    implementation = load_backend(backend, anyv2v_root, python_executable, device)
    records, hits = run_candidates(plan.resolve(), experiment_dir.resolve(), cache.resolve(), implementation)
    succeeded = sum(record.status.value == "succeeded" for record in records)
    typer.echo(f"completed: {succeeded}/{len(records)} succeeded; cache hits: {hits}")
    if succeeded != len(records):
        raise typer.Exit(code=1)


@app.command("reward")
def reward_command(
    candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    cache: Path = typer.Option(Path("artifacts/cache.sqlite3")),
    backend: str = typer.Option("mock"),
    model: str = typer.Option("mock-schema-v1"),
    prompt_version: str = typer.Option("w1-v0"),
    replay: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    """Run the non-research mock/replay reward interface."""
    results, hits = run_rewards(candidates.resolve(), cache.resolve(), backend, model, prompt_version, output.resolve(), replay)
    typer.echo(f"reward records: {len(results)}; cache hits: {hits}; research measurements: 0")


@app.command("verify")
def verify_command(
    candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    expected: int = typer.Option(50),
    compare: Optional[Path] = typer.Option(None, exists=True, dir_okay=False),
) -> None:
    """Verify candidate media, checksums, counts, and optional reproducibility."""
    result = verify_candidates(candidates.resolve(), expected, compare.resolve() if compare else None)
    typer.echo(json.dumps(result, indent=2))
    if not result["valid"]:
        raise typer.Exit(code=1)


@app.command("report")
def report_command(
    plan: Path = typer.Option(..., exists=True, dir_okay=False),
    candidates: Path = typer.Option(..., exists=True, dir_okay=False),
    rewards: Path = typer.Option(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(...),
) -> None:
    """Generate the W1 report and pipeline diagrams."""
    path = generate_report(plan.resolve(), candidates.resolve(), rewards.resolve(), output_dir.resolve())
    typer.echo(f"report written to {path}")


if __name__ == "__main__":
    app()
