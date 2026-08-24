"""E1 judge runner, plan, locking, and merge (implemented in E1-runner-cache-v01)."""

from pathlib import Path
from typing import List, Optional


def build_judge_plan(pairs: Path, config: Path, output: Path) -> None:
    raise NotImplementedError("judge plan implemented in E1-runner-cache-v01")


def run_judge(
    backend: str,
    plan: Path,
    experiment_dir: Path,
    cache: Path,
    split: Optional[str],
    judge_python: Optional[str],
    judge_script: Optional[str],
) -> None:
    raise NotImplementedError("runner implemented in E1-runner-cache-v01")


def unlock(experiment_dir: Path, reason: str) -> None:
    raise NotImplementedError("lock implemented in E1-runner-cache-v01")


def merge_results(inputs: List[Path], output: Path) -> None:
    raise NotImplementedError("merge implemented in E1-runner-cache-v01")
