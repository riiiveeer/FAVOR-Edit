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

## Commands

```powershell
uv run w1 validate
uv run w1 prepare --davis-root D:\datasets\DAVIS
uv run w1 plan --prepared data\processed\w1\manifest.json --backend mock
uv run w1 run --backend mock --plan <plan.json> --experiment-dir <run-dir>
uv run w1 reward --backend mock --candidates <candidates.json> --output <rewards.json>
uv run w1 verify --candidates <candidates.json>
uv run w1 report --plan <plan.json> --candidates <candidates.json> --rewards <rewards.json> --output-dir <report-dir>
```

See `docs/SCHOOL_SERVER_DELIVERY.md` for the offline school-server delivery and
execution procedure. `docs/REMOTE_RUNBOOK.md` contains the shorter experiment
gate summary.

E1 schema-v2 的本地命令、真实人工标注、Qwen2.5-VL judge、冻结协议与 A6000
执行顺序见 [`docs/E1_A6000_RUNBOOK.md`](docs/E1_A6000_RUNBOOK.md)。该手册固定使用
新的 `E1-judge-pilot-v02` 目录，不会覆盖 E0 或旧 E1 产物。

## Research dependency boundary

AnyV2V is not vendored into this repository. Remote execution clones and pins
the official `TIGER-AI-Lab/AnyV2V` repository. AnyV2V is MIT-licensed, while its
README notes that the upstream I2VGen-XL component has no declared license.
This adapter is therefore intended for internal research validation only.
