"""Batch backend contract for E1 judge adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import RuntimeConfigV2


class JudgeBackend(ABC):
    name: str

    @abstractmethod
    def run_batch(self, requests_path: Path, output_dir: Path, runtime: RuntimeConfigV2) -> None:
        """Run a request JSONL and atomically publish one envelope per judge_key."""
