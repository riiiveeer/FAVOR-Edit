"""Run dependency-free JS failure tests when Node is available for development."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_playback_network_and_lifecycle():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed only for frontend development tests")
    script = Path(__file__).with_name("annotation_playback.test.cjs")
    run = subprocess.run([node, "--test", str(script)], capture_output=True, text=True, timeout=30, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
