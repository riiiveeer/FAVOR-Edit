"""Command-line interface for the CPU-only Defense MVP."""

import json
from pathlib import Path
from typing import List, Optional

import typer

from .archive import extract_delivery_archive
from .config import load_config
from .design import create_design
from .ingest import ingest_delivery, verify_delivery
from .metrics import score_ingest
from .selection import select_design


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
    compat_profile: Optional[str] = typer.Option(None),
) -> None:
    _, report = verify_delivery(delivery, config, compat_profile)
    typer.echo(json.dumps(report, sort_keys=True))


@app.command("ingest")
def ingest_command(
    delivery: Path = typer.Option(..., exists=True, file_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
    compat_profile: Optional[str] = typer.Option(None),
) -> None:
    receipt = ingest_delivery(delivery, config, output, compat_profile)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("score")
def score_command(
    ingest: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    receipt = score_ingest(ingest, config, output)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("design")
def design_command(
    metrics: Path = typer.Option(..., exists=True, dir_okay=False),
    ingest: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    receipt = create_design(metrics, ingest, config, output)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("select")
def select_command(
    design: Path = typer.Option(..., exists=True, dir_okay=False),
    metrics: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
) -> None:
    receipt = select_design(design, metrics, config, output)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("extract-delivery")
def extract_delivery_command(
    archive: Path = typer.Option(..., exists=True, dir_okay=False),
    checksum: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    config: Path = typer.Option(
        Path("configs/defense_mvp/pilot.yaml"), exists=True, dir_okay=False
    ),
    compat_profile: Optional[str] = typer.Option(None),
) -> None:
    receipt = extract_delivery_archive(archive, checksum, config, output, compat_profile)
    typer.echo(json.dumps(receipt, sort_keys=True))


@app.command("prepare-annotation")
def prepare_annotation_command(
    selection: Path = typer.Option(..., exists=True, file_okay=False),
    ingest: Path = typer.Option(..., exists=True, dir_okay=False),
    output: Path = typer.Option(...),
    mode: str = typer.Option(..., help="formal or practice; practice can never count as formal evidence"),
    config: Path = typer.Option(Path("configs/defense_mvp/annotation-v1.yaml")),
    pilot: Path = typer.Option(Path("configs/defense_mvp/pilot.yaml")),
    metrics: Optional[Path] = typer.Option(None),
    design: Optional[Path] = typer.Option(None),
    fixture_native_media: bool = typer.Option(False, help="Practice-only fake-byte unit fixtures; never formal media"),
) -> None:
    from .annotation_bundle import prepare_annotation
    typer.echo(json.dumps(prepare_annotation(selection, ingest, output, mode, config, pilot, metrics, design, fixture_native_media), sort_keys=True))


@app.command("annotate")
def annotate_command(
    bundle: Path = typer.Option(..., exists=True, file_okay=False),
    annotator_id: str = typer.Option(..., help="annotator-a or annotator-b"),
    output: Path = typer.Option(..., help="Independent session directory, basename equals annotator ID"),
    resume: bool = typer.Option(False, help="Explicitly resume the same bundle/protocol/identity"),
    port: int = typer.Option(8765, min=0, max=65535),
) -> None:
    from .annotation_server import serve_annotation
    serve_annotation(bundle, annotator_id, output, resume, port)


@app.command("export-annotations")
def export_annotations_command(
    bundle: Path = typer.Option(..., exists=True, file_okay=False),
    session: Path = typer.Option(..., exists=True, file_okay=False),
    output: Path = typer.Option(...),
) -> None:
    from .annotation_export import export_annotations
    typer.echo(json.dumps(export_annotations(bundle, session, output), sort_keys=True))


@app.command("verify-annotations")
def verify_annotations_command(
    bundle: Path = typer.Option(..., exists=True, file_okay=False),
    exports: Optional[List[Path]] = typer.Option(None, "--export", exists=True, file_okay=False),
    allow_practice: bool = typer.Option(False, help="Verify practice engineering only, never formal evidence"),
) -> None:
    from .annotation_export import verify_annotations
    typer.echo(json.dumps(verify_annotations(bundle, exports, allow_practice), sort_keys=True))


if __name__ == "__main__":
    app()
