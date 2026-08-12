# DEVLOG

> 项目：面向忠实—保持冲突的鲁棒成对偏好视频编辑优化  
> 起始日期：2026-08-12  
> 用途：记录实际进度、环境、命令、实验、失败、决定和下一步。正式方案见 `proposal.md`。

---

## 使用规则

1. 每次工作开始时新增一条记录，不覆盖历史内容。
2. **每完成一个独立、可验证的开发步骤，必须立即追加一条记录，写完后才能开始下一步。未写入本日志的步骤不得标记或宣称为完成。**
3. 记录“实际发生了什么”，不要把计划当成结果。
4. 所有实验使用唯一 ID，例如 `E1-judge-pairwise-v01`。
5. 每次记录至少包含：日期时间、本地或远程环境、目标、改动、命令/配置、结果、结论、产物路径、问题、下一步。
6. 指标必须注明数据划分、样本数、模型版本和随机种子。
7. 失败或中断的实验只要产生诊断信息或影响后续决策，也必须记录。
8. checkpoint、生成视频和表格只写可定位路径，不把大文件直接放入本日志。

推荐状态：`TODO`、`RUNNING`、`DONE`、`BLOCKED`、`INVALID`。

---

## 项目里程碑

| 里程碑 | 截止日期 | 交付物 | 状态 |
| --- | --- | --- | --- |
| M1：课程答辩基本成果 | 2026-09-01 | reward 初步校准、Best-of-N 主表与曲线、案例、slides 初稿 | TODO |
| M1+：答辩增强版 | 2026-09-08 | 类别分析、统计检验、小规模 DPO sanity check | TODO |
| M2：八周完整成品 | 2026-10-06 | 训练、hacking、完整评测、代码、报告、slides、演示 | TODO |

---

## 当前关键决策

| 日期 | 决策 | 原因 | 后续影响 |
| --- | --- | --- | --- |
| 2026-08-12 | 不再使用“首个视频编辑偏好对齐”的表述 | VIVA 已在 CVPR 2026 使用 Edit-GRPO 优化指令视频编辑 | 创新聚焦 reward 可靠性、冲突建模和 hacking |
| 2026-08-12 | 课程答辩不依赖 DPO 完成 | 3–4 周窗口内，judge 校准和 Best-of-N 更低风险 | W1–W3 优先完成 E0–E2 |
| 2026-08-12 | IVEBench 仅作最终独立测试 | 避免训练/测试输入泄漏 | 训练与开发另建数据池 |
| 2026-08-12 | AnyV2V 默认只作推理/BoN baseline | 免训练流水线不适合作为直接 DPO 主干 | 另选一个可训练编辑模型 |
| 2026-08-12 | Reward 通过人工校准后才生成训练 pair | 防止错误 judge 被训练放大 | E1 是进入 E3 的决策门 |
| 2026-08-12 | 本地开发、A6000 执行真实模型与批量计算 | 降低远程调试成本并集中使用 GPU 资源 | 本地先 mock/smoke；远程作业前后均记录 |
| 2026-08-12 | 每完成一个可验证开发步骤立即更新 DEVLOG | 保证开发和实验全过程可追溯 | 未记录不得宣称完成 |

---

## 实验索引

| 实验 ID | 日期 | 目的 | 数据/模型 | 状态 | 主要结果 | 产物路径 |
| --- | --- | --- | --- | --- | --- | --- |
| E0-pipeline-v01 | — | 跑通生成、缓存和评测 | 待定 | TODO | — | — |
| E1-judge-v01 | — | 比较绝对与成对 judge | 待定 | TODO | — | — |
| E2-bon-v01 | — | 测试 N=1/2/4/8 | 待定 | TODO | — | — |
| E3-dpo-sanity-v01 | — | 检查偏好损失和梯度方向 | 待定 | TODO | — | — |
| E4-hacking-v01 | — | 忠实—保持压力测试 | 待定 | TODO | — | — |
| E5-final-v01 | — | 独立最终评测 | IVEBench | TODO | — | — |

---

## 每日记录

### 2026-08-12｜学校服务器离线交付手册与辅助工具验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 12:14:24 +08:00
- 执行位置：本地 Windows；文档和静态/单元验证

**实验 ID**

- `W1-school-delivery-doc-v02`

**行动与关键配置**

