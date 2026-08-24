"""Tests for the E1 scaffold: package import and CLI command discovery."""

from typer.testing import CliRunner

from e1_judge.cli import app

runner = CliRunner()

EXPECTED_COMMANDS = {
    "validate",
    "build-pairs",
    "build-packets",
    "annotate",
    "adjudicate",
    "plan",
    "run",
    "unlock",
    "merge-results",
    "analyze",
    "verify",
    "report",
}


def test_e1_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in EXPECTED_COMMANDS:
        assert command in result.stdout


def test_e1_subcommand_help_available() -> None:
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--config" in result.stdout

