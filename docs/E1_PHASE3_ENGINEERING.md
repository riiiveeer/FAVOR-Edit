# E1 v2 phase 3 工程与恢复说明

本文只说明 phase 3 的本地/服务器工程身份、只读验收、partial-output 风险和恢复边界。
正式阶段顺序、GPU preflight、smoke、人工标注、freeze 和 final gate 仍以
[`E1_A6000_RUNBOOK.md`](E1_A6000_RUNBOOK.md) 为唯一执行入口。本文不授权操作服务器，
也不改变固定研究协议。

## 1. 输入、派生产物与放行关系

```text
E0 三文件 + 原始媒体 + masks + pilot/runtime template + MODEL_SHA256SUMS
                                │
                                ▼
                      e1 prepare-phase3
               （同文件系统唯一 staging root）
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
 runtime + pairs          media packets           550-request plan
                                │
                                ▼
                  prepublish verify-preparation
               （声明 final root → 实体 staging root）
                                │
          PASS + receipt + sorted tree checksum manifest
                                │
                                ▼
                    atomic no-replace rename
                                │
                                ▼
                         正式 $E1 root
                                │
           direct verify + sha256sum -c + 4-request smoke
```

Verifier 只读 pairs、manifest 及其全部文件引用、plan、config 和 runtime。除显式指定的
新 report 外不写任何输入；它不是构建器，也不是 GPU/model loader。`prepare-phase3` 是正式
runbook 的唯一创建入口；`build-pairs`、`build-packets` 和 plan builder 仍可用于本地开发，
但不得作为正式 phase 3 的手工替代链。

## 2. 固定计数

| 层级 | 总量 | dev | frozen-eval | 额外不变量 |
|---|---:|---:|---:|---|
| sample | 10 | 3 | 7 | 固定 DAVIS train sample |
| candidate asset | 50 | 15 | 35 | 每 sample 5 个 |
| canonical pair | 100 | 30 | 70 | 每 sample `C(5,2)=10` |
| absolute-v1 request | 50 | 15 | 35 | 每 candidate 一条 |
| pairwise-single-v1 request | 100 | 30 | 70 | 每 pair `a_vs_b` 一条 |
| pairwise-swap-v1 request | 200 | 60 | 140 | 每 pair 双方向 |
| rubric-swap-v1 request | 200 | 60 | 140 | 每 pair 双方向 |
| 全部 request | 550 | 165 | 385 | request_id/judge_key 均唯一 |

媒体层还必须精确为 60 个 asset × 16 frame = 960 个逐帧引用、60 张 contact sheet、
100 个 pair metadata 和 100 个 mask overlay。正式已审计 E0 预期 identical-media=0、
excluded pair=0。

## 3. 两种 source checksum 语义

- `InputRecord.source_checksum`：16 张 source frame 的组合身份；它不是 MP4 文件哈希。
- `InputRecord.video_checksum`：`source_video_path` 指向的 source MP4 文件 SHA-256。
- `PairRecordV2.source.video_sha256` 必须来自 `input.video_checksum`。

Verifier 不相信字段名本身：它会把 pair source SHA 与 manifest source
`original_sha256` 对齐，再读取 original MP4 重新计算 SHA。把 frame-set checksum 填入
`source.video_sha256` 会在 media identity gate 被拒绝。

## 4. 创建链的原子性审计

| 创建步骤 | 已有输出门 | 发布方式 | 中断后现场 | 原样重跑 |
|---|---|---|---|---|
| `prepare-phase3`（正式入口） | final、staging、failure 任一存在即拒绝 | 全部 staging 内验收后，使用同文件系统 atomic no-replace rename | 发布前失败转为具名 failed artifact；failure rename 不可用则保留原 staging | 同一 prepare ID 永久不可重试；恢复必须使用新 ID |
| runtime YAML：`cp` + Python `write_text`（旧手工链） | 无整体事务门 | `cp` 可覆盖，随后原地重写 | 可能留下 placeholder manifest 或半配置文件 | 有静默覆盖风险，禁止正式使用 |
| `build-pairs` | final output 存在即拒绝 | 先完成内存校验，再直接打开 final JSONL 写入 | 写盘中断可能留下 partial final 文件 | 因 final 已存在而拒绝；不得删除后重跑 |
| `build-packets` | output dir 存在即拒绝 | 先创建 final dir，再逐 asset/pair 写入 | 会留下可浏览但不完整的 assets/pairs/manifest 树 | 因目录已存在而拒绝；风险最高 |
| `build_judge_plan` | final output 存在即拒绝 | 全部请求验证后写 `.tmp`，再 replace final | final 通常 ABSENT，可能留临时文件 | final ABSENT 时可审计临时文件后决定；不得覆盖 final |
| `verify-preparation --output` | report 存在即拒绝 | 同目录完整临时文件，原子无覆盖发布 | 发布成功即完整 passed/failed JSON；发布前异常可能仅有隐藏 temp | 已有 report 一律拒绝 |