- 将服务器流程改为完全离线优先：Git bundle、Linux conda-pack、两个本地模型 snapshot、十条 DAVIS 数据和全包 SHA-256 随交付包上传。
- 明确 Windows prepared manifest 不能复用，必须在 Linux 服务器重新 `w1 prepare`。
- 增加国内 PyPI/Anaconda 镜像作为环境包不可用时的备选，不允许运行时从 GitHub/Hugging Face 拉取代码或权重。
- 增加离线模型软链接、`HF_HUB_OFFLINE`、双 smoke、逐帧复现门、50 候选批量、验收、故障处理和结果回传步骤。
- 将 smoke-plan 核心逻辑移入 `w1_pipeline.delivery`，脚本保留薄入口；增加 preflight 和手册关键约束测试。
- 命令：`uv run pytest`、`uv run python scripts/make_smoke_plan.py --help`、`uv run w1 validate`、`git diff --check`。

**结果**

- 18 个测试全部通过；smoke-plan CLI 和 W1 manifest 校验正常；diff 无空白错误。
- 本机无可用 Linux bash，因此 `offline_preflight.sh` 的真实 bash 语法和运行仍需在学校 Linux 服务器首次执行时验证并记录。

**产物路径**

- `docs/SCHOOL_SERVER_DELIVERY.md`
- `src/w1_pipeline/delivery.py`
- `scripts/make_smoke_plan.py`
- `scripts/offline_preflight.sh`
- `tests/test_delivery_helpers.py`

**下一步**

1. 创建本次文档与工具的 Git 快照。
2. 按手册在联网 Linux 机器制作模型/环境交付包；学校连接恢复后执行离线 preflight 和真实 smoke。

### 2026-08-12｜学校服务器离线交付手册首次回归

**状态：INVALID（产生有效诊断）**

**时间与环境**

- 完成时间：2026-08-12 12:12:55 +08:00
- 执行位置：本地 Windows；未使用远程 A6000

**实验 ID**

- `W1-school-delivery-doc-v01`

**行动与关键配置**

- 新增离线交付目录规范、联网侧资源打包、模型 snapshot、Linux 环境包、DAVIS 数据、服务器离线部署、双 smoke、50 候选、验收和结果回传手册。
- 新增单候选 smoke plan 生成器和服务器离线 preflight 脚本。
- 执行 `uv run pytest`、脚本 `--help`、`git diff --check` 和本机 bash 探测。

**结果**

- smoke plan CLI 的 `--help` 正常，diff 无空白错误。
- pytest 收集失败：`scripts` 未声明为 Python 包，测试无法导入 `scripts.make_smoke_plan`。
- 本机 `bash` 是未安装 WSL 的 Windows 占位程序，其输出不能作为有效 bash 语法验证证据。

**产物路径**

- `docs/SCHOOL_SERVER_DELIVERY.md`
- `scripts/make_smoke_plan.py`
- `scripts/offline_preflight.sh`

**下一步**

1. 增加 `scripts/__init__.py` 并重跑完整测试。
2. 增加对离线 preflight 关键检查项的静态回归测试；真实 bash 语法需在 Linux/学校服务器执行。

### 2026-08-12｜远程 Runbook 与最终本地回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:58:00 +08:00
- 执行位置：本地

**实验 ID**

- `W1-local-final-regression-v01`

**行动与关键配置**

- 新增 A6000 preflight、精确 commit bootstrap、单候选双重复 smoke、复现门、50 候选批量运行和结束记录的完整 runbook。
- 更新 README 的全部 CLI 示例和远程文档入口。
- 执行 `uv run pytest`、`uv run w1 validate`、`git diff --check`。

**结果**

- 15 个测试全部通过；固定 manifest 校验为 10 inputs / 5 seeds；Git diff 无空白错误。
- 本地 W1 框架、mock/replay、媒体与复现验收完成；真实 AnyV2V GPU 验证仍受 SSH reset 阻塞。

**产物路径**

- `docs/REMOTE_RUNBOOK.md`
- `README.md`
- 本地 mock 交付：`artifacts/E0-pipeline-mock-v01/`

**下一步**

1. 创建最终代码快照。
2. A6000 恢复后按 runbook 先执行 `E0-anyv2v-smoke-v01`，通过后运行 `E0-anyv2v-w1-v01`。

### 2026-08-12｜A6000 连通性复查

**状态：BLOCKED（外部连接状态）**

**时间与环境**

