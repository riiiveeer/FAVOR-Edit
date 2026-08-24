"""E1 result verification (implemented in E1-metrics-v01)."""

from pathlib import Path
from typing import Optional


def verify_results(
    plan: Path, results: Path, human: Optional[Path], expect_requests: Optional[int], strict: bool
) -> None:
    raise NotImplementedError("verification implemented in E1-metrics-v01")
