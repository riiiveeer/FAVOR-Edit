"""Command backend invoking a separate judge environment."""

import json
import subprocess
from pathlib import Path

from .base import JudgeBackend


class CommandBackend(JudgeBackend):
    name = "command"

    def __init__(self, judge_python: str, judge_script: str):
        self.judge_python = judge_python
        self.judge_script = judge_script

    def run(self, request_path: Path, output_path: Path) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        temp = output_path.with_suffix(".tmp")
        proc = subprocess.run(
            [self.judge_python, self.judge_script, "--request", str(request_path), "--output", str(temp)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"command judge failed: {proc.stderr or proc.stdout}")
        if not temp.is_file():
            raise RuntimeError("command judge produced no output file")
        temp.replace(output_path)