- 完成时间：2026-08-12 11:56:44 +08:00
- 执行位置：本地到学校远程入口；只读探测

**实验 ID**

- `E0-a6000-preflight-v01`

**行动与关键配置**

- 执行 `scripts/probe_a6000.ps1`，依次探测三个现有 SSH alias。
- 探测内容原计划为 hostname、GPU 型号/显存、Python 和磁盘；未进行任何远程写入。

**结果**

- `202.120.62.181-hfy-24100`、`202.120.62.181-sunyinan-24097`、`202.120.62.181-hfy-24095` 均在 SSH 密钥交换阶段被远端 reset。
- 无法读取 GPU、Python 或磁盘状态；未启动远程环境安装、模型下载、smoke 或批量推理。

**产物路径**

- 探测脚本：`scripts/probe_a6000.ps1`
- 无远程产物。

**问题 / 失败**

- 需要恢复校园网/VPN、端口映射或远程实例状态。
- 在连通恢复前，W1 的 50 个真实 AnyV2V 候选仍未完成；当前仅有 50 个 mock 接口验收结果。

**下一步**

1. 连接恢复后重新运行 preflight，确认 A6000 与至少 100GB 空闲磁盘。
2. 在 DEVLOG 写入确切 AnyV2V/model commit 和资源估计后，先跑单候选双重复 smoke，再提交 `E0-anyv2v-w1-v01`。

### 2026-08-12｜Mock 逐帧复现性验证

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:56:00 +08:00
- 执行位置：本地；CPU；独立输出目录和 SQLite 缓存

**实验 ID**

- `E0-pipeline-mock-v01-repeat`

**行动与关键配置**

- 使用同一 `plan.json` 在全新 `artifacts/E0-pipeline-mock-v01-repeat` 中重新生成 50 个候选。
- 执行 `w1 verify --compare`，按 candidate ID 比较两次运行的 16 张逐帧 SHA-256。

**结果**

- 第二次运行 50/50 成功、0 cache hit。
- 校验结果 `valid: true`、`reproducible: true`，所有逐帧校验和一致。

**产物路径**

- `artifacts/E0-pipeline-mock-v01-repeat/candidates.json`
- `artifacts/E0-pipeline-mock-v01-repeat/cache.sqlite3`

**下一步**

1. 只读探测现有 A6000 SSH 入口。
2. 更新远程运行文档和最终代码快照；真实 smoke 等连接恢复后执行。

### 2026-08-12｜Mock E2E 50/50 媒体验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:55:06 +08:00
- 执行位置：本地；CPU；合成数据

**实验 ID**

- `E0-pipeline-mock-v01-acceptance`

**行动与关键配置**

- 修复 verify CLI 的 JSON 导入并增加命令级回归测试。
- 执行 `uv run pytest`、`w1 verify --expected 50` 和 `w1 report`。

**结果**

- 15 个测试全部通过。
- verifier 报告 `valid: true`、`count: 50`、`errors: {}`；全部候选满足文件、校验和、16 帧、512×512 和 8 fps 要求。
- 生成完整 mock 报告和 pipeline Mermaid/SVG；报告明确 mock/replay 不属于研究测量。

**产物路径**

- `artifacts/E0-pipeline-mock-v01/candidates.json`
- `artifacts/E0-pipeline-mock-v01/rewards.json`
- `artifacts/E0-pipeline-mock-v01/report/W1_REPORT.md`
- `artifacts/E0-pipeline-mock-v01/report/pipeline.mmd`
- `artifacts/E0-pipeline-mock-v01/report/pipeline.svg`

**下一步**

1. 以相同 plan 在独立输出/缓存中重新生成 50 条 mock 候选，逐帧比较复现性。
2. 执行 A6000 只读探测，并记录真实 smoke 阻塞状态。

### 2026-08-12｜Mock E2E 失败项恢复与 Verify 二次诊断

**状态：INVALID（候选已补齐，CLI 输出仍需修复）**

**时间与环境**

- 完成时间：2026-08-12 11:53:56 +08:00
- 执行位置：本地；CPU

**实验 ID**

- `E0-pipeline-mock-v01-retry01`

**行动与关键配置**

- 查明两个失败项均为 Windows 临时目录发布时的短暂 `WinError 5`，为目录原子替换增加有界退避重试。
- 将 verifier 从 `list(reader)` 改为最多解码 17 帧的流式计数，避免内存耗尽。
- 重跑全部测试与 run/reward/verify/report；cache 跳过已有成功项。

