"""One-process-per-batch command backend for independent judge environments."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..models import RuntimeConfigV2
from .base import JudgeBackend


class CommandBackendError(RuntimeError):
    def __init__(self, returncode: int, stdout: str, stderr: str):
        super().__init__(f"command judge exited {returncode}: {stderr or stdout}")
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CommandBackend(JudgeBackend):
    name = "command"

    def run_batch(self, requests_path: Path, output_dir: Path, runtime: RuntimeConfigV2) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            str(runtime.adapter.python), str(runtime.adapter.script),
            "--requests", str(requests_path),
            "--output-dir", str(output_dir),
            "--model-path", runtime.model.local_path,
        ]
        timeout = runtime.adapter.timeout_seconds or None
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        (output_dir / "adapter.stdout.log").write_text(proc.stdout or "", encoding="utf-8")
        (output_dir / "adapter.stderr.log").write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0:
            raise CommandBackendError(proc.returncode, proc.stdout or "", proc.stderr or "")
