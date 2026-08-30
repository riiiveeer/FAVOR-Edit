# E2 Best-of-N 服务器端 Agent 执行手册

## 1. 权限边界

本手册只交付给学校服务器端 agent 执行。当前本地 agent 不得连接学校服务器，不得读取或写入 DATA4，不得加载真实 Judge/视频模型，也不得创建下列正式目录。

服务器端 agent 仅可在收到本地已发布的精确实现 commit SHA、验收摘要和本手册后施工。禁止根据浮动 `main` 直接运行；先 fetch，再 checkout 用户交付的精确 commit，并记录 `git rev-parse HEAD`。禁止 force-push、禁止在服务器 worktree 就地打补丁。

正式固定目录：

- `/DATA/DATA4/hfy/outputs/E2-anyv2v-extension-v01`
- `/DATA/DATA4/hfy/outputs/E2-visual-audit-v01`
- `/DATA/DATA4/hfy/outputs/E2-bon-pilot-v01`

三个目录在首次写入前必须全部 **ABSENT**。任一目录、对应 staging 路径或 failed 路径已存在时立即停止，不删除、不移动、不覆盖，由用户决定新的实验 ID。

## 2. 正式 E2 gate

在创建任何正式 E2 根之前，服务器端 agent 必须只读确认：

1. E1 `decision.json` 的 `decision` 为 `PASS_PROVISIONAL`，四项 gate 完整且全部为 true；
2. 同一 E1 frozen delivery 中存在 `reward-v0.yaml`、`protocol.lock.json`、`pilot-frozen.yaml`、`runtime-frozen.yaml` 和 frozen prompts；
3. `reward-v0`、frozen protocol、runtime/model/prompt fingerprints 与本地交付代码的 `e2 prepare` 校验一致；
4. 若 E1 selected method 不是 `rubric-swap-v1`，线性/Pareto 暂时为 `NOT_APPLICABLE`。只有在额外 frozen rubric 结果通过 `e2 qualify-rubric` 四项门并产生独立 `auxiliary-rubric-v0.json` 后，才可创建 E2 auxiliary rubric 计划；
5. E1 gate 未满足时，只回传阻塞证据。不得创建正式 E2 根，不得生成正式候选，不得声称研究结论，也不得进入 E3/DPO。

## 3. Linux no-replace 与存储 preflight

将以下检查及完整输出写入服务器执行日志：

```bash
set -euo pipefail
git rev-parse HEAD
git status --short --branch
df -h /DATA/DATA4
test ! -e /DATA/DATA4/hfy/outputs/E2-anyv2v-extension-v01
test ! -e /DATA/DATA4/hfy/outputs/E2-visual-audit-v01
test ! -e /DATA/DATA4/hfy/outputs/E2-bon-pilot-v01
uv run pytest
uv run e2 validate
uv run e2 --help
```

随后在与目标目录相同的 DATA4 文件系统中，用临时、唯一、窄范围目录验证 Linux `renameat2(RENAME_NOREPLACE)`。测试目录必须由 `mktemp -d` 创建；记录成功后只清理该临时目录。若 no-replace 不可用，停止正式 preparation，不得用可覆盖的 `mv` 替代。

## 4. 30 个新增候选

服务器端 agent 应先解析并记录既有 E0 plan/candidates/audit 的精确路径与 SHA256，不猜测路径。执行：

```bash
uv run e2 plan-generation \
  --e0-plan "$E0_PLAN" \
  --config configs/e2/pilot.yaml \
  --snapshot "$AUDITED_COMMIT" \
  --output "$EXTENSION_ROOT/generation-plan-v01.json"
```

确认计划恰好10 inversion、30 candidate，seed 仅为 `606/707/808`，且除 seed、运行时、产物路径和 code snapshot 外，AnyV2V commit、model revision、分辨率、帧数与全部生成参数和 E0 完全一致。然后由服务器端 GPU agent 使用 W1/AnyV2V 既有 audited runner 生成30项，写入唯一 extension root；记录命令、runtime、peak VRAM、每项状态和 checksum。失败现场永久保留，不复用同一路径重跑。

## 5. 扩展候选人工粗审与80候选池

在独立 visual-audit root 中生成30项 blind visual audit 表。人工逐项填写固定 `usable_for_e2`/拒绝状态，不得由 agent 臆造。全部30项通过后执行：

