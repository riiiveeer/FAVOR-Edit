"""E1 human annotation service and adjudication (implemented in E1-annotation-tool-v01)."""

from pathlib import Path
from typing import List, Optional


def run_annotation_server(
    pairs: Path, packets: Path, annotator_id: str, output: Path, host: str, port: int
) -> None:
    raise NotImplementedError("annotation server implemented in E1-annotation-tool-v01")


def adjudicate(annotations: List[Path], third: Optional[Path], output: Path) -> None:
    raise NotImplementedError("adjudication implemented in E1-annotation-tool-v01")
