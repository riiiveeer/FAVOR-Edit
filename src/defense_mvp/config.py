"""Configuration loading for the frozen Defense MVP protocol."""

from pathlib import Path

import yaml

from .models import DefenseConfigV1


def load_config(path: Path) -> DefenseConfigV1:
    return DefenseConfigV1.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
