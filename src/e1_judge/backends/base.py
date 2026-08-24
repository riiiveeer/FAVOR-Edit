"""Abstract judge backend (implemented in E1-runner-cache-v01)."""


class JudgeBackend:
    def run(self, request_path, output_path) -> None:
        raise NotImplementedError
