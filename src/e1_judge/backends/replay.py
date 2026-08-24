"""Batch replay backend keyed by immutable judge_key."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..models import RuntimeConfigV2
from .base import JudgeBackend


class ReplayBackend(JudgeBackend):
    name = "replay"

    def run_batch(self, requests_path: Path, output_dir: Path, runtime: RuntimeConfigV2) -> None:
        source_dir = Path(runtime.adapter.replay_source or "")
        output_dir.mkdir(parents=True, exist_ok=True)
        for line in Path(requests_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            request = json.loads(line)
            source = source_dir / f"{request['judge_key']}.json"
            if not source.is_file():
                continue
            target = output_dir / source.name
            temporary = target.with_suffix(".tmp")
            shutil.copy2(source, temporary)
            temporary.replace(target)
