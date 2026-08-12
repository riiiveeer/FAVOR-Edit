# Robust Video Editing — W1 Pipeline

This repository implements the first-week reproducibility pipeline described in
`proposal.md`: DAVIS input preparation, deterministic candidate planning,
generation/reward caching, mock and AnyV2V execution adapters, verification,
and reporting.

The W1 experiment contains 10 DAVIS train inputs and five seeds per input
(`101, 202, 303, 404, 505`), for 50 candidates. IVEBench is explicitly excluded
from development and tuning.

## Local setup

```powershell
uv sync --python 3.11
uv run w1 --help
uv run pytest
```

`imageio-ffmpeg` provides a pinned local ffmpeg executable for media work, so a
system-wide ffmpeg installation is not required.

## Research dependency boundary

AnyV2V is not vendored into this repository. Remote execution clones and pins
the official `TIGER-AI-Lab/AnyV2V` repository. AnyV2V is MIT-licensed, while its
README notes that the upstream I2VGen-XL component has no declared license.
This adapter is therefore intended for internal research validation only.

