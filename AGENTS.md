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

## Current E1 v2 repair authorization

1. On 2026-08-28, the user explicitly authorized Codex to modify the local code, tests, documentation, and `DEVLOG.md` needed to repair the confirmed E1 source-video checksum identity defect.
2. After the repair passes the required local verification, Codex is authorized to create a new audited baseline commit and push it to `main` without force-pushing.
3. This authorization is scoped to the confirmed E1 v2 repair and its reproducibility records. It does not authorize rewriting server history, modifying sealed deliveries, changing E0 inputs, or patching the school-server worktree in place.

## Current E1 v2 follow-up local engineering authorization

1. On 2026-08-29, the user explicitly authorized Codex to perform the local CPU-only code development, tests, documentation, and `DEVLOG.md` preparation needed for the subsequent E1 stages.
2. This authorization does not permit creating or pushing a Git commit without renewed explicit user confirmation.
3. This authorization does not permit changing the fixed research protocol or operating the school server, including connecting to it, running a real model, or creating server experiment directories.

## Current E1 publication and local E2 CPU engineering authorization

1. On 2026-08-29, the user explicitly authorized Codex to create audited commits for the completed local E1 P0/P1 work and to push them to `main` without force-pushing.
2. The user also authorized staged local CPU-only development, tests, documentation, DEVLOG records, audited commits, and ordinary pushes to `main` for the E2 Best-of-N engineering framework approved in the implementation plan.
3. Local E2 work may use only tiny fixtures, mock/replay data, fake command adapters, static checks, CPU tests, and locally generated reports. It must not create or claim real E2 research measurements before a valid E1 `PASS_PROVISIONAL` and `reward-v0.yaml` exist.
4. Codex must not connect to or operate the school server, read or write DATA4, load a real judge or video model, launch GPU work, or create remote experiment roots. All DATA4 preparation, Linux-site checks, real candidate generation, real judge inference, formal server-hosted annotation data, and GPU work are delegated through an audited runbook to the server-side agent.
5. E2 work must not enter E3/DPO, alter sealed E0 outputs, overwrite any remote experiment, or bypass the fixed E1 research gate.