底层 builders 的 partial 风险没有消失，而是被 wrapper 隔离在 staging/failure artifact 中。
单条 builder 返回 0 不能代表 phase 3 DONE；只有 wrapper 退出 0、正式 root 原子发布、prepublish
report PASS、tree checksum 复算通过且 final root direct verifier 再次通过，才允许放行 smoke。

## 5. partial output 与恢复规则

1. Wrapper 开始前，final、staging、failure 三者必须均为 ABSENT；任一存在都立即停止，不接管、
   不覆盖已有现场。
2. 任一内部步骤失败或中断，立即停止后续命令，记录时间、命令、exit code、stderr、Git
   snapshot、E0/input SHA、现有文件树和磁盘/inode。
3. 失败现场固定为 `<target>.prepare-<prepare-id>.failed` 并包含
   `PREPARATION_FAILED.json`；若 failure rename 能力不可用，原
   `.<target>.prepare-<prepare-id>.staging` 保持原位，stderr 必须报告准确路径。
4. 同一 prepare ID 不可重试。恢复时选用新的 prepare ID，同时永久保留旧 failed/staging
   artifact 供审计。
5. 不删除、不覆盖、不手工补齐 partial 文件；不重新生成 checksum 来掩盖损坏。
6. 不把存在 `media-manifest.json`、行数看似正确或目录可打开当作 DONE。
7. Verifier failed 时保留唯一 failed report 并计算其 SHA-256；禁止进入 smoke。
8. 若问题需要改 prompt、threshold、generation、model、split、方法或 gate，它不是恢复，必须
   停止并向用户提交证据和新实验身份方案。

## 6. preparation verification report schema

顶层至少包含：

- `report_schema_version`、`status`、`generated_at`、`ready_for_smoke`；
- `inputs`：pairs、media manifest、plan、config、runtime 的绝对路径和 SHA-256；
- `counts`、`method_counts`、`split_counts`、`method_split_counts`；
- `runtime`、`model_identity`、`prompt_checksums`、`code_snapshot`；
- `checks`：每个硬检查的 `check_id/status/summary` 和必要明细；
- `verification_context`：`prepublish-staging` 或 `direct`、声明的 final root，以及实体映射说明；
- `warnings`：例如经过现场 Git 核对的 DEVLOG-only `+dirty`；
- `failures`：失败 check 和精确错误；任何非空值均强制 `ready_for_smoke=false`。

Prepublish verifier 通过“声明 final root → 实体 staging root”的只读映射访问文件：manifest、
packet metadata、plan 和 report 中保存 final 路径，文件读取与 SHA 复算访问 staging。正式发布后，
这些身份无需二次改写，direct verifier 可直接复验；report 本身不得泄漏 staging 绝对前缀。

Development plan 的 `code_snapshot` 必须是 40 位 commit，可选 `+dirty`。`+dirty` 只有当
现场 `git status --porcelain` 的 dirty 路径精确为 `DEVLOG.md` 时才允许，并在 report 中产生
显式 warning；unknown、混合 snapshot 或其他 dirty 文件均失败。Freeze 前仍必须按 runbook
恢复为干净仓库，P0 的这个 development 例外不能外推到 freeze。

## 7. 磁盘、inode 与只读边界

GPU 和磁盘状态都具有时效性。phase 3 创建前、preparation verifier 前、smoke 前分别执行：

