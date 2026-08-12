# A6000 Runbook for W1

The real W1 experiment must not start until the SSH preflight reports an
NVIDIA A6000, enough free VRAM for the smoke test, and at least 100 GB free
disk space. Current SSH aliases are listed in `scripts/probe_a6000.ps1`.

## 1. Preflight

```powershell
./scripts/probe_a6000.ps1
```

Select the first host that reports an A6000 and sufficient resources. Before
any remote write, add a `RUNNING` DEVLOG record containing:

- experiment ID (`E0-anyv2v-smoke-v01` first);
- local Git commit and remote workspace path;
- exact 40-character AnyV2V and I2VGen-XL/Hugging Face revisions;
- DAVIS split/sample IDs, seed, 512x512, 16 frames, 8 fps;
- inversion/PnP steps (500/50), CFG 9, and PnP thresholds;
- expected runtime, VRAM, and unique artifact directory.

## 2. Bootstrap an exact checkout

Copy this repository to a versioned remote directory, then run:

```bash
bash scripts/bootstrap_anyv2v_remote.sh \
  /absolute/remote/workspace \
  <40-char-anyv2v-commit> \
  E0-anyv2v-smoke-v01
```

The script refuses an unpinned commit or an existing experiment directory.
The official environment uses Python 3.9, CUDA 11.8, and Diffusers 0.26.3.

## 3. Prepare and plan

Prepare DAVIS locally or remotely using the fixed manifest. Plan the real run
only with exact revisions:

```bash
uv run w1 prepare --davis-root /data/DAVIS --output-dir data/processed/w1
uv run w1 validate --prepared data/processed/w1/manifest.json
uv run w1 plan \
  --prepared data/processed/w1/manifest.json \
  --output artifacts/E0-anyv2v-smoke-v01/plan.json \
  --backend anyv2v \
  --model-commit <40-char-model-revision> \
  --anyv2v-commit <40-char-anyv2v-commit> \
  --seed 101
```

For the smoke test, reduce the generated plan to one candidate without editing
its contents. Keep the full plan for `E0-anyv2v-w1-v01` in a separate directory.

## 4. Smoke and reproducibility gate

Run the single candidate twice in independent experiment/cache directories:

```bash
uv run w1 run --backend anyv2v --plan <smoke-plan> \
  --experiment-dir <smoke-run-a> --cache <smoke-run-a>/cache.sqlite3 \
  --anyv2v-root <AnyV2V-root> --python-executable <conda-python>
uv run w1 run --backend anyv2v --plan <smoke-plan> \
  --experiment-dir <smoke-run-b> --cache <smoke-run-b>/cache.sqlite3 \
  --anyv2v-root <AnyV2V-root> --python-executable <conda-python>
uv run w1 verify --expected 1 --candidates <smoke-run-a>/candidates.json \
  --compare <smoke-run-b>/candidates.json
```

Proceed only if both media checks and the 16-frame checksum comparison pass.
If official CUDA kernels remain nondeterministic, record the mismatch and do
not silently weaken the gate.

## 5. Batch and closeout

Run the full plan in the unique `E0-anyv2v-w1-v01` directory. Resume with the
same cache after isolated failures. Completion requires `w1 verify` to report
50/50. Then run reward mock/replay and report generation; these reward values
remain interface tests, not research measurements.

Immediately append the final DEVLOG entry with status, runtime, peak VRAM,
50/50 result, cache hits, exact paths, and observed failures.

