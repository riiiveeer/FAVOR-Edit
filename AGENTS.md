# Workspace Development Rules

These rules apply to all development work in this workspace, including work performed by Codex.

## DEVLOG is mandatory

1. After every completed, independently verifiable development step, immediately append a record to `DEVLOG.md` before starting the next step.
2. A development step includes, but is not limited to:
   - changing code, configuration, prompts, data-processing logic, or experiment scripts;
   - setting up or changing an environment or dependency;
   - downloading or preparing a model or dataset;
   - running a test, inference job, training job, evaluation, or analysis;
   - making a technical decision that changes the implementation or experiment protocol.
3. Each record must state at least: date/time, local or remote environment, step/experiment ID, action taken, command or key configuration, result, artifact path, and next step.
4. Failed or interrupted runs must also be recorded when they produce diagnostic information or affect the next decision.
5. Do not batch several completed steps into a vague retrospective entry. Record each step when it completes.
6. Do not claim a development step is complete unless its DEVLOG entry has been written.
7. Pure discussion that does not change files, environments, data, experiments, or technical decisions does not require a DEVLOG entry.

## Local and remote execution

1. Default to local development for documentation, code editing, static checks, unit tests with mocks or tiny fixtures, data manifests, result parsing, plotting, and report generation.
2. Use the school A6000 for full model loading/inference, batch video generation, GPU-heavy feature extraction or video metrics, locally hosted MLLM/VLM judging, LoRA/DPO training, and full benchmark evaluation.
3. Before launching an A6000 job, record the planned experiment ID, repository commit or code snapshot, model/checkpoint, dataset split, command/configuration, expected outputs, and resource estimate in `DEVLOG.md`.
4. After the job ends or is interrupted, record status, runtime, peak VRAM if available, metrics, output paths, and observed failures before starting the next experiment.
5. Never overwrite a remote experiment output directory. Use a unique experiment ID and preserve the exact configuration with the outputs.

