"""Strict replay backend: re-emits previously captured real results."""

import json
import shutil
from pathlib import Path

from .base import JudgeBackend


class ReplayBackend(JudgeBackend):
    name = "replay"

    def __init__(self, source_dir: Path):
        self.source_dir = Path(source_dir)

    def run(self, request_path: Path, output_path: Path) -> None:
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        key = request["judge_key"]
        source = self.source_dir / f"{key}.json"
        if not source.is_file():
            raise FileNotFoundError(f"replay result missing for key {key}")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output_path)
