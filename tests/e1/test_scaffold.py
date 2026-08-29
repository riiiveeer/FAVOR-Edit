from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner

from e1_judge.cli import app


def test_cli_exposes_v2_commands_and_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "validate", "build-pairs", "build-packets", "annotate", "adjudicate", "plan", "run",
        "prepare-phase3", "unlock", "merge-results", "analyze", "freeze", "verify",
        "verify-preparation", "report",
    ):
        assert command in result.stdout


def test_validate_real_config():
    runner = CliRunner()
    root = Path(__file__).parents[2]
    result = runner.invoke(app, [
        "validate", "--config", str(root / "configs" / "e1" / "pilot.yaml"),
        "--runtime", str(root / "configs" / "e1" / "runtime-mock.yaml"),
    ])
    assert result.exit_code == 0, result.stdout
    assert "schema-v2" in result.stdout


def test_qwen_adapter_help_has_no_heavy_import_requirement():
    script = Path(__file__).parents[2] / "scripts" / "e1_judge_qwen25_vl.py"
    result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--requests" in result.stdout and "--model-path" in result.stdout