**结果**

- 14 个测试通过；候选达到 50/50，其中 48 个 generation cache hit；reward 50 条，其中 48 个 cache hit。
- 流式媒体校验完成，但 CLI 输出阶段因 `cli.py` 漏导入 `json` 触发 `NameError`，因此本次验收命令仍为失败状态。

**产物路径**

- `artifacts/E0-pipeline-mock-v01/`
- 修复文件：`src/w1_pipeline/backends.py`、`verification.py`

**下一步**

1. 补充 `json` 导入并增加 CLI verifier 回归测试。
2. 重新执行 verify/report，并进行第二份独立 mock run 的逐帧复现比较。

### 2026-08-12｜完整 CLI Mock E2E 首次运行

**状态：INVALID（产生有效诊断，待修复后重跑）**

**时间与环境**

- 完成时间：2026-08-12 11:52:18 +08:00
- 执行位置：本地；CPU；合成 10 输入数据

**实验 ID**

- `E0-pipeline-mock-v01`

**行动与关键配置**

- 生成 10 条合成 prepared 输入，依次执行 `w1 plan`、`run --backend mock`、`reward --backend mock`、`verify` 和 `report`。
- 固定 5 seeds，共计划 10 inversions / 50 candidates。

**结果**

- plan 正确生成 10/50；run 仅成功 48/50；reward 对 48 个成功项生成 48 条非研究 mock 记录。
- `verify` 在 `decoded = list(reader)` 处触发 `MemoryError`，ffmpeg 被终止；该实现不能用于批量验证。
- report 虽生成，但基于不完整候选，因此不能作为合格交付物。

**产物路径**

- 诊断产物：`artifacts/E0-pipeline-mock-v01/`

**问题 / 失败**

- 需检查两个失败 candidate 的缓存错误。
- verifier 必须改为逐帧流式检查，避免同时保留全部解码数组。

**下一步**

1. 读取 SQLite/candidates 中的失败原因。
2. 修复 mock 后端或媒体编码问题以及流式 verifier，然后仅重试失败项并重新验收。

### 2026-08-12｜W1 初始代码快照

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:50:56 +08:00
- 执行位置：本地 Git 仓库

**实验 ID**

- `W1-code-snapshot-v01`

**行动与关键配置**

- 执行 `git diff --check`、`git add .` 和 `git commit -m "Implement W1 reproducible video editing pipeline"`。
- 将文档、环境锁、源码、配置、脚本和测试纳入同一可追溯初始快照。

**结果**

- 创建 root commit `bb671dd`，27 个文件、3311 行。
- 后续生成计划可记录实际 Git commit，而不是 `unversioned`。

**产物路径**

- Git commit：`bb671dd`

**下一步**

1. 使用该代码快照运行完整 CLI mock E2E。
2. mock E2E 完成后立即记录产物、数量、耗时和验证结果。

### 2026-08-12｜Reward Mock/Replay、Verify 与报告接口

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:50:18 +08:00
- 执行位置：本地；CPU

**实验 ID**

- `W1-reward-verify-report-v01`

**行动与关键配置**

- 实现 reward request/result 规范化 key、SQLite 缓存、确定性 mock 和严格 replay 后端。
- mock 结果强制标记 `research_result: false`、`confidence: 0`、`preference: uncertain`，避免误作实验结论。
- 实现 candidate 数量、唯一 ID、文件存在、SHA-256、16 帧、512×512、8 fps 和双清单逐帧复现校验。
- 实现 W1 Markdown 报告、代表案例/失败案例槽位、Mermaid 源图和无需外部工具的 SVG 图。
- 命令：`uv run pytest`、`uv run w1 --help`。

**结果**

- 14 个测试全部通过；CLI 暴露 `validate/prepare/plan/run/reward/verify/report` 全部计划命令。
- reward 方向进入 cache key，正反向比较不会错误共用缓存。

**产物路径**

- `src/w1_pipeline/rewards.py`、`verification.py`、`reporting.py`
- `tests/test_rewards_verify_report.py`

**下一步**

1. 用完整 10×5 合成 prepared 数据运行 CLI 级 mock E2E，生成可检查交付物。
2. 探测 A6000 并准备真实 smoke 的 DEVLOG 前置记录。

