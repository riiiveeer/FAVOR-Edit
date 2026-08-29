"""E2 fixed protocol validation."""

from pathlib import Path
from typing import Optional

import yaml

from w1_pipeline.hashing import sha256_file
from w1_pipeline.models import ExperimentSpec

from .models import E2ConfigV1


def load_config(path: Path, w1_manifest: Optional[Path] = None) -> E2ConfigV1:
    config = E2ConfigV1.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    if w1_manifest is not None:
        spec = ExperimentSpec.model_validate(yaml.safe_load(Path(w1_manifest).read_text(encoding="utf-8")))
        if spec.dataset != config.dataset or spec.split != config.split:
            raise ValueError("E2 dataset/split must match the fixed W1 manifest")
        if spec.seeds != config.base_seeds:
            raise ValueError("E2 base seeds must exactly match the W1 manifest")
        if [item.sample_id for item in spec.inputs] != config.sample_ids:
            raise ValueError("E2 sample order must exactly match the W1 manifest")
    return config


def config_sha256(path: Path) -> str:
    return sha256_file(Path(path))