```bash
df -h /DATA/DATA4/hfy
df -i /DATA/DATA4/hfy
nvidia-smi
```

不得清理他人数据/缓存，不得 kill 他人进程、reset GPU 或启动占位囤卡进程。磁盘/inode
不足不是覆盖旧实验或跳过媒体验收的理由。Verifier 是 CPU/read-only 文件验收，不能把其
PASS 解读为 GPU 可用、模型成功加载、VRAM gate 通过或真实 judge 已运行。

## 8. DEVLOG 模板

### PLAN

```text
状态：PLANNED
时间/环境：<ISO>，school server，CPU-only phase-3 preparation
步骤 ID：<唯一 ID>
代码：<40位 commit；git status>
输入：E0 三文件路径+SHA；config/runtime/prompt/model manifest identity
命令：完整 prepare-phase3 命令（含 prepare ID 与 MODEL_SHA256SUMS 路径）
预期产物：唯一绝对路径；逐项 ABSENT 结果
资源：预计磁盘、inode、运行时间；不加载模型
下一步：仅 verifier PASS 后允许 smoke
```

### COMPLETE

```text
状态：DONE
完成时间/环境：<ISO>，school server，CPU-only
结果：pairs/assets/frames/masks/requests 精确计数；全部 checks passed
产物：final root、pairs/manifest/plan/report/receipt/PREPARATION_SHA256SUMS 路径+SHA
Git：code_snapshot；DEVLOG-only dirty warning（如有）
磁盘/inode：前后现场值
下一步：按 runbook 写 smoke GPU job 前置 DEVLOG
```

### FAILED / INTERRUPTED

```text
状态：FAILED / INTERRUPTED
时间/环境：<ISO>，school server
失败命令：完整命令、exit code、stderr/异常
诊断：failed check；partial 文件/目录；report 路径+SHA（若已发布）
身份：Git/E0/config/runtime/prompt/model manifest SHA
现场：磁盘/inode；未删除/未覆盖确认
下一步：STOP；保留 failed/staging 现场并使用新 prepare ID 提出恢复，不进入 smoke
```

## 9. P1 atomic preparation wrapper 实现状态与不变量

P1 已在本地工程实现并通过 tiny/mock CPU 验收；正式入口为 `e1 prepare-phase3`：

1. 正式 `$E1` 在发布前必须 ABSENT；wrapper 不接受已有 root。
2. 在与正式 root 同一文件系统创建唯一 staging root，runtime、pairs、packets、plan 和
   verification report 全部只写 staging。
3. staging 内运行同一个 `verify-preparation`；只有完整 PASS 才可发布。
4. 发布使用单次同文件系统原子 rename；目标出现的竞争条件必须失败，不能 replace。
5. failed staging 原样保留并改为明确的 failure artifact 身份，记录 SHA/DEVLOG；不得冒充正式根。
6. wrapper 固化完整 config、command、code snapshot 和输入 SHA，并验证自己未修改 E0。
7. runtime 创建也必须采用模板读取、内存校验、原子无覆盖写，不再使用可覆盖的 `cp` + 原地改写。
8. 单 writer；所有异常都返回非零；不得自动删除 staging、final 或 failed artifact。
9. 发布前将内部媒体路径重基为 final root，重建 100 个 packet metadata/checksum，再生成 550
   条 plan 和 judge key；E0 original media 路径保持不变。
10. Wrapper 在启动前、发布前、发布后复算 E0 三文件及全部外部 source/candidate/mask SHA；
    任一漂移都失败。
11. `phase3-preparation-v01.json` 固化输入、模型、代码、runtime/prompt、计数和产物身份；
    `PREPARATION_SHA256SUMS` 覆盖除清单自身外的所有常规文件与 symlink 内容并按 POSIX 相对路径排序。
12. Linux 发布仅接受 `renameat2(RENAME_NOREPLACE)`；Windows 使用拒绝既有目标的原子 rename；
    能力不可用即失败关闭，不降级为 replace。

本地实现完成不等于学校服务器已获得该代码。服务器执行前仍须按交付流程使用已审计代码快照，
并在服务器 CPU-only preflight 验证 `renameat2(RENAME_NOREPLACE)` 能力；本次本地工作不连接服务器。