### 2026-08-12｜AnyV2V 两阶段远程适配与提交护栏

**状态：DONE（静态与单元测试；未执行真实 GPU 推理）**

**时间与环境**

- 完成时间：2026-08-12 11:48:03 +08:00
- 执行位置：本地；未连接学校 A6000

**实验 ID**

- `W1-anyv2v-adapter-v01`

**行动与关键配置**

- 完成官方 AnyV2V `run_group_ddim_inversion.py` 与 `run_group_pnp_edit.py` 的配置生成和调用适配。
- 每个 sample 在共享 staging 目录只生成一次 inversion；已有完整 latents 时复用，不完整目录拒绝覆盖。
- 每个 candidate 使用同一 seed 执行 InstructPix2Pix 首帧编辑和 PnP，规范化收集 1 个 MP4、16 张 PNG、校验和、运行时间和显存记录。
- 强制 AnyV2V checkout 与计划中的 40 位 commit 一致；新增远端 bootstrap 的 commit/唯一输出目录护栏和 A6000 探测脚本。
- 命令：`uv run pytest`。

**结果**

- 12 个测试全部通过；适配器固定 16 帧、512×512、8 fps、500/50 步和计划 seed。
- 因 SSH 入口尚未恢复，本步骤不声称真实 AnyV2V 端到端链路已验证。

**产物路径**

- `src/w1_pipeline/backends.py`
- `scripts/probe_a6000.ps1`、`scripts/bootstrap_anyv2v_remote.sh`
- `tests/test_anyv2v_adapter.py`

**下一步**

1. 实现 reward mock/replay、候选媒体 verify、汇总报告和流程图。
2. 运行完整本地 mock E2E，并在恢复 A6000 后执行真实 smoke。

### 2026-08-12｜候选规划、SQLite 缓存与 Mock 断点续跑

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:44:36 +08:00
- 执行位置：本地；CPU；合成 prepared manifest

**实验 ID**

- `E0-pipeline-mock-v01`

**行动与关键配置**

- 实现规范化 generation key、10 inversion / 50 candidate 规划器、代码快照标识。
- 实现 SQLite WAL 状态缓存、running/succeeded/failed 状态更新、原子 manifest 写入与成功项恢复。
- 实现 mock 后端，按 seed 生成确定性 16 帧、512×512、8 fps 视频，并明确标注 `research_result: false`。
- 增加 AnyV2V checkout commit 强制校验和首帧编辑适配骨架；真实 inversion/PnP 完整适配尚列为下一步。
- 命令：`uv run pytest tests/test_cache_and_runner.py tests/test_models_and_data.py`。

**结果**

- 10 个测试全部通过。
- 首次 mock run 调用后端 50 次并成功 50/50；第二次运行后端调用 0 次、缓存命中 50/50。
- 规范化哈希对字典字段顺序稳定，SQLite 读写验证通过。

**产物路径**

- `src/w1_pipeline/cache.py`、`planning.py`、`backends.py`、`runner.py`
- `tests/test_cache_and_runner.py`

**下一步**

1. 完成 AnyV2V inversion 只运行一次、每 seed 首帧与 PnP 配置生成及产物采集。
2. 实现 reward mock/replay 和完整 verify/report。

### 2026-08-12｜DAVIS 预处理媒体 Smoke Test

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:41:19 +08:00
- 执行位置：本地；合成 DAVIS fixture；CPU

**实验 ID**

- `W1-data-prepare-smoke-v01`

**行动与关键配置**

- 构造 50 帧、120×80、逐帧对齐 mask 的临时 DAVIS 序列。
- 执行预处理内部路径并验证 48 帧窗口、步长 3、16 帧、联合 mask 方形裁剪、512×512、8 fps 和清单校验。
- 命令：`uv run pytest tests/test_models_and_data.py`。

**结果**

- 7 个测试全部通过；合成输入产生 16 帧 512×512 PNG 和一个 16 帧、8 fps MP4。
- 对 40×40 mask 加 25% 上下文后得到 50 像素方形裁剪，符合协议。

**产物路径**

- 测试代码：`tests/test_models_and_data.py`
- 媒体仅位于 pytest 临时目录，测试后不作为研究产物保留。

**下一步**

1. 实现 10 inversion / 50 candidate 规划与规范化 cache key。
2. 实现 SQLite 状态缓存、mock 执行和断点续跑。

