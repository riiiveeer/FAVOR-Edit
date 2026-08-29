"""Command-line entry point for the CPU-first E2 Best-of-N pipeline."""

from __future__ import annotations

import json
from pathlib import Path

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
