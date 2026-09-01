from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from defense_mvp.cli import app
from defense_mvp.config import load_config


CONFIG = Path("configs/defense_mvp/pilot.yaml")


def test_frozen_config_counts() -> None:
    cfg = load_config(CONFIG)
    assert len(cfg.sample_ids) == 10
    assert cfg.candidate_count == 50
    assert cfg.quantitative_candidate_count == 35
    assert cfg.qualitative_candidate_count == 15
    assert cfg.comparisons_per_annotator == 42


def test_config_rejects_protocol_drift(tmp_path: Path) -> None:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    payload["n_values"] = [1, 2, 5]
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="N values must be 1/2/4"):
        load_config(path)


def test_validate_config_cli() -> None:
    result = CliRunner().invoke(app, ["validate-config", "--config", str(CONFIG)])
    assert result.exit_code == 0, result.output
    assert '"candidates": 50' in result.output
    assert '"comparisons_per_annotator": 42' in result.output