### 2026-08-12｜W1 数据协议、Schema 与固定 Manifest

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 11:40:32 +08:00
- 执行位置：本地 `D:\lab idea`
- Python：3.11.15

**实验 ID**

- `W1-data-contract-v01`

**行动与关键配置**

- 实现严格 Pydantic 类型：`ExperimentSpec`、`InputRecord`、`GenerationConfig`、`CandidateRecord`、`RewardRequest`、`RewardResult`。
- 新增固定 `configs/w1_manifest.yaml`：DAVIS-2017 train、10 个输入、4/3/3 任务分布、种子 `101/202/303/404/505`。
- 实现 DAVIS 帧/mask 对齐检查、最高 mask 面积 48 帧窗口、步长 3 抽取 16 帧、联合框加 25% 上下文、方形裁剪与 512×512 同步缩放。
- 修复 Typer 单命令折叠，形成 `w1 version/validate/prepare` 多命令入口。
- 执行 `uv run w1 version`、`uv run w1 validate` 和 `uv run pytest tests/test_models_and_data.py`。

**结果**

- CLI 输出版本 `0.1.0`，manifest 校验为 10 inputs / 5 seeds。
- 5 个 schema/泄漏测试全部通过；重复 seed、重复 sample、非法 split 和 IVEBench 内容均被拒绝。

**产物路径**

- `configs/w1_manifest.yaml`
- `src/w1_pipeline/models.py`、`data.py`、`hashing.py`、`cli.py`
- `tests/test_models_and_data.py`

**下一步**

1. 增加合成 DAVIS fixture，端到端验证预处理媒体与校验和。
2. 实现任务规划、SQLite 缓存和执行后端。

### 2026-08-12｜W1 工程与本地环境初始化

**状态：DONE（发现并保留 CLI 诊断）**

**时间与环境**

- 完成时间：2026-08-12 11:38:01 +08:00
- 执行位置：本地 `D:\lab idea`
- 主机：Windows 11；Python 3.11.15（uv 管理）

**实验 ID**

- `W1-env-bootstrap-v01`

**行动与关键配置**

- 执行 `git init`，新增 `pyproject.toml`、`.gitignore`、`README.md` 与 `src/w1_pipeline` 包骨架。
- 执行 `uv sync --python 3.11`，安装 Pydantic、Typer、PyYAML、pytest、Pillow、imageio 和 imageio-ffmpeg。
- 执行 `uv run python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` 验证媒体依赖。

**结果**

- Git 仓库和 `.venv` 成功建立，锁文件为 `uv.lock`。
- ffmpeg 7.1 可执行文件位于 `.venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`。
- `uv run w1 version` 暴露 Typer 单命令折叠行为：当前只有一个命令时 `version` 被当作额外参数；需在下一步增加回调或完整命令组后复测。

**产物路径**

- `pyproject.toml`、`uv.lock`、`.gitignore`、`README.md`、`src/w1_pipeline/`

**下一步**

1. 实现完整多命令 CLI，同时落地数据 schema、固定 W1 manifest 和校验器。
2. 为 CLI 与 schema 编写单元测试并复测命令发现行为。

### 2026-08-12｜方案重构

**状态：DONE**

**目标**

- 解析项目文档；
- 根据当前相关工作修正研究定位；
- 将时间线调整为 3–4 周基本成果、8 周完整成品；
- 精简文档并建立开发日志。

**完成内容**

- 将正式方案更新为 v4；
- 将主线调整为“验尺子 → 选 → 训 → 防”；
- 删除过时的零基础解释稿；
- 增加数据隔离、judge 决策门、Best-of-N 成本曲线、DPO 对照、hacking 压力测试和统计要求；
- 建立本 DEVLOG。

**结论**

- 9 月初答辩的最低闭环是 reward 初步校准与 Best-of-N；
- DPO、hacking 缓解和独立完整评测安排在八周成品阶段；
- 开始实现前必须确定硬件、可训练主干、数据下载和 MLLM judge 接口。

**下一步**

1. 记录本机 GPU、CUDA、磁盘和 Python 环境；
2. 确定推理 baseline 与 DPO 训练主干；
3. 建立代码目录和实验配置；
4. 完成 `E0-pipeline-v01`。

### 2026-08-12｜增加本地/A6000 分工与强制日志规则

**状态：DONE**

**环境**

- 本地工作区：`D:\lab idea`
- 本步骤未使用远程 A6000。

