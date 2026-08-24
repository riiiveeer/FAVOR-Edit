"""Abstract judge backend."""

from pathlib import Path


class JudgeBackend:
    """Run a single judge request, writing the parsed result to output_path."""

    name = "base"

    def run(self, request_path: Path, output_path: Path) -> None:
        raise NotImplementedError
