"""Command-line interface for the CPU-only Defense MVP."""

import json
from pathlib import Path

import typer

from .archive import extract_delivery_archive
from .config import load_config
from .ingest import ingest_delivery, verify_delivery


app = typer.Typer(no_args_is_help=True, help="CPU-only audited video-edit selection MVP")


@app.command("version")
def version_command() -> None:
    from . import __version__

    typer.echo(__version__)


@app.command("validate-config")
def validate_config_command(
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    cfg = load_config(config)
    typer.echo(json.dumps({
        "valid": True,
        "experiment_id": cfg.experiment_id,
        "samples": len(cfg.sample_ids),
        "candidates": cfg.candidate_count,
        "quantitative_candidates": cfg.quantitative_candidate_count,
        "qualitative_candidates": cfg.qualitative_candidate_count,
        "comparisons_per_annotator": cfg.comparisons_per_annotator,
    }, sort_keys=True))


@app.command("verify-delivery")
def verify_delivery_command(
    delivery: Path = typer.Option(..., exists=True, file_okay=False),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    _, report = verify_delivery(delivery, config)
    typer.echo(json.dumps(report, sort_keys=True))


@app.command("ingest")
def ingest_command(
    delivery: Path = typer.Option(..., exists=True, file_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    receipt = ingest_delivery(delivery, config, output)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("extract-delivery")
def extract_delivery_command(
    archive: Path = typer.Option(..., exists=True, dir_okay=False),
    checksum: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    receipt = extract_delivery_archive(archive, checksum, config, output)
    typer.echo(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    app()