**步骤 ID**

- `DOC-workspace-rules-v01`

**完成内容**

- 新增根目录 `AGENTS.md`，规定每完成一个可验证开发步骤必须立即更新 DEVLOG；
- 在正式方案中新增“本地开发与 A6000 计算分工”；
- 明确真实模型推理、批量候选生成、GPU 指标、本地 VLM、LoRA/DPO、权重扫描和完整 benchmark 使用 A6000；
- 明确文档、代码、mock 测试、数据清单、结果分析和写作优先在本地完成；
- 增加 A6000 作业提交前后的最小记录要求。

**结果与产物**

- 规则文件：`AGENTS.md`
- 正式方案：`proposal.md`
- 答辩主线：`idea-logic.md`
- 开发日志：`DEVLOG.md`

**下一步**

1. 盘点本地与 A6000 的系统、CUDA、Python、磁盘和连接方式；
2. 确定推理 baseline 与可训练主干；
3. 为本地/远程代码同步和唯一实验输出目录制定实现方式。

---

## 记录模板

### 2026-08-12｜本地仓库同步前完整性回归

**状态：DONE**

**时间与环境**

- 完成日期：2026-08-12（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- Python：项目虚拟环境 `.venv\Scripts\python.exe`

**步骤 ID**

- `LOCAL-git-sync-verify-v01`

**操作与关键配置**

- 在提交 `4efa9e7`（`Prepare local repository for synchronization`）上执行 Git 对象完整性检查；
- 运行完整本地测试集；
- 关键命令：`git fsck --full`、`.venv\Scripts\python.exe -m pytest -q`、`git status --short --branch`。

**结果与产物**

- `git fsck --full` 通过，无对象错误；
- Pytest：18 项测试全部通过；
- 验证结束时工作区 clean，当前分支为 `main`；
- 产物路径：`D:\lab idea\.git`、`D:\lab idea\DEVLOG.md`。

**问题 / 失败**

- 无。

**下一步**

1. 提交本条验证记录；
2. 获取 GitHub 空仓库 URL 后设置 `origin` 并推送 `main`。

---

### 2026-08-12｜本地 Git 仓库同步基线整理

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-12 17:13:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未连接学校 A6000

**步骤 ID**

- `LOCAL-git-sync-baseline-v01`

**操作与关键配置**

- 检查现有 Git 历史、工作区、远程仓库、已跟踪文件及大文件；
- 确认 `.venv/`、`.pytest_cache/` 和 `artifacts/` 均由 `.gitignore` 排除；
- 确认唯一超过 50 MB 的扫描结果位于被忽略的 `.venv/` 内；
- 将本地默认分支由 `master` 重命名为 `main`；
- 关键命令：`git status --short --branch`、`git remote -v`、`git check-ignore -v`、`git branch -m master main`。

**结果与产物**

- 本地仓库已有 3 个历史提交，分支现为 `main`；
- 工作区在整理前为 clean，尚未配置远程仓库；
- 已跟踪文件数：33；未发现会被误提交的大型模型、数据集或虚拟环境文件；
- 产物路径：`D:\lab idea\.git`、`D:\lab idea\.gitignore`、`D:\lab idea\DEVLOG.md`。

**问题 / 失败**

- 尚未提供 GitHub 仓库 URL，因此本步骤不创建 `origin`，也不执行外部 push。

**下一步**

1. 提交本条日志并验证仓库完整性；
2. 用户创建或指定 GitHub 空仓库后，添加 `origin` 并推送 `main`；
3. 在学校服务器通过 GitHub（若可访问）或本地中转方式克隆。

---

复制以下区块到“每日记录”顶部或末尾：

````markdown
### YYYY-MM-DD｜简短标题

**状态：TODO / RUNNING / DONE / BLOCKED / INVALID**

**时间与环境**

- 开始/结束时间：
- 执行位置：本地 / 学校 A6000
- 主机/GPU：

**实验 ID**

- `E?-name-v??`

**目标**

- 

**环境与输入**

- Git commit / 代码版本：
- 模型与 checkpoint：
- 数据 split / 样本数：
- GPU / CUDA：
- 随机种子：

**命令或关键配置**

```text

```

**结果**

- 核心指标：
- 运行时间：
- 峰值显存：
- 产物路径：

**观察与结论**

- 

**问题 / 失败**

- 

**下一步**

1. 
````