```bash
uv run e2 build-pool \
  --e0-plan "$E0_PLAN" \
  --e0-candidates "$E0_CANDIDATES" \
  --e0-audit "$E0_AUDIT" \
  --extension-plan "$EXTENSION_ROOT/generation-plan-v01.json" \
  --extension-candidates "$EXTENSION_ROOT/candidates.json" \
  --extension-audit "$VISUAL_AUDIT_ROOT/extension-audit.csv" \
  --config configs/e2/pilot.yaml \
  --output "$VISUAL_AUDIT_ROOT/candidate-pool-v01.json"
```

必须得到10 sample、80 candidate、每 sample 恰好8 seed，且视频与16帧 checksum 全部通过。

## 6. 原子 preparation 与真实 Judge

仅在第2节 gate 和第5节 pool 都通过后执行 `e2 prepare`。`E2-bon-pilot-v01` final/staging/failed 均必须预先 ABSENT：

```bash
uv run e2 prepare \
  --pool "$VISUAL_AUDIT_ROOT/candidate-pool-v01.json" \
  --config configs/e2/pilot.yaml \
  --e1-decision "$E1_DECISION" \
  --reward-v0 "$E1_REWARD" \
  --frozen-config "$E1_FROZEN_CONFIG" \
  --frozen-protocol "$E1_FROZEN_PROTOCOL" \
  --runtime "$E1_FROZEN_RUNTIME" \
  --output-root /DATA/DATA4/hfy/outputs/E2-bon-pilot-v01 \
  --prepare-id "$UNIQUE_PREPARE_ID"
```

若已存在 qualified auxiliary rubric artifact，附加 `--auxiliary-rubric`。成功后先验证 `PREPARATION_SHA256SUMS`、280 pair、80 trial、560 primary request，以及可选560 rubric request。

真实 Judge 仅由服务器端 GPU agent 执行，primary 与 auxiliary 使用独立 run/cache 路径：

```bash
uv run e2 run --plan "$PILOT_ROOT/plans/judge-plan-primary.jsonl" --runtime "$PILOT_ROOT/runtime-frozen.yaml" --experiment-dir "$PILOT_ROOT/runs/primary" --cache "$PILOT_ROOT/runs/primary-cache.sqlite3"
```

如有 auxiliary plan，再运行一次独立 auxiliary experiment/cache。`.e2-run.lock` 只可在确认原进程已结束并记录理由后通过 `e2 unlock` 清除。

## 7. 选择、正式双人盲标与第三人裁决

执行 `e2 select --measurement-mode formal-command`。pairwise primary 没有 qualified rubric 时不得提供 rubric 参数，线性/Pareto 必须保持 `NOT_APPLICABLE`。有合法 auxiliary 时同时提供 `--rubric-results` 与 `--auxiliary-rubric`。

两名不同主标注者分别运行 `e2 annotate`，完整标注所有非 `identical_selection` 项。正式 annotation 文件保存在 pilot root 的 `human/`，不得覆盖。相同 checksum 项自动 tie，不启动人工 UI但保留在80项计划中。

首次 `e2 adjudicate` 若报告 `needs_third_annotator`，将该 no-replace preliminary report 保留。第三位不同标注者以该 report 的 disputed comparison filter 运行 `e2 annotate`，完整覆盖所有且仅争议项；使用新的 final adjudication report 路径再次执行 adjudication。

## 8. 分析、报告、验证与回传

依次运行：

1. `e2 analyze`：输入 config、selection、80项 adjudicated、agreement report、candidate pool、primary results 和可选 rubric results；
2. `e2 report`：从 analysis 目录生成 Markdown/SVG/CSV；
3. `e2 verify`：输入 preparation、selection、adjudicated、analysis、report、Judge results、reward 和可选 rubric/auxiliary artifact。

只有 `verification.status=passed` 且 `ready_for_research_interpretation=true` 时，才可把正式指标标为研究测量。`meets_m1_target=true` 只表示 point estimate 达到0.60，不自动表示统计显著；任何 `significant_faithfulness_degradation` 或 `significant_preservation_degradation` 必须在回传摘要中单列。

回传给本地的最小审计包：精确 Git SHA、全部命令日志、环境/模型 manifest、E1依赖 SHA、extension plan/candidate records/audit、candidate pool、preparation receipt/report/SHA256SUMS、primary/auxiliary result与runner summary、selection、两位主标注与第三人文件、adjudicated/agreement、analysis、report、final verification，以及每个正式根的全树 checksum 清单。不得回传模型 checkpoint 或生成视频进 Git。
