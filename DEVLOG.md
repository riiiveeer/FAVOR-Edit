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

### 2026-08-23｜阶段总结：Part A 完成 + Part B 纯工程完成，真实 judge/人工标注待前置（BLOCKED）

**状态：BLOCKED（等待外部前置：真实 judge 权重 + 人工标注）**

**时间与环境**

- 总结时间：2026-08-23 13:30（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；本轮无 GPU 作业，E0 只读

**本轮完成概览**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` 严格顺序，完成 Part A（E0 查验）与 Part B 全部**纯工程阶段**（scaffold→schema→pairs/packets→annotation-tool→runner/cache→metrics→mock E2E）。
- 每完成一个可验证步骤均即时追加 DEVLOG 并单独提交 Git，未合并笼统记录。
- 未破坏 E0：E0 输入目录（`E0-anyv2v-w1-v01`、`E0-anyv2v-smoke-v01`）全程只读，无写入/覆盖。

**Part A 结果（E0 查验）**

- 硬验收：`w1 verify --expected 50` → `{"valid": true, "count": 50, "errors": {}}`（50/50），复验两次一致。
- 审计工具：`src/w1_pipeline/e0_audit.py` + `scripts/build_e0_audit.py` + `tests/test_build_e0_audit.py`。
- 审计包 `/DATA/DATA4/hfy/outputs/E0-visual-audit-v01/`：50 张 4×4 联系表 + 22 个并排代理（512×256/8fps/16帧）+ `audit-manifest.json` + `audit.csv` + `SHA256SUMS` + `README.md`；`sha256sum -c` 全部 `: OK`（75 文件，6.2M）。
- 人工查验：`audit.csv` 50 行四维粗分（0/1/2）+ `usable_for_e1` 全 `yes`；匿名 `reviewer=anon-01`、`reviewed_at` 已填；`--verify-existing` 校验通过。
- 放行判定：满足 §6.1（50/50 valid、三类任务可判、10/10 sample 可成对、无源/候选错配）→ **Part A 放行**。

**Part B 纯工程阶段（逐步提交，commit 顺序如下）**

| 步骤 ID | commit | 内容 |
| --- | --- | --- |
| `E1-scaffold-v01` | `f10776d` | `src/e1_judge/` + 12 命令 CLI + configs/e1 + pyproject `e1` 入口 |
| `E1-schema-v01` | `da5d43f` | 严格 Pydantic（PairRecord/HumanAnnotation/JudgeRequest/JudgeResult/AdjudicatedLabel，`extra="forbid"`） |
| `E1-pairs-packets-v01` | `6770829` | 100 无序 pair（dev 30 + frozen 70）+ 确定性展示随机化 + media packets |
| `E1-annotation-tool-v01` | `8c3d0fa` | loopback 标注服务 + adjudicate（两人 + 第三人裁决） |
| `E1-runner-cache-v01` | `3f2d42f` | mock/replay/command backend + judge key + SQLite 缓存 + 排他锁 + 断点续跑 + merge |
| `E1-metrics-v01` | `d579bd7` | accuracy/swap/position bias/cluster bootstrap/分类别 + ranking + report + verify |
| `E1-mock-e2e-v01` | `bcfda1e` | 100 pair → 550 requests → 550 mock results → replay 缓存命中，`research_measurements=0` |

- 测试：**76/76 通过**（`tests/e1/` 下 8 个测试文件覆盖 §18.1–§18.7），`git diff --check` 全部通过。
- 关键修正：`absolute-v1` 改为「每个唯一候选 1 请求（50）」，避免原「每 pair 两个」导致 700 请求。

**当前 BLOCKED 状态（两个外部前置）**

1. `BLOCKED_MISSING_REAL_JUDGE`：只读盘点 `/DATA/DATA4/hfy/models` 仅有 `i2vgen-xl`(4.7G) + `instruct-pix2pix`(4.0G)，**无 VLM/LLM judge 权重**（无 Qwen-VL/InternVL/LLaVA 等）。
2. `BLOCKED_MISSING_HUMAN_LABELS`：E1 需两名真人标注 100 pairs + 第三人裁决争议；工具已就绪，但未启动，不得 mock 冒充。

**产物路径**

- 代码：`/home/sunyinan/FAVOR-Edit/src/e1_judge/`、`configs/e1/`、`tests/e1/`
- E0 审计包：`/DATA/DATA4/hfy/outputs/E0-visual-audit-v01/`
- E1 输出目录 `/DATA/DATA4/hfy/outputs/E1-judge-pilot-v01` **尚未创建**（按序等真实 judge 就位后建，避免空目录污染）

**后续方案选项（待你确定）**

- 选项 A：你在联网/镜像机器准备一个视频/多图 VLM judge snapshot（固定 revision + SHA256SUMS + MODEL_CARD_LOCAL.md），上传服务器后继续 `E1-judge-smoke-v01` → dev → freeze → pilot → analysis。
- 选项 B：先推进人工标注（两名真人完成 100 pairs），judge 权重稍后到位；两者可并行准备。
- 选项 C：暂停 E1，回看/调整 judge 选型或数据范围后再继续。

**结论（严格措辞）**

- `E1 framework complete; E1 research acceptance not complete.`
- Part A 已放行；Part B 纯工程全部完成并通过 550/550 mock 验收；真实 judge 与人工标注缺失即为 BLOCKED，未用 mock 冒充研究结果。

### 2026-08-23｜E1 真实 judge 模型盘点（BLOCKED）

**状态：BLOCKED（BLOCKED_MISSING_REAL_JUDGE）**

**时间与环境**

- 记录时间：2026-08-23 13:25（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；只读盘点，无 GPU 作业

**步骤 ID**

- `E1-judge-model-inventory-v01`

**行动与关键配置**

- 按手册 §14.1 只读盘点 `/DATA/DATA4/hfy/models`（不使用会打印 credential 的命令）。

**结果**

- 服务器现有权重仅有：
  - `i2vgen-xl`（4.7G）——AnyV2V inversion 的生成模型，非 judge。
  - `instruct-pix2pix`（4.0G）——AnyV2V 首帧编辑模型，非 judge。
- **不存在任何支持视频/多图输入的 VLM 或 LLM judge 权重**（无 Qwen-VL/InternVL/LLaVA/GPT 类模型）。
- 因此真实 judge 环节（§14–§15.3）无法在当前服务器执行。

**判定**

- `decision=BLOCKED_MISSING_REAL_JUDGE`。
- 依 AGENTS.md 与任务约束，不得用 mock/replay 或粗分冒充真实 judge 结果；E1 框架与 mock 验收已完成，但 **E1 研究验收未完成**。

**产物路径**

- 无新增产物（只读盘点）。

**下一步（需外部前置）**

1. 在联网/镜像机器准备一个支持视频或多图输入的 judge 模型 snapshot，固定 revision + 生成 SHA256SUMS + `MODEL_CARD_LOCAL.md`，上传到 `/DATA/DATA4/hfy/models/<judge-name>-<revision>` 并建独立环境 `/DATA/DATA4/hfy/envs/e1-judge-<model>`。
2. 权重就位后：`E1-judge-smoke-v01`（2 dev pair rubric-swap 4 方向）→ `E1-judge-dev-v01` → `E1-prompt-freeze-v01` → `E1-judge-pilot-v01` → `E1-analysis-v01`。
3. 人工标注（§11）同样需两名真人完成 100 pairs，当前未启动，不得 mock 冒充。

### 2026-08-23｜E1 mock E2E 全链路验收（E1-mock-e2e-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 13:20（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯 CPU mock 作业，无 GPU

**步骤 ID**

- `E1-mock-e2e-v01`

**行动与关键配置**

- 修正 `build_judge_plan`：`absolute-v1` 为每个唯一候选生成 1 个请求（50），而非每 pair 两个（原会算出 700）。
- 新增 `tests/e1/test_e2e_mock.py`：完整 mock E2E——100 pair → 550 judge requests → 550 mock results → 第二次运行 550 缓存命中 → 每个 result `raw_response.research_result=false`、`confidence=0`。
- 修正测试 fixture：不同 sample 相同 seed 的视频内容撞 checksum，改为 seed×1000+sample_index，确保 50 个候选 checksum 唯一、judge_key 唯一。

**结果**

- `python -m pytest`：**76/76 通过**（原 65 + 新 1 e2e + 之前 metrics 11），耗时 54.37s。
- `git diff --check`：无 whitespace error。
- mock E2E：550/550 请求、550 结果、replay 缓存命中、`research_measurements=0`。

**产物路径**

- `tests/e1/test_e2e_mock.py`
- `src/e1_judge/runner.py`（absolute 请求计数修正）

**下一步**

1. 提交本步骤。
2. 纯工程阶段全部完成。下一步进入「真实 judge」边界：`E1-judge-model-inventory-v01` 只读盘点（已确认无 VLM 权重 → 返回 `BLOCKED_MISSING_REAL_JUDGE`），并如实汇报 Part B 阶段性状态。

### 2026-08-23｜E1 metrics/report/verify 实现（E1-metrics-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 13:10（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-metrics-v01`

**行动与关键配置**

- 实现 `src/e1_judge/metrics.py`（§16）：
  - `pairwise_accuracy`：decisive-only / effective / coverage（judge 输出 tie/uncertain 计未正确 + 单独 coverage）。
  - `swap_consistency`：两方向映射回 canonical 候选身份后比较（tie/tie 与 uncertain/uncertain 一致，明确 vs tie/uncertain 不一致）。
  - `position_bias`：left/right 原始选择率。
  - `cluster_bootstrap_ci`：以 sample_id 聚类重采样，固定 seed、95% percentile。
  - `category_metrics`：attribute/object/local 分列。
- 实现 `src/e1_judge/ranking.py`：tie-aware Bradley-Terry 效用 + Kendall tau + Spearman。
- 实现 `src/e1_judge/verification.py`：`verify_results`（请求计数、重复 ID、strict 模式缺/多请求、human 标签 ≥100）。
- 实现 `src/e1_judge/reporting.py`：`generate_report` 写 `E1_REPORT.md` 摘要。
- 新增 `tests/e1/test_metrics.py`：11 条测试（100%/0% accuracy、tie/uncertain coverage、swap 一致/不一致、position bias 翻转、bootstrap 可复现、排序已知序、kendall/spearman、analyze 写 metrics）。

**结果**

- `python -m pytest tests/e1/test_metrics.py`：**11/11 通过**。
- `git diff --check`：无 whitespace error。

**产物路径**

- `src/e1_judge/metrics.py`、`ranking.py`、`verification.py`、`reporting.py`
- `tests/e1/test_metrics.py`

**下一步**

1. 提交本步骤。
2. `E1-mock-e2e-v01`：真实跑 100 pair → 550 requests → 550 mock results → replay → report（`research_measurements=0`）+ `verify --expect-requests 550`。

### 2026-08-23｜E1 runner/cache/backend/锁实现（E1-runner-cache-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 13:00（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-runner-cache-v01`

**行动与关键配置**

- 实现 `src/e1_judge/cache.py`：SQLite `judge_results` 表（judge_key 主键、request_id/status/payload/error/时间戳），WAL。
- 实现 `src/e1_judge/backends/`：
  - `base.py`：`JudgeBackend.run(request_path, output_path)`。
  - `mock.py`：确定性假结果（`overall=uncertain, confidence=0, research_result=false`），非研究测量。
  - `replay.py`：严格回放已有真实结果（按 judge_key 找源文件）。
  - `command.py`：调用独立 judge 环境 `<judge-python> <judge-script> --request --output`，写临时文件后原子重命名。
- 实现 `src/e1_judge/runner.py`：
  - `judge_key`：§13.2 全部字段的规范化 SHA-256（方向不同产生不同 key）。
  - `acquire_lock/release_lock/unlock`：`O_CREAT|O_EXCL` 排他锁，锁内记录 PID/hostname；陈旧锁只报告，unlock 写审计记录。
  - `build_judge_plan`：100 pair → 4 方法共 550 请求（absolute 50 / single 100 / swap 200 / rubric-swap 200）。
  - `run_judge`：缓存命中不调 backend；失败写入缓存允许重试；raw response 永久保存。
  - `merge_results`：拒绝重复 request ID。
- 新增 `tests/e1/test_cache_and_resume.py`：10 条测试（judge key 顺序无关/方向敏感、缓存读写命中、锁互斥、unlock 移除锁/无锁失败、plan 550 计数、mock run 与缓存续跑、merge 去重/合并）。

**结果**

- `python -m pytest tests/e1/test_cache_and_resume.py`：**10/10 通过**。
- `git diff --check`：无 whitespace error。

**产物路径**

- `src/e1_judge/cache.py`、`runner.py`
- `src/e1_judge/backends/{base,mock,replay,command}.py`
- `tests/e1/test_cache_and_resume.py`

**下一步**

1. 提交本步骤。
2. `E1-metrics-v01`：§16 全部指标（accuracy/swap consistency/position bias/排序相关/分类别/cluster bootstrap）+ report + verify。

### 2026-08-23｜E1 人工标注工具与裁决实现（E1-annotation-tool-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 12:50（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-annotation-tool-v01`

**行动与关键配置**

- 实现 `src/e1_judge/annotations.py`：
  - `run_annotation_server`：Python 标准库单用户 HTTP 服务，默认 loopback；显示 instruction/target caption，四维 + overall + confidence 选择；上一条/下一条、断点续标（读取已有标注跳过）、防止同 annotator 重复提交同一 pair；保存 display_direction。
  - `adjudicate`：两名独立标注者对每个 pair 判一致（overall + 四维全部相等）；争议时要求第三人裁决文件，缺第三人则失败（不自动任选）；输出 AdjudicatedLabel，标注 tie/uncertain。
- 新增 `tests/e1/test_annotations.py`：6 条测试（一致取第一、争议缺第三人失败、争议用第三人、缺标注失败、tie/uncertain 标记、agreement helper）。

**结果**

- `python -m pytest tests/e1/test_annotations.py`：**6/6 通过**。
- `git diff --check`：无 whitespace error。

**产物路径**

- `src/e1_judge/annotations.py`
- `tests/e1/test_annotations.py`

**下一步**

1. 提交本步骤。
2. `E1-runner-cache-v01`：mock/replay/command backend、judge key、SQLite 缓存、排他锁、断点续跑。

### 2026-08-23｜E1 pair 与 media packet 实现（E1-pairs-packets-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 12:40（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-pairs-packets-v01`

**行动与关键配置**

- 实现 `src/e1_judge/pairs.py`：
  - `build_pairs`：按 sample 对 5 个候选做全量两两组合，共 100 无序 pair（每 sample 10）。
  - dev 30（`bear-white/dog-tiger/hiker-backpack`）+ frozen-eval 70（其余 7 sample）。
  - 每个 pair 关联 source/candidate 路径与 checksum、canonical A/B 字典序、display_direction 确定性（`pair_id|annotator|seed` 的 SHA-256 决定方向）。
  - `usable_for_e1!=yes` 的候选相关 pair 标记 `excluded_reason`（不静默删除）；相同 video_checksum 标记 `identical_media=true`。
- 实现 `src/e1_judge/packets.py`：
  - `build_packets`：每 pair 目录含 `source.mp4`/`candidate-a.mp4`/`candidate-b.mp4`（软链优先、失败降级拷贝）、三个 4×4 contact sheet、`mask-overlay.jpg`、`metadata.json`（原始绝对路径 + checksum + packet_checksum + mask_available）。
  - 输出目录已存在即拒绝。
- 新增 `tests/e1/test_pairs_packets.py`：5 条测试（100 pair / dev 30 + frozen 70 / 无跨 sample / 方向确定性 / packet 结构与 metadata / 输出目录已存在拒绝）。

**结果**

- `python -m pytest`：**48/48 通过**（原 43 + 新 5），耗时 51.64s。
- `git diff --check`：无 whitespace error。

**产物路径**

- `src/e1_judge/pairs.py`
- `src/e1_judge/packets.py`
- `tests/e1/test_pairs_packets.py`

**下一步**

1. 提交本步骤。
2. `E1-annotation-tool-v01`：loopback 标注服务 + adjudicate（两人 + 第三人裁决）。

### 2026-08-23｜E1 严格 schema 实现（E1-schema-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 12:20（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-schema-v01`

**行动与关键配置**

- 按手册 §9 实现严格 Pydantic schema（`src/e1_judge/models.py`），全部 `extra="forbid"`：
  - `PairRecord`（§9.1）：pair_id/sample_id/task_type/instruction/target_caption/源与候选路径与 checksum/canonical A-B/display_direction/split/randomization_seed/schema version；校验候选不同、canonical 字典序、checksum 格式、IVEBench 拒绝。
  - `HumanAnnotation`（§9.2）：四维 + overall preference 限定 `a/b/tie/uncertain`，confidence∈[0,1]。
  - `JudgeRequest`（§9.3）：absolute/pairwise 方向，absolute 不得携带 candidate_b_checksum，IVEBench 拒绝。
  - `JudgeResult`（§9.4）：judge_key 64 hex、raw_response 必存、status/维度/置信度。
  - `AdjudicatedLabel`（§9.5）：两名标注者 min_length=2、agreement/第三人/四维/overall/tie/uncertain。
- 实现 `hashing.py`：`canonical_json` + `canonical_sha256`（排序键、稳定顺序）。
- 实现 `validate_config`：校验 `pilot.yaml` 必需键 + 550 请求合计。
- 新增 `tests/e1/test_models.py`：13 条测试覆盖缺字段、非法 preference/split、自比较、canonical 未排序、checksum 格式、IVEBench、extra 拒绝、哈希顺序无关/值区分。

**结果**

- `python -m pytest`：**43/43 通过**（原 30 + 新 13），耗时 23.79s。
- `git diff --check`：无 whitespace error（修正两处 EOF 空行）。

**产物路径**

- `src/e1_judge/models.py`
- `src/e1_judge/hashing.py`
- `tests/e1/test_models.py`

**下一步**

1. 提交本步骤。
2. `E1-pairs-packets-v01`：100 无序 pair（dev 30 / frozen 70）+ 确定性展示随机化 + media packets（软链 + contact sheet + metadata）。

### 2026-08-23｜E1 包骨架与 CLI 完成（E1-scaffold-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 12:10（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业

**步骤 ID**

- `E1-scaffold-v01`

**行动与关键配置**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` §8 新增独立包 `src/e1_judge/`，不修改 W1 研究边界：
  - `cli.py`：12 个命令 `validate/build-pairs/build-packets/annotate/adjudicate/plan/run/unlock/merge-results/analyze/verify/report`。
  - 模块骨架：`models.py`、`hashing.py`、`pairs.py`、`packets.py`、`annotations.py`、`prompts.py`、`cache.py`、`runner.py`、`ranking.py`、`metrics.py`、`reporting.py`、`verification.py`。
  - 后端骨架：`backends/{base,mock,replay,command}.py`。
- 新增 `configs/e1/`：`pilot.yaml`（冻结协议 + 4 方法 550 请求预算 + 判定门槛 + bootstrap seed）+ 4 个 prompt 占位文件。
- 更新 `pyproject.toml`：注册 `e1 = "e1_judge.cli:app"`，wheel 打包 `src/e1_judge`。
- 重新 `pip install --no-deps -e .` 并验证 `e1 --help`。
- 新增 `tests/e1/test_scaffold.py`：验证 12 命令发现与子命令帮助。

**结果**

- `e1 --help` 列出全部 12 个命令。
- `python -m pytest`：**30/30 通过**（原 28 + 新 2），耗时 25.44s。
- `git diff --check`：无 whitespace error。

**产物路径**

- `src/e1_judge/`（含 `cli.py`、模块骨架、`backends/`）
- `configs/e1/`（`pilot.yaml` + 4 prompt 占位）
- `tests/e1/test_scaffold.py`

**下一步**

1. 提交本步骤（代码 + 配置 + 测试 + DEVLOG）。
2. `E1-schema-v01`：实现严格 Pydantic schema（PairRecord/HumanAnnotation/JudgeRequest/JudgeResult/AdjudicatedLabel），`extra="forbid"`。

### 2026-08-23｜E0 视觉人工查验完成并放行

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 12:05（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；无 GPU 作业，无 E0 写入

**步骤 ID**

- `E0-visual-review-v01`

**行动与关键配置**

- 人工已填写 `audit.csv`：50 行四维粗分（0/1/2）、`usable_for_e1` 全部 `yes`、failure_tags/systematic_failure 为空（无失败/无系统性失败）。
- 因标注者匿名，按约定将 `reviewer` 统一填匿名 ID `anon-01`、`reviewed_at` 填查验时间戳 `2026-08-23T12:05:00+08:00`（50 行）。
- 运行 `python scripts/build_e0_audit.py --verify-existing /DATA/DATA4/hfy/outputs/E0-visual-audit-v01` 校验。

**结果**

- `--verify-existing` 返回 `{'valid': True, 'rows': 50, 'spot_check_ids': [...22...]}`，校验通过。
- 50 行审计记录无重复 ID；22 个固定抽查候选四维粗分完整；failure tag 枚举合法；`usable_for_e1` 仅 yes/no；E0 输入 checksum 未变化。
- 四维粗分分布：faithfulness 0×7/1×22/2×21；preservation 0×11/1×18/2×21；temporal 0×3/1×22/2×25；quality 0×3/1×30/2×17。

**放行判定**

- 满足 §6.1 放行规则：硬验收仍 50/50 valid；三类任务存在可判断候选差异；10/10 sample 可形成有效 pair；无源/候选错配。
- **Part A 放行，允许进入 E1 Pilot。**

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-visual-audit-v01/audit.csv`（50 行已填写）

**下一步**

1. 提交本记录（DEVLOG）。
2. 进入 Part B：`E1-scaffold-v01`（E1 包骨架 + CLI + pyproject 入口 + configs/e1）。

### 2026-08-23｜E0 视觉人工查验待执行（BLOCKED）

**状态：BLOCKED（等待人工视觉标注）**

**时间与环境**

- 记录时间：2026-08-23 11:38（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；本步骤无 GPU 作业、无 E0 写入

**步骤 ID**

- `E0-visual-review-v01`

**行动与关键配置**

- 审计包已就绪于 `/DATA/DATA4/hfy/outputs/E0-visual-audit-v01`（50 联系表 + 22 并排代理 + 空 `audit.csv` + `audit-manifest.json` + `SHA256SUMS` + `README.md`）。
- `audit.csv` 已按固定表头生成，`candidate_id` 已预填，四维粗分 / failure tags / `usable_for_e1` / reviewer / reviewed_at 均为空，等待人工填写。
- 依手册 §6，四维粗分、failure tags、`usable_for_e1` 属于**人工视觉判断**，本工具（及本助手）不得以 AI 冒充人工视觉查验、不得编造评分。

**结果**

- 未执行人工查验；`audit.csv` 仍为空白状态。
- 因此按 AGENTS.md 与任务约束，Part A 的人工查验环节判定为 **BLOCKED（缺人工标注）**，不进入 Part B（E1 施工）。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-visual-audit-v01/audit.csv`（空，待人工填写）

**下一步（需人工完成）**

1. 人工按 §6 顺序查验：先看 50 张 `contact-sheets/*.jpg`，再看 22 个 `proxies/*.mp4`（完整 16 帧），异常候选补看 E0 原始 `video.mp4`。
2. 在 `audit.csv` 填写四维粗分（0/1/2 或空）、failure tags（枚举）、`usable_for_e1`（仅 yes/no）、reviewer、reviewed_at。
3. 检查同一 sample 五个 seed 是否有系统性失败。
4. 人工填写后运行 `python scripts/build_e0_audit.py --verify-existing /DATA/DATA4/hfy/outputs/E0-visual-audit-v01` 校验。
5. 根据 §6.1 放行规则判定是否进入 E1 Pilot；放行确认后，再开始 Part B。

### 2026-08-23｜E0 轻量审计包构建完成（E0-visual-audit-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 11:37（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯 CPU ffmpeg 构建，无 GPU 作业；E0 输入只读

**实验 ID**

- `E0-visual-audit-v01`

**行动与关键配置**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` §5 执行真实构建：
  `python scripts/build_e0_audit.py --plan $E0/plan.json --candidates $E0/candidates.json --output-dir /DATA/DATA4/hfy/outputs/E0-visual-audit-v01`
- 构建前确认输出目录不存在（`test ! -e`），干净新建。
- 构建后执行 §5 验收：联系表/代理计数、`du`、`sha256sum -c SHA256SUMS`，并复验 E0 `w1 verify` 仍 50/50。

**结果**

- 产物：`50` 张联系表（`contact-sheets/<candidate_id>.jpg`，4×4）；`22` 个并排代理（`proxies/<candidate_id>.mp4`，512×256 / 8fps / 16 帧）。
- `SHA256SUMS` 覆盖 75 个产物文件，`sha256sum -c` 全部 `: OK`（50 联系表 + 22 代理 + audit-manifest.json + audit.csv + README.md）。
- 目录大小：`6.2M`（轻量，不搬运原视频）。
- 固定 22 代理集合与手册 §4.3 一致：`bear-white`/`dog-tiger`/`hiker-backpack` 各 5 seed（15）+ 其余 7 sample 的 `seed 303`（7）= 22。
- E0 复验：`w1 verify --expected 50` 仍返回 `{"valid": true, "count": 50, "errors": {}}`；E0 `plan.json` checksum `06d9fa2f…` 记录于 manifest，未发生变化。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-visual-audit-v01/`
  - `contact-sheets/`（50 张 jpg）
  - `proxies/`（22 个 mp4）
  - `audit-manifest.json`、`audit.csv`、`SHA256SUMS`、`README.md`

**下一步**

1. `E0-visual-review-v01`：人工按 §6 顺序查验（50 联系表 → 22 完整代理 → 异常候选补看原始 video.mp4），填写 `audit.csv` 四维粗分 / failure tags / `usable_for_e1`，并判定是否放行进入 E1。
2. 人工填写后运行 `python scripts/build_e0_audit.py --verify-existing $E0_AUDIT` 校验。

### 2026-08-23｜E0 审计脚本与测试实现（E0-audit-tool-v01）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 11:36（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；纯代码/测试，无 GPU 作业，无 E0 写入

**步骤 ID**

- `E0-audit-tool-v01`

**行动与关键配置**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` §4 实现轻量审计工具：
  - `src/w1_pipeline/e0_audit.py`：`build_audit()`（构建）与 `verify_existing()`（§6 校验）+ `spot_check_ids()` 固定 22 代理集合逻辑。
  - `scripts/build_e0_audit.py`：薄 CLI，`--plan --candidates --output-dir` 构建，`--verify-existing` 校验。
  - `tests/test_build_e0_audit.py`：9 条测试覆盖 §4.5 全部清单。
- 关键实现：
  - 输出目录已存在即失败（`AuditError`）。
  - 输入校验：10 inversions / 50 candidates、全 `succeeded`、candidate ID/sample/seed 与 plan 一一对应、video/frames checksum 匹配、16 帧、ffmpeg/ffprobe 可执行。
  - 50 张联系表：`scale=160:160:flags=lanczos,tile=4x4:padding=2:margin=2`（真实 smoke 验证输出 650×650，4×4）。
  - 22 个并排代理：左源右候选 `hstack`，512×256 / 8fps / 16 帧 / H.264 crf=30 faststart（真实 smoke 验证）。
  - `audit-manifest.json`（记录 E0 plan/candidates 绝对路径+SHA-256、code_snapshot、50 candidate ID、22 spot-check ID、原/编辑视频、contact sheet、proxy 路径与 checksum、instruction/target_caption/task_type/seed、ffmpeg 版本与时间）。
  - `audit.csv`（固定 11 列表头）、`SHA256SUMS`（不含自身、可 `sha256sum -c`）、`README.md`。
- 固定抽查集合：`bear-white`/`dog-tiger`/`hiker-backpack` 全 5 seed + 其余 7 sample 的 seed 303 = 15+7 = 22。

**结果**

- `w1-control` 环境 `python -m pytest`：**28/28 通过**（原 19 + 新 9），耗时 24.96s。
- `git diff --check`：无 whitespace error。
- 新增文件：`src/w1_pipeline/e0_audit.py`、`scripts/build_e0_audit.py`、`tests/test_build_e0_audit.py`。
- 构建过程只读 E0，不写入 E0 输入目录（测试中显式断言构建前后 E0 checksum 不变）。

**产物路径**

- `src/w1_pipeline/e0_audit.py`
- `scripts/build_e0_audit.py`
- `tests/test_build_e0_audit.py`

**下一步**

1. 提交本步骤（代码 + 测试 + DEVLOG）。
2. `E0-visual-audit-v01`：在 `$E0_AUDIT=/DATA/DATA4/hfy/outputs/E0-visual-audit-v01` 运行真实构建，核对 50 联系表 / 22 代理 / `sha256sum -c` 全通过，并复验 E0 仍 50/50。

### 2026-08-23｜E0 硬验收复验守卫（只读重跑）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-23 09:52（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）；只读重跑复验，无 GPU 作业，无 E0 写入

**步骤 ID**

- `E0-audit-hard-verify-v02`

**行动与关键配置**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` §3/§21 停止条件守卫，在启动 Part A 施工前只读重跑 `w1 verify --expected 50 --candidates /DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/candidates.json`（日志 `/tmp/e0-verify-v01.log`）。
- 再次执行 50 条清单断言：总数=50、全 `succeeded`、每候选 16 `frame_paths`/16 `frame_checksums`、`candidate_id` 唯一、`(sample_id, seed)` 唯一。
- 只读复核工作树：`main` @ `244ffa46e38ce16af1688c16a359d88757e3d93d`，工作树仅 `DEVLOG.md` 待提交；E0 审计/E1 输出目录均不存在，可干净新建；控制环境 `w1-control` 的 `python`/`w1` 可执行，`ffmpeg`/`ffprobe` 位于 `/usr/bin`。

**结果**

- `w1 verify` 返回 `{"valid": true, "count": 50, "errors": {}, "reproducible": null}`，与 2026-08-21 记录完全一致。
- 清单断言全部通过：status 50×`succeeded`；samples=10；seeds=[101,202,303,404,505]；runtime_seconds=12413.71；peak_vram_mb=22476.0。
- E0 输入未做任何写入。

**产物路径**

- 复验日志：`/tmp/e0-verify-v01.log`（临时，不入库）

**下一步**

1. `E0-audit-tool-v01`：实现 `scripts/build_e0_audit.py` + `tests/test_build_e0_audit.py`，通过后提交 Git。

### 2026-08-21｜E0 硬验收复查（50/50）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-21 10:04（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`sunyinan@ps`）；只读复验，无 GPU 作业

**步骤 ID**

- `E0-audit-hard-verify-v01`

**行动与关键配置**

- 执行 `w1 verify --expected 50 --candidates /DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/candidates.json`，日志保存于 `/tmp/e0-verify-v01.log`。
- 额外执行 50 条清单断言：总数=50、全 `succeeded`、每候选 16 `frame_paths`/16 `frame_checksums`、`candidate_id` 唯一、`(sample_id, seed)` 唯一。

**结果**

- `w1 verify` 返回 `{"valid": true, "count": 50, "errors": {}, "reproducible": null}`。
- 额外断言全部通过：status 50×`succeeded`；samples=10；seeds=[101,202,303,404,505]；候选总 runtime_seconds=12413.71；峰值 peak_vram_mb=22476.0。
- E0 输入未做任何写入。

**产物路径**

- 复验日志：`/tmp/e0-verify-v01.log`（临时，不入库）

**下一步**

1. `E0-audit-tool-v01`：实现 `scripts/build_e0_audit.py` + `tests/test_build_e0_audit.py`，通过后提交 Git。

### 2026-08-21｜E0 只读预检（Part A 开工）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-21 09:58（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`sunyinan@ps`），只读预检，无 GPU 作业

**步骤 ID**

- `E0-audit-preflight-v01`

**行动与关键配置**

- 按 `docs/E0_AUDIT_E1_EXECUTION.md` §2 执行只读预检：`git status --short --branch`、`git rev-parse HEAD`、控制环境 `python`/`w1` 可执行性、E0 输入文件存在性、ffmpeg 版本、GPU 与磁盘。
- 确认 E0 只读输入完整：`plan.json`（10 inversions / 50 candidates）、`candidates.json`（50 条全 succeeded）、`cache.sqlite3`、`candidates/` 目录均存在；`E0-anyv2v-smoke-v01` 亦存在。
- 确认审计输出目录 `E0-visual-audit-v01` 与 E1 目录 `E1-judge-pilot-v01` 当前均不存在，可干净新建。

**结果**

- Git：`main`，HEAD `244ffa46e38ce16af1688c16a359d88757e3d93d`，工作区 clean（仅本 DEVLOG 待改）。
- 控制环境 `/DATA/DATA4/hfy/envs/w1-control/bin/{python,w1}` 均存在且可执行。
- ffmpeg/ffprobe：`4.2.7-0ubuntu0.1`。
- GPU：6×`NVIDIA RTX A6000`（每卡 49140 MiB）。
- 磁盘：`/DATA/DATA4` 余 255G（99% 已用但可写）。
- 任务分布核对：attribute 4 / object 3 / local 3，seed 101/202/303/404/505，与手册 §4.3 固定 22 代理集合一致。

**产物路径**

- 无新增产物（只读预检）。

**下一步**

1. `E0-audit-hard-verify-v01`：`w1 verify --expected 50` 复验 50/50，并跑额外 50 条清单断言。

### 2026-08-20｜E0/E1 施工手册最终自动校验

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-20 20:51:27 +08:00
- 执行位置：本地 `D:\lab idea`；Python 文本检查与 Git whitespace 检查

**步骤 ID**

- `DOC-e0-e1-validation-v02`

**行动与关键配置**

- 修正文档执行链：prompt 冻结后重建 `judge-plan-frozen.json`，最终 dev/frozen-eval 结果通过 `merge-results` 严格合并。
- 明确 50 个候选全部填写 E0 可用性，22 个固定候选完成四维粗分和完整视频播放；相同媒体 checksum 的不同 seed pair 作为合法 tie 案例保留。
- 使用 Python 检查 UTF-8、Markdown code fence 配对及 10 项关键协议，并执行 `git diff --check`。

**结果**

- 文档共 1571 行、43527 字节、124 个 code fence（配对）；10/10 关键协议检查通过，无 UTF-8 replacement character。
- `git diff --check` 通过；仅有 Windows LF/CRLF 提示，不构成 whitespace error。
- 当前改动为 `DEVLOG.md` 和新增 `docs/E0_AUDIT_E1_EXECUTION.md`，尚未提交。

**产物路径**

- `D:\lab idea\docs\E0_AUDIT_E1_EXECUTION.md`
- `D:\lab idea\DEVLOG.md`

**下一步**

1. 将施工手册交给服务器端 Cline，从 E0 只读预检开始逐步执行。
2. 服务器完成每一步后提交代码与 DEVLOG；真实 judge 权重或人工标注缺失时按文档返回 BLOCKED，不得用 mock 冒充实验完成。

### 2026-08-20｜E0/E1 施工手册首次自动校验

**状态：FAILED（校验脚本断言过严，文档未发现对应缺陷）**

**时间与环境**

- 完成时间：2026-08-20 20:50:50 +08:00
- 执行位置：本地 `D:\lab idea`；Python 文本检查与 Git whitespace 检查

**步骤 ID**

- `DOC-e0-e1-validation-v01`

**行动与关键配置**

- 检查 Markdown code fence 是否配对、UTF-8、关键数量/门槛/离线变量是否存在，并执行 `git diff --check`。
- 检查脚本错误地要求文档包含精确中文短语 `550 个请求`，而文档实际使用 `550 judge requests`、`550 条` 和表格合计 `550`。

**结果**

- 关键短语断言因测试字面量过严失败；这是校验脚本问题，不是施工协议或数量缺失。
- `git diff --check` 未报告 whitespace error，仅提示 Windows 工作区未来可能将 `DEVLOG.md` 的 LF 转为 CRLF。

**产物路径**

- `D:\lab idea\docs\E0_AUDIT_E1_EXECUTION.md`

**下一步**

1. 将校验条件改为匹配文档实际使用的 `550 judge requests`，重跑完整自动校验。

### 2026-08-20｜E0 查验与 E1 施工手册定稿

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-20 20:46:56 +08:00
- 执行位置：本地 `D:\lab idea`；文档与协议设计，无 GPU 作业

**步骤 ID**

- `DOC-e0-audit-e1-execution-v01`

**行动与关键配置**

- 基于服务器实际路径、现有 W1/E0 产物和 `proposal.md` 的 E1 决策门，新增可直接交给服务器端 Cline 的详细执行手册。
- 固定 E0 只读输入为 `/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01`，审计输出为唯一目录 `E0-visual-audit-v01`；规定生成全部 50 个联系表和 22 个分层并排代理。
- 固定 E1 Pilot 为 10 输入、50 候选、100 个无序 pair，开发/冻结评估按 30/70 pairs 划分；四种 judge 方法共规划 550 个请求。
- 施工范围覆盖严格 schema、pair/media packet、离线人工标注、mock/replay/command backend、SQLite 缓存、排他锁、位置去偏、cluster bootstrap、报告和 PASS/FAIL/BLOCKED 判定。
- 保持原定硬门槛：总体成对准确率不低于 70%，换位一致率不低于 85%；明确 E1 Pilot 只允许形成 provisional 决策，且 mock/replay 不是研究测量。
- 代码 snapshot：`0fa6d85454708667ad948351ad367397c6a446f4`；新增文档后工作树 dirty。

**结果**

- 已生成 1528 行详细施工文档；包含逐步命令、预期数量、测试计划、DEVLOG/提交边界、离线模型准备、停止条件和 Cline 完工汇报模板。
- 本步骤只编写文档，没有启动服务器查验、人工标注或真实 judge，因此不声称 E0 视觉审计或 E1 研究验收已完成。

**产物路径**

- `D:\lab idea\docs\E0_AUDIT_E1_EXECUTION.md`

**下一步**

1. 对手册执行 Markdown 结构、关键路径、命令和 Git diff 检查。
2. 将文档交给服务器端 Cline，严格从 `E0-audit-preflight-v01` 开始执行并逐步追加 DEVLOG。

### 2026-08-19｜同步后本地回归验证

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-19 13:31:42 +08:00
- 执行位置：本地 `D:\lab idea`；Python 3.11 控制环境

**实验 ID**

- `SYNC-school-results-regression-v01`

**行动与关键配置**

- 对同步后的 commit `7c6d851` 执行 `uv run pytest` 和 `git diff --check`。
- 回归覆盖数据协议、缓存/断点续跑、AnyV2V dict_file adapter、reward/verify/report 与离线交付辅助工具。

**结果**

- 19/19 测试通过，耗时 18.53 秒。
- `git diff --check` 无错误；当前仅本次新增 DEVLOG 记录尚未提交。
- 服务器端 `dict_file` 适配修复未破坏本地控制链路。

**产物路径**

- 测试目录：`D:\lab idea\tests`
- 同步代码：`D:\lab idea\src\w1_pipeline\backends.py`

**下一步**

1. 汇总 W1 当前完成度与遗留风险。
2. 从学校服务器同步真实候选媒体、`cache.sqlite3`、运行日志和报告到本地归档；Git 中当前仅有代码和文字记录，没有大体积真实产物。

### 2026-08-19｜同步学校服务器提交到本地

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-19 13:30:12 +08:00
- 执行位置：本地 `D:\lab idea`；通过 GitHub `origin/main` 同步

**实验 ID**

- `SYNC-school-results-v01`

**行动与关键配置**

- 执行 `git fetch --prune origin`，确认远端比本地领先 12 个提交。
- 执行 `git pull --ff-only origin main`，从 `0e0c02a` fast-forward 到 `7c6d851`。
- 同步内容包括远程 A6000 环境准备、DAVIS 处理、真实双 smoke、AnyV2V 适配修复、50 候选批任务及完成记录。
- 同时只读探测三个学校 SSH alias，均在 banner 阶段超时，未直接读取服务器文件。

**结果**

- 本地 `main` 已同步到 `7c6d8513119390f1ec7bc84999e8824d212d5201`。
- 本次同步修改 `DEVLOG.md`、`src/w1_pipeline/backends.py` 和 `tests/test_anyv2v_adapter.py`；未覆盖本地实验产物。

**产物路径**

- 本地仓库：`D:\lab idea`
- 同步基线 commit：`7c6d851`

**下一步**

1. 审阅新增 DEVLOG 和代码差异，核实真实 smoke、50 候选成功数、媒体校验与遗留问题。
2. 检查远程结果是否已提交候选清单/日志摘要，必要时给出应从服务器带回的具体文件列表。

### 2026-08-19｜E0-anyv2v-w1-v01 50 候选批量完成与验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-19（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）

**实验 ID**

- `E0-anyv2v-w1-v01`

**行动与关键配置**

- 单实例批量跑完：`completed: 50/50 succeeded; cache hits: 0`。
- 依次执行 `w1 verify --expected 50`、`w1 reward --backend mock`、`w1 report`。

**结果**

- `verify`：`{"valid": true, "count": 50, "errors": {}}`，全部候选满足文件/校验和/16 帧/512×512/8fps。
- `reward`：50 条 mock 记录，`research measurements: 0`（非研究测量）。
- `report`：生成 `W1_REPORT.md`。
- 运行统计：50/50 succeeded；候选总 runtime 206.9 min，单候选平均 248.3 s；峰值显存 22476 MB（约 22 GB，`_peak_vram_mb` 已捕获到 nvidia-smi 输出）。
- 代码版本：`code_snapshot=4a46a8c…`（非补丁 dict_file 路径）。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/candidates.json`（50）
- `/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/rewards.json`（50 mock）
- `/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/report/W1_REPORT.md`

**观察与结论**

- W1 真实 AnyV2V 50 候选全量链路完成，E0 pipeline 阶段达标；此前 smoke 双重复门 + 非补丁 dict_file 修复均验证有效。
- 批量总计约 3.4 小时，单实例无并发，断点续跑机制无需触发。

**问题 / 失败**

- 无。

**下一步**

1. 进入 E1（judge 可靠性）：实现基于 rubric 的四维 judge 与成对判断、位置去偏、置信过滤；先在小样本人评上校准，达到 70% 准确率/85% 换位一致率门槛后再进入 Best-of-N。

### 2026-08-19｜E0-anyv2v-w1-v01 50 候选批量单实例重启

**状态：RUNNING**

**时间与环境**

- 启动时间：2026-08-19 08:15（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）

**实验 ID**

- `E0-anyv2v-w1-v01`

**行动与关键配置**

- 清空并发污染后，以单实例、全新 `cache.sqlite3` 重启 50 候选批量（命令同启动记录，`> /tmp/run-w1.log 2>&1 &`）。
- 启动时确认仅 1 个 `w1 run` 进程 + 1 个 inversion 子进程（无上次双实例并发），从 `bear-white` inversion 开始。

**结果**

- 运行中；首个 inversion `bear-white` 正常推进（seed 8888，500 步）。
- 暂无 `completed:` 最终行（需全部 50 候选完成后才打印）。

**问题 / 失败**

- 无。

**下一步**

1. 等待 `completed: 50/50 succeeded`。
2. `w1 verify --expected 50` → mock reward → report。

### 2026-08-17｜E0-anyv2v-w1-v01 并发启动排障与工作区清理

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**实验 ID**

- `E0-anyv2v-w1-v01`

**行动与关键配置**

- 发现 50 候选批量命令被误执行了**两次**（job [2]/[3] 同时指向同一 `experiment-dir` 与 `cache.sqlite3`），两个 `w1 run` 并发争用共享 `bear-white`/`bus-red` inversion 目录与同一 cache，出现竞态。
- 观察到 cache 中 `bear-white` 5 个 seed 全部 `failed`（PnP `exit status 1`）、`bus-red-s101` 卡 `running`；`bear-white` latents 500 个但由两进程交错写入不自洽，`bus-red` 仅 318 个（残缺）。
- 处置：`kill` 全部残留 `w1 run`/`run_group_*` 进程并清空半成品 `anyv2v_data/inversions`、`candidates/`、`cache.sqlite3*`，仅保留 `plan.json` 与 `anyv2v_data/demo` 源数据。

**结果**

- 确认无残留进程；`E0-anyv2v-w1-v01` 目录仅剩 `plan.json` 与 `demo` 源数据，可干净单实例重启。

**问题 / 失败**

- 手动批量命令重复粘贴导致双实例并发，共享 inversion/cache 无进程级互斥，是本次竞态根因；批量作业必须保证单实例。

**下一步**

1. 以单实例、全新 `cache.sqlite3` 重新跑 50 候选批量（重跑同一命令不再双开）。
2. 完成后 `w1 verify --expected 50`、mock reward、report。

### 2026-08-17｜dict_file 路径单候选真实 GPU 复验通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）

**实验 ID**

- `E0-anyv2v-smoke-v01`（run-c 复验）

**行动与关键配置**

- 重构后以重建的 `smoke-plan.json`（`code_snapshot=4a46a8c…`）在全新 `run-c` 目录跑单候选 `bear-white-s101`，验证 adapter 新 `--dict_file` 路径。

**结果**

- `completed: 1/1 succeeded; cache hits: 1`，`status=succeeded`、`frames=16`、`error=None`。
- `code_snapshot=4a46a8c1127cf8b32628e4aa6db85a6dc5677ccf`、`anyv2v_commit=e23629bd…`，与重建计划一致。
- 证明非补丁 dict_file 首帧编辑路径在真实链路有效，外部 AnyV2V 无需任何补丁。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-c/candidates.json`

**问题 / 失败**

- 无。

**下一步**

1. 启动 `E0-anyv2v-w1-v01` 50 候选批量。

### 2026-08-17｜E0-anyv2v-w1-v01 50 候选批量启动记录

**状态：RUNNING**

**时间与环境**

- 启动时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）
- GPU 环境：`/DATA/DATA4/hfy/envs/anyv2v-cu118`；控制环境：`/DATA/DATA4/hfy/envs/w1-control`

**实验 ID**

- `E0-anyv2v-w1-v01`

**目标**

- 对全量 50 候选执行真实 AnyV2V 生成，先单候选复验 dict_file 首帧编辑路径，再批量恒等续跑，最终 `w1 verify --expected 50` 达到 50/50。

**环境与输入**

- Git commit / 代码版本：`4a46a8c`（`Drive edit_image via dict_file path (non-patch fix)`）
- 全量计划：`/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/plan.json`（10 inversions / 50 candidates，`code_snapshot=4a46a8c…`）
- 数据 split：DAVIS-2017 train，10 输入 × 5 seeds（101/202/303/404/505）
- 模型/checkpoint：与 smoke 一致（i2vgen-xl `39e1979e…`、instruct-pix2pix `31519b5c…`、AnyV2V `e23629bd…`）
- 协议：512×512 / 16 帧 / 8 fps，inversion 500 / PnP 50 / CFG 9

**命令或关键配置**

```text
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
w1 run --backend anyv2v \
  --plan /DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/plan.json \
  --experiment-dir /DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01 \
  --cache /DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/cache.sqlite3 \
  --anyv2v-root /DATA/DATA4/hfy/external/AnyV2V \
  --python-executable /DATA/DATA4/hfy/envs/anyv2v-cu118/bin/python
```

- 先以重建后的 `smoke-plan.json` 在 run-b 复用 inversion 做单候选 dict_file 复验（约 80s），确认无 `NameError`。
- 复验通过后，对 50 候选批量按同一命令恒等续跑；中断后重跑同一命令，cache 跳过 succeeded、共享 inversion 复用、失败项自动重试。

**结果**

- 待执行。

**观察与结论**

- 无。

**问题 / 失败**

- 无。

**下一步**

1. 单候选 dict_file 复验（run-b 复用 inversion）。
2. 50 候选批量，`verify --expected 50`，然后 mock reward + report。

### 2026-08-17｜非补丁式重构：adapter 改用 dict_file 调用官方 edit_image.py

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**步骤 ID**

- `SERVER-anyv2v-dictfile-refactor-v01`

**行动与关键配置**

- 将第 3 步对官方 `AnyV2V/edit_image.py` 的补丁式修复改为非补丁方案：adapter 不再走有 bug 的 `--video_path/--output_dir` 路径，改用官方正常的 `--dict_file` 路径。
- 在 `src/w1_pipeline/backends.py` 生成 `edit-dict.json`：
  `{ "<sample_id>.mp4": [ {"image_model": "instructpix2pix", "instruction": <instruction>, "target_caption": <target_caption>} ] }`，
  并以 `--input_dir <demo_dir> --output_dir <edited_first_frame_dir> --dict_file <edit-dict.json> --seed <seed> --force_512` 调用。
- 回滚外部补丁：`git -C .../AnyV2V checkout -- edit_image.py`，恢复 pinned commit `e23629bd` 纯净（仅剩软链目录 untracked）。
- 新增回归测试 `test_edit_image_driven_via_dict_file_path`，断言 adapter 使用 `--dict_file` / `--input_dir` / `"image_model": "instructpix2pix"`。

**结果**

- `pytest` 19/19 通过。
- 官方输出文件名仍为 `<output_dir>/<instruction>.png`（dict_file 路径 prompt=instruction），与 adapter 下游 `generated_first_frame` 期望一致，PnP 无需改动。

**产物路径**

- 修复文件：`src/w1_pipeline/backends.py`
- 回归测试：`tests/test_anyv2v_adapter.py`

**问题 / 失败**

- 无。

**下一步**

1. 用新的 dict_file 路径对单候选做一次真实 GPU 快速复验（复用已算 inversion 亦可，或 run-c 全链路）。
2. 复验通过后启动 `E0-anyv2v-w1-v01` 50 候选批量。

### 2026-08-17｜E0-anyv2v-smoke-v01 双重复逐帧门通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）
- GPU 环境：`/DATA/DATA4/hfy/envs/anyv2v-cu118`；控制环境：`/DATA/DATA4/hfy/envs/w1-control`

**实验 ID**

- `E0-anyv2v-smoke-v01`

**行动与关键配置**

- 先修复官方 `AnyV2V/edit_image.py` 的 `video_filename` 未定义（见上一条记录），AnyV2V HEAD 保持 `e23629bd` 未变。
- run-a 复用已完成的 500 步 inversion latents，重跑首帧编辑 + PnP；run-b 在全新目录/缓存从头完整生成（inversion + edit + PnP）。
- 命令与前置记录一致：`--backend anyv2v`，离线开关 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`，512×512/16帧/8fps、inversion 500 / PnP 50 / CFG 9，seed 101。

**结果**

- run-a：`completed: 1/1 succeeded`，`runtime_seconds=81.5`（复用 inversion）。
- run-b：`completed: 1/1 succeeded`，`runtime_seconds=289.5`（全链路，含 inversion）。
- 逐帧复现校验（`w1 verify --expected 1 --compare`）：
  ```json
  {"valid": true, "count": 1, "errors": {}, "reproducible": true}
  ```
- 两次 16 帧 SHA-256 完全一致 ⇒ 单候选真实 AnyV2V 复现门通过。

**观察与结论**

- `peak_vram_mb=0.0` 为 `_peak_vram_mb()` 在测量时刻未捕获到进程（`nvidia-smi --query-compute-apps` 无输出）的占位值，非真实峰值；后续批量作业应在推理进行中采样记录峰值显存。
- 首次真实链路已跑通，AnyV2V 双模型加载、离线软链解析、invert/edit/PnP 产物采集与逐帧校验全部验证，具备进入 50 候选批量的条件。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-a/candidates.json`
- `/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-b/candidates.json`

**问题 / 失败**

- 无（edit_image.py 修复已单独记录）。

**下一步**

1. 进入 `E0-anyv2v-w1-v01`：对全量 50 候选逐个生成（复用共享 inversion，每 seed 一次首帧编辑 + PnP），断点续跑。
2. 完成后 `w1 verify --expected 50`（不需 compare），并跑 mock reward + report。

### 2026-08-17｜修复官方 AnyV2V edit_image.py 的 video_filename 未定义

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**步骤 ID**

- `SERVER-anyv2v-editimage-fix-v01`

**行动与关键配置**

- run-a 在 inversion 完成后、调用官方 `edit_image.py` 时于第 145 行触发 `NameError: name 'video_filename' is not defined`，随后 `completed: 0/1 succeeded`。
- 根因：`edit_image.py` 的 `__main__` 非 dict_file 分支中，`video_filename` 只在 `args.output_dir is None` 时定义；本 adapter 显式传入 `--output_dir`，走 `else` 分支后 `video_filename` 未定义，却被无条件 `print` 引用。
- 最小修复：在非 dict_file 分支无条件先 `video_filename = os.path.basename(video_path)`，保持其余行为不变。

**结果**

- 修复后 `python -m py_compile edit_image.py` 通过。
- AnyV2V 本地 HEAD 仍为 `e23629bde607183b8e7afd9a853d6e5ec756b8d9`（未提交，working tree 含 `edit_image.py` 修改与软链目录），`_checkout()` 的 commit 校验不受影响。
- run-a 的 inversion latents 完整（`t=999` 已保存），重跑将复用 inversion，仅重跑首帧编辑与 PnP。

**产物路径**

- 修复文件：`/DATA/DATA4/hfy/external/AnyV2V/edit_image.py`

**问题 / 失败**

- 官方脚本在「显式传 output_dir」路径存在遗留 debug 打印 bug，首次真实链路运行才暴露（本地 mock 不覆盖）。

**下一步**

1. 重跑 run-a（复用 inversion），随后 run-b，再 `w1 verify --compare`。

### 2026-08-17｜E0-anyv2v-smoke-v01 启动记录（真实 GPU 双重复门）

**状态：RUNNING**

**时间与环境**

- 启动时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，RTX A6000）
- GPU 环境：`/DATA/DATA4/hfy/envs/anyv2v-cu118`（torch 2.1.2+cu118，CUDA 11.8）
- 控制环境：`/DATA/DATA4/hfy/envs/w1-control`

**实验 ID**

- `E0-anyv2v-smoke-v01`

**目标**

- 对单候选 `bear-white-s101` 执行两次独立真实 AnyV2V 生成，逐帧比较 16 帧 SHA-256，作为 50 候选批量（`E0-anyv2v-w1-v01`）的复现放行门。

**环境与输入**

- Git commit / 代码版本：`90a4c93`（`Record W1 candidate and smoke plan generation`）
- smoke 计划：`/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/smoke-plan.json`（`inv-bear-white` + `bear-white-s101`）
- 模型与 checkpoint：
  - I2VGen-XL：`ali-vilab/i2vgen-xl` revision `39e1979ea27be737b0278c06755e321f2b4360d5`（fp16）
  - InstructPix2Pix：`timbrooks/instruct-pix2pix` revision `31519b5cb02a7fd89b906d88731cd4d6a7bbf88d`
  - AnyV2V：本地固化 HEAD `e23629bde607183b8e7afd9a853d6e5ec756b8d9`（计划内 `anyv2v_commit`）
- 数据 split / 样本数：DAVIS-2017 train，样本 `bear-white`，seed `101`
- 随机种子：`101`

**命令或关键配置**

- 推理协议：512×512、16 帧、8 fps；DDIM inversion 500 步、PnP 50 步、CFG 9、`ddim_init_latents_t_idx=0`。
- 离线开关：`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`（模型经 AnyV2V 源码内软链解析）。

```text
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
w1 run --backend anyv2v \
  --plan /DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/smoke-plan.json \
  --experiment-dir /DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-a \
  --cache /DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-a/cache.sqlite3 \
  --anyv2v-root /DATA/DATA4/hfy/external/AnyV2V \
  --python-executable /DATA/DATA4/hfy/envs/anyv2v-cu118/bin/python
```

- run-b 使用独立 `--experiment-dir .../run-b` 与 `--cache .../run-b/cache.sqlite3`，其余参数相同。
- 校验：`w1 verify --expected 1 --candidates run-a/candidates.json --compare run-b/candidates.json`。

**结果**

- 待执行。

**观察与结论**

- 无。

**问题 / 失败**

- 无。

**下一步**

1. 依次执行 run-a、run-b。
2. 对两次结果执行 `verify --compare`；逐帧一致（`reproducible=true`）即放行，否则如实记录并评估处理。

### 2026-08-17｜W1 候选计划与单候选 smoke 计划生成

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）
- 控制环境：`/DATA/DATA4/hfy/envs/w1-control`

**实验 ID**

- `E0-anyv2v-plan-v01`

**行动与关键配置**

- 复核 AnyV2V 本地固化 HEAD = `e23629bde607183b8e7afd9a853d6e5ec756b8d9`，仓库 FAVOR-Edit HEAD = `8bd8657`（clean）。
- 执行 `w1 plan --backend anyv2v`，`--model-commit 39e1979ea27be737b0278c06755e321f2b4360d5`（I2VGen-XL revision）、`--anyv2v-commit e23629bde607183b8e7afd9a853d6e5ec756b8d9`。
- 执行 `scripts/make_smoke_plan.py` 生成单候选 smoke plan。

**结果**

- 全量计划：`planned 10 inversions and 50 candidates`。
- 单候选 smoke plan：1 个 inversion `inv-bear-white` + 1 个 candidate `bear-white-s101`。
- 计划内 `code_snapshot=8bd8657667f417da20cc43ac71bb65dc82493cfa`（无 `-dirty`）。
- 计划内 `config.anyv2v_commit=e23629bde607183b8e7afd9a853d6e5ec756b8d9`、`config.model_commit=39e1979ea27be737b0278c06755e321f2b4360d5`。

**产物路径**

- `/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01/plan.json`（50 candidates）
- `/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/smoke-plan.json`（1 candidate）

**观察与结论**

- 计划阶段完成，40 字符 commit 校验通过，smoke 候选固定为 `bear-white-s101`（seed 101）。
- 产物按实验 ID 独立目录分布，与 AGENTS.md 的“不可覆盖/唯一目录”约定一致。

**问题 / 失败**

- 无。

**下一步**

1. 按 AGENTS.md 在启动真实 GPU 前追加 `E0-anyv2v-smoke-v01` 的完整命令与资源估计记录。
2. 两个独立目录各跑一次单候选 smoke，逐帧校验 16 帧 SHA-256，通过后进入 `E0-anyv2v-w1-v01`。

### 2026-08-17｜服务器 DAVIS 预处理与 W1 清单校验

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）
- 控制环境：`/DATA/DATA4/hfy/envs/w1-control`（`w1` v0.1.0，editable 指向 `/home/sunyinan/FAVOR-Edit/src`）

**步骤 ID**

- `SERVER-w1-prepare-v01`

**行动与关键配置**

- 提交未提交的 08-13 服务器记录（`cf3409d`），确认 `w1_pipeline` 经 editable install 解析到 `/home/sunyinan/FAVOR-Edit/src/w1_pipeline`。
- 执行 `w1 prepare --davis-root /DATA/DATA4/hfy/data/DAVIS --output-dir /DATA/DATA4/hfy/w1-workspace/prepared/w1`。
- 执行 `w1 validate --prepared /DATA/DATA4/hfy/w1-workspace/prepared/w1/manifest.json`。

**结果**

- `prepare` → 10 inputs；`validate` → `source manifest valid: 10 inputs, 5 seeds`、`prepared manifest valid: 10 inputs`。
- 每输入 16 帧 PNG + 16 mask PNG + 1 个 `source.mp4`；全部帧/mask/video 逐样本对齐一致。
- 媒体协议复检：10 个输入首帧均为 512×512，`source.mp4` 均为 8 fps。

| sample_id | frames | masks | video | size | fps |
| --- | --- | --- | --- | --- | --- |
| bear-white | 16 | 16 | 1 | 512×512 | 8 |
| bus-red | 16 | 16 | 1 | 512×512 | 8 |
| elephant-pink | 16 | 16 | 1 | 512×512 | 8 |
| classic-car-blue | 16 | 16 | 1 | 512×512 | 8 |
| dog-tiger | 16 | 16 | 1 | 512×512 | 8 |
| horse-zebra | 16 | 16 | 1 | 512×512 | 8 |
| mallard-swan | 16 | 16 | 1 | 512×512 | 8 |
| hiker-backpack | 16 | 16 | 1 | 512×512 | 8 |
| rider-helmet | 16 | 16 | 1 | 512×512 | 8 |
| car-headlights | 16 | 16 | 1 | 512×512 | 8 |

**产物路径**

- `/DATA/DATA4/hfy/w1-workspace/prepared/w1/`（10 个 sample 目录 + `manifest.json`）

**观察与结论**

- 数据预处理链路在服务器上首次真实通过，10 输入全部符合 W1 协议（16 帧/512×512/8fps + checksum）。
- 前置障碍已清除，可进入真实 AnyV2V 计划与 smoke。

**问题 / 失败**

- 无。

**下一步**

1. 生成 50 候选全量计划（`w1 plan --backend anyv2v`，填入真实 AnyV2V/model commit）。
2. 用 `scripts/make_smoke_plan.py` 生成单候选 smoke plan。
3. 执行 `E0-anyv2v-smoke-v01` 双重复逐帧复现门。

### 2026-08-17｜E0-anyv2v-smoke-v01 真实 GPU smoke 前置记录

**状态：RUNNING（前置记录；smoke 尚未执行）**

**时间与环境**

- 记录时间：2026-08-17（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，6×RTX A6000）

**实验 ID**

- `E0-anyv2v-smoke-v01`

**目标**

- 在真实 AnyV2V（I2VGen-XL inversion + InstructPix2Pix + PnP）链路上跑通单候选，并用两次独立运行的 16 帧逐帧 SHA-256 校验复现性，作为 50 候选批量（`E0-anyv2v-w1-v01`）的放行门。

**环境与输入**

- Git commit / 代码版本：`cf3409d`（`Record A6000 env setup, model download, AnyV2V pin and DAVIS prep`）
- 模型与 checkpoint：
  - I2VGen-XL：`ali-vilab/i2vgen-xl`，revision `39e1979ea27be737b0278c06755e321f2b4360d5`（fp16 variant，4.7G）
  - InstructPix2Pix：`timbrooks/instruct-pix2pix`，revision `31519b5cb02a7fd89b906d88731cd4d6a7bbf88d`（4.0G）
  - AnyV2V：upstream `bc540befacafddb9689ee86a396e7738bfed0e4f`，本地固化 HEAD `e23629bde607183b8e7afd9a853d6e5ec756b8d9`
- 数据 split / 样本数：DAVIS-2017 train，10 输入，种子 `101/202/303/404/505`（smoke 仅取 1 个单候选）
- GPU / CUDA：RTX A6000，CUDA 11.8（env `anyv2v-cu118`，torch 2.1.2+cu118）
- 随机种子：smoke 候选沿用计划内固定 seed

**命令或关键配置**

- 本步骤不执行 smoke 推理；仅记录即将使用的真实推理配置与前序 prepare 依赖。
- 推理协议：512×512、16 帧、8 fps；DDIM inversion 500 步、PnP 50 步、CFG 9。
- 离线开关：`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`；模型经 AnyV2V 源码内软链解析。
- 预期 smoke 命令（prepare/plan 完成后执行）：

```text
w1 run --backend anyv2v --plan <smoke-plan> \
  --experiment-dir /DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-a \
  --cache /DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/run-a/cache.sqlite3 \
  --anyv2v-root /DATA/DATA4/hfy/external/AnyV2V \
  --python-executable /DATA/DATA4/hfy/envs/anyv2v-cu118/bin/python
```

- 产物目录：`/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01/`（唯一，不可覆盖）

**结果**

- 待执行；前置依赖为 `w1 prepare` + `w1 validate`（10 输入）通过后生成单候选 smoke plan。

**观察与结论**

- 无（尚未执行推理）。

**问题 / 失败**

- 无。

**下一步**

1. 服务器执行 `w1 prepare`（`--davis-root /DATA/DATA4/hfy/data/DAVIS`）并 `w1 validate --prepared`。
2. 生成 50 候选全量计划与单候选 smoke plan。
3. 两次独立运行单候选，逐帧校验 16 帧 SHA-256，再进入 `E0-anyv2v-w1-v01`。

### 2026-08-13｜DAVIS-2017 数据下载与选择性解压

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 21:51（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**步骤 ID**

- `SERVER-davis-v01`

**行动与关键配置**

- 源：官方 ETH `https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip`（832,766,765 字节）。
- 下载经 `curl -C -` 断点续传（脚本 `scripts/prepare_davis.sh`）。
- 排障：zip 内部有顶层目录 `DAVIS/`，首次解压通配缺少该前缀致 0 文件；改用 `scripts/extract_davis.sh` 按 `DAVIS/JPEGImages/480p/<seq>/*` 与 `DAVIS/Annotations/480p/<seq>/*` 正确解压。

**结果**

- 10 条序列逐序列帧/掩码数一致（均 ≥48，满足预处理要求）：

| seq | frames | masks |
| --- | --- | --- |
| bear | 82 | 82 |
| bus | 80 | 80 |
| elephant | 80 | 80 |
| classic-car | 63 | 63 |
| dog-gooses | 86 | 86 |
| horsejump-low | 60 | 60 |
| mallard-water | 80 | 80 |
| hike | 80 | 80 |
| scooter-gray | 75 | 75 |
| drift-turn | 64 | 64 |

**产物路径**

- `/DATA/DATA4/hfy/data/DAVIS/JPEGImages/480p/<seq>`
- `/DATA/DATA4/hfy/data/DAVIS/Annotations/480p/<seq>`
- `/DATA/DATA4/hfy/data/DAVIS-2017-trainval-480p.zip`

**下一步**

1. 服务器跑 `w1 prepare --davis-root /DATA/DATA4/hfy/data/DAVIS`，再 `w1 validate --prepared`。
2. 通过后生成 50 候选计划与单候选 smoke 计划，进入 `E0-anyv2v-smoke-v01`。

### 2026-08-13｜模型离线软链与调度器加载自检

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 19:08（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**步骤 ID**

- `SERVER-model-symlink-v01`

**行动与关键配置**

- 在 AnyV2V 源码中建立模型相对 ID 的软链：
  - `AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl -> /DATA/DATA4/hfy/models/i2vgen-xl`
  - `AnyV2V/timbrooks/instruct-pix2pix -> /DATA/DATA4/hfy/models/instruct-pix2pix`
- 设 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`，用 GPU 环境只加载调度器配置（不加载完整权重）验证相对路径解析：
  - `DDIMScheduler.from_pretrained("ali-vilab/i2vgen-xl", subfolder="scheduler", local_files_only=True)` → OK
  - `EulerAncestralDiscreteScheduler.from_pretrained("timbrooks/instruct-pix2pix", subfolder="scheduler", local_files_only=True)` → OK

**结果**

- 两模型 `model_index.json` 经软链可解析；离线开关下无网络请求即成功，证明本地 snapshot 完整。

**产物路径**

- 软链：`/DATA/DATA4/hfy/external/AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl`、`/DATA/DATA4/hfy/external/AnyV2V/timbrooks/instruct-pix2pix`

**下一步**

1. 准备 10 条 DAVIS 序列并在服务器重跑 `w1 prepare`。
2. 完成后进入 `E0-anyv2v-smoke-v01` 单候选真实 GPU 复现门。

### 2026-08-13｜两个模型 snapshot 下载完成（经 hf-mirror）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 19:07（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`）

**步骤 ID**

- `SERVER-models-v01`

**行动与关键配置**

- `ali-vilab/i2vgen-xl`（revision `39e1979ea27be737b0278c06755e321f2b4360d5`）：按 `variant="fp16"` 下载 fp16 safetensors 五组件 + scheduler/tokenizer/feature_extractor/config，完整 4.7G。
- `timbrooks/instruct-pix2pix`（revision `31519b5cb02a7fd89b906d88731cd4d6a7bbf88d`）：标准 Diffusers snapshot（safety_checker=None 时不加载），text_encoder 492M / vae 335M / unet 3.44G，完整 4.0G。
- 关键排障：`huggingface_hub 0.20.3` 在 **import 时**捕获 `HF_HOME`/`HF_HUB_CACHE`/`HF_ENDPOINT`，必须把这些环境变量放在 `import huggingface_hub` **之前**设置，并指向 `https://hf-mirror.com` 与 `/DATA/DATA4/hfy/caches/hf`，否则缓存落满根盘 `/`（0 字节可用）且端点落到被墙的 `huggingface.co`。
- 最终改用 `curl -C -` 断点续传 + `.part` 原子改名（脚本 `scripts/download_missing.sh`），`setsid nohup` 后台防杀，直接写入 DATA4 目标路径，跳过 byte 级校验已完成的文件。

**结果**

- 两模型 `model_index.json` 齐全；i2vgen-xl 4.7G、instruct-pix2pix 4.0G。
- 所有大权重字节数与 hf-mirror 返回的 `content-length` 一致。

**产物路径**

- `/DATA/DATA4/hfy/models/i2vgen-xl`
- `/DATA/DATA4/hfy/models/instruct-pix2pix`
- 下载脚本：`/DATA/DATA4/hfy/scripts/download_models.py`、`download_missing.sh`、`download_models_curl.sh`

**下一步**

1. 在 `AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl` 与 `AnyV2V/timbrooks/instruct-pix2pix` 建软链并设 `HF_HUB_OFFLINE=1` 做只加载配置的自检。
2. 准备 10 条 DAVIS 数据并在服务器重跑 `w1 prepare`。

### 2026-08-13｜AnyV2V 源码固化（GitHub git 对象传输被限流，改用 codeload 快照）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 13:20（Asia/Shanghai）
- 执行位置：学校 A6000 服务器

**步骤 ID**

- `SERVER-anyv2v-source-v01`

**行动与关键配置**

- 尝试 `git clone https://github.com/TIGER-AI-Lab/AnyV2V.git` 多次失败：`GnuTLS recv error (-110)`、`Operation too slow`（git 智能 HTTP 对象传输到 github.com 被限流，停在约 112KB）。
- 改用 `codeload.github.com` 下载精确 commit tarball：`https://codeload.github.com/TIGER-AI-Lab/AnyV2V/tar.gz/bc540befacafddb9689ee86a396e7738bfed0e4f`（91MB）。
- 解压到 `/DATA/DATA4/hfy/external/AnyV2V`，`git init` + 全量 commit 生成本地可定位 HEAD，变成本地可 `git rev-parse HEAD` 的可追溯快照。
- 已确认关键入口存在：`edit_image.py`、`i2vgen-xl/run_group_ddim_inversion.py`、`i2vgen-xl/run_group_pnp_edit.py`。

**结果**

- upstream 精确 commit：`bc540befacafddb9689ee86a396e7738bfed0e4f`（2024-10-29）。
- 本地固化 HEAD：`e23629bde607183b8e7afd9a853d6e5ec756b8d9`，`git status` clean。
- 模型加载方式确认：
  - I2VGen-XL：`I2VGenXLPipeline.from_pretrained("ali-vilab/i2vgen-xl", torch_dtype=fp16, variant="fp16")` + `DDIM( Inverse)Scheduler.from_pretrained(..., subfolder="scheduler")` → 需要 fp16 variant 权重 + `scheduler` 子目录。
  - InstructPix2Pix：`StableDiffusionInstructPix2PixPipeline.from_pretrained("timbrooks/instruct-pix2pix", safety_checker=None)` → 标准 Diffusers snapshot。

**产物路径**

- `/DATA/DATA4/hfy/external/AnyV2V`（源码快照 + 本地 git）
- 下载缓存 `/DATA/DATA4/hfy/external/anyv2v.tar.gz`

**下一步**

1. 经 hf-mirror 下载 `ali-vilab/i2vgen-xl`（含 fp16 variant）与 `timbrooks/instruct-pix2pix` 两个 Diffusers snapshot。
2. 建 `AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl` 与 `AnyV2V/timbrooks/instruct-pix2pix` 软链，设离线开关验证加载。

### 2026-08-13｜服务器两个 conda 环境建立（控制 + AnyV2V GPU）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 12:22（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（`ps`，6×RTX A6000）
- 网络：走清华 PyPI 镜像 + 官方 `download.pytorch.org/whl/cu118`

**步骤 ID**

- `SERVER-envs-v01`

**行动与关键配置**

- 控制环境 `/DATA/DATA4/hfy/envs/w1-control`（Python 3.11）：安装 pydantic 2.13.4、typer、pyyaml、imageio/imageio-ffmpeg、pillow、numpy、pytest 8.4.2、hatchling；`pip install --no-deps -e ~/FAVOR-Edit`。`pytest` 18/18 通过，`w1` 全部命令可见。
- GPU 环境 `/DATA/DATA4/hfy/envs/anyv2v-cu118`（Python 3.9.25）：`torch==2.1.2+cu118`、`torchvision==0.16.2+cu118`，再固定 `diffusers==0.26.3`、`transformers==4.37.2`、`accelerate==0.27.2`、`huggingface_hub==0.20.3`、numpy 1.26.4、omegaconf、opencv-python-headless、moviepy 1.0.3、imageio/imageio-ffmpeg、safetensors。
- 关键排障：首次 torch 安装报 `[Errno 28] No space left on device`，根因是 pip 仍用已满根盘 `/tmp` 作下载暂存；设置 `TMPDIR=/DATA/DATA4/hfy/tmp` 后重装成功。torch 2.1.2 又被 pip 拉到 numpy 2.0.2 触发 NumPy 1.x ABI 报错，再降级 `numpy<2`(1.26.4) 解决。
- 全程设置 `CONDA_PKGS_DIRS` 与 `PIP_CACHE_DIR` 指向 DATA4，避免写满根盘。

**结果**

- GPU 环境自检：`torch 2.1.2+cu118 cuda 11.8 avail True`、`diffusers 0.26.3`、`transformers 4.37.2`、`accelerate 0.27.2`、`hf_hub 0.20.3`、`cv2 4.11.0`、`GPU NVIDIA RTX A6000`。
- 控制环境 `w1` 命令与 18 项测试全部可用。

**产物路径**

- `/DATA/DATA4/hfy/envs/w1-control`
- `/DATA/DATA4/hfy/envs/anyv2v-cu118`
- 缓存：`/DATA/DATA4/hfy/caches/{conda-pkgs,pip}`、临时目录 `/DATA/DATA4/hfy/tmp`

**下一步**

1. 克隆官方 AnyV2V 并记录 40 位 HEAD SHA 作为 pinned commit。
2. 经 hf-mirror 下载 `ali-vilab/i2vgen-xl` 与 `timbrooks/instruct-pix2pix` 两个 Diffusers snapshot，建离线软链。

### 2026-08-13｜学校服务器工作区建立（改用 DATA4）

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-13 12:04（Asia/Shanghai）
- 执行位置：学校 A6000 服务器（Ubuntu 20.04.6，6×RTX A6000，192 核，503GB）
- 主机：`ps`

**步骤 ID**

- `SERVER-workspace-setup-v01`

**行动与关键配置**

- 先探测全部大容量盘健康度，发现 `/DATA/DATA2`（`/dev/sdf`）出现硬件 I/O 错误：`dmesg` 报 `blk_update_request: I/O error`、`lost sync page write`、`EXT4-fs error while writing superblock`，`ls /DATA/DATA2` 返回 `Input/output error`，不可用。
- 原计划使用 DATA2，经确认改为使用健康且可写的 `/DATA/DATA4`。
- 建立工作区 `/DATA/DATA4/hfy/` 及子目录 `w1-workspace models envs data/DAVIS caches/conda-pkgs caches/pip`。
- 命令：`mkdir -p` 各子目录；`touch .wtest` 写测试；`df -h /DATA/DATA4`。

**结果**

- 工作区目录创建成功，写测试通过；`/DATA/DATA4` 剩余 761G（95% 已用，总体健康可写）。
- 根盘 `/` 仍满（2.8G free），按用户指示暂不删除 home 下大文件，所有工程数据均放 DATA4。
- 网络结论：GitHub、PyPI、download.pytorch.org、hf-mirror.com、modelscope.cn 可达；huggingface.co DNS 被阻断。

**产物路径**

- `/DATA/DATA4/hfy/`（含 `w1-workspace models envs data/DAVIS caches/conda-pkgs caches/pip`）

**下一步**

1. 创建控制环境与 AnyV2V GPU conda 环境（放 `/DATA/DATA4/hfy/envs`），缓存目录指向 DATA4。
2. 克隆并 pin AnyV2V，经 hf-mirror 下载两个模型 snapshot。

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

### 2026-08-13｜GitHub 首次推送完成

**状态：DONE**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- GitHub 仓库：`https://github.com/riiiveeer/FAVOR-Edit.git`

**步骤 ID**

- `LOCAL-github-initial-push-v01`

**操作与关键配置**

- 在提交 `2ada91f` 上执行 `git push -u origin main`；
- 将本地 `main` 设置为跟踪 `origin/main`。

**结果与产物**

- GitHub 成功创建远端 `main` 分支；
- 项目代码、配置、测试、文档与截至本步骤前的 DEVLOG 已推送；
- 远端地址：`https://github.com/riiiveeer/FAVOR-Edit.git`。

**问题 / 失败**

- 无。

**下一步**

1. 提交并推送本条日志；
2. 核对本地 `HEAD` 与 `origin/main` 一致；
3. 在学校服务器克隆该仓库并运行离线预检。

---

### 2026-08-13｜项目级 GitHub 直连配置完成

**状态：DONE**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远端：`origin = https://github.com/riiiveeer/FAVOR-Edit.git`

**步骤 ID**

- `LOCAL-github-proxy-override-v03`

**操作与关键配置**

- 从 `.git/config` 删除带单个空格的无效重复代理项；
- 保留仓库级空 `http.proxy` 与 `https.proxy`，覆盖失效的用户级代理但不修改全局配置；
- 使用普通 `git ls-remote origin` 验证，无需命令级 `-c` 参数。

**结果与产物**

- GitHub HTTPS 直连成功；
- 远端无 refs，确认仓库仍为空；
- 本地分支 `main`、工作区 clean；
- 本地专用配置位于 `D:\lab idea\.git\config`（该文件不进入提交）。

**问题 / 失败**

- 无。

**下一步**

1. 提交本条记录；
2. 首次推送本地 `main` 至 `origin` 并设置 upstream。

---

### 2026-08-13｜仓库级代理重复项诊断

**状态：BLOCKED**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`

**步骤 ID**

- `LOCAL-github-proxy-override-v02`

**操作与关键配置**

- 在 `.git/config` 中新增真正的空 `http.proxy` 与 `https.proxy`；
- 使用 `git config --local --get-regexp` 和 `git ls-remote origin` 验证。

**结果与产物**

- 发现此前写入的空格代理配置作为重复 section 仍然存在；
- Git 同时读取空值和空格值，最终仍因空格值的畸形 URL 报错；
- 未执行 push。

**问题 / 失败**

- `.git/config` 中存在两组 `[http]` / `[https]` proxy 项，需要精确删除 `proxy = " "` 的重复项。

**下一步**

1. 移除带空格的重复代理 section；
2. 保留真正空值并再次验证远端。

---

### 2026-08-13｜仓库级空代理参数第二次诊断

**状态：INVALID**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`

**步骤 ID**

- `LOCAL-github-proxy-override-v01`

**操作与关键配置**

- 尝试将仓库级 `http.proxy` 与 `https.proxy` 写为空格，以覆盖用户级失效代理；
- 运行 `git ls-remote origin` 验证。

**结果与产物**

- `.git/config` 成功写入空格值，但 Git 将其解析为代理 URL 而不是“无代理”；
- 远端检查失败：`Unsupported proxy syntax in ' ': Malformed input to a URL function`。

**问题 / 失败**

- 空格代理值是无效配置，必须移除；
- 本步骤未执行 push，GitHub 内容未改变。

**下一步**

1. 在 `.git/config` 中写入语法层面的空代理值；
2. 验证普通 `git ls-remote origin` 无需命令级覆盖即可直连。

---

### 2026-08-13｜添加 origin 与仓库级代理配置诊断

**状态：DONE**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`

**步骤 ID**

- `LOCAL-github-origin-v01`

**操作与关键配置**

- 添加远端：`git remote add origin https://github.com/riiiveeer/FAVOR-Edit.git`；
- 尝试通过 `git config --local http.proxy ""` 与 `https.proxy ""` 写入仓库级空代理覆盖；
- 检查 `.git/config` 并重新运行 `git ls-remote origin`。

**结果与产物**

- `origin` 已正确配置为 GitHub 仓库；
- PowerShell 调用 Git 时未持久化空字符串参数，`.git/config` 中没有生成代理覆盖项；
- 因而普通 `git ls-remote origin` 仍继承失效的用户级 `127.0.0.1:7890` 代理并失败；
- 产物路径：`D:\lab idea\.git\config`、`D:\lab idea\DEVLOG.md`。

**问题 / 失败**

- 组合命令末尾因查询不存在的本地代理项返回退出码 1；此前的日志提交及 `origin` 添加均已成功；
- 普通远端命令仍需显式空代理覆盖。

**下一步**

1. 直接在仓库配置中加入空代理值并验证其优先于用户级配置；
2. 推送 `main`。

---

### 2026-08-13｜GitHub 直连复查与代理隔离决策

**状态：DONE**

**时间与环境**

- 执行日期：2026-08-13（Asia/Shanghai）
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远端目标：`https://github.com/riiiveeer/FAVOR-Edit.git`

**步骤 ID**

- `LOCAL-github-probe-v02`

**操作与关键配置**

- 检查 Git、环境变量、WinHTTP 与本机监听端口的代理配置；
- 定位到用户级 `C:\Users\18531\.gitconfig` 配置了 `http.proxy` 与 `https.proxy` 为 `http://127.0.0.1:7890`，但端口未监听；
- 使用命令级空代理覆盖执行 `git -c http.proxy= -c https.proxy= ls-remote https://github.com/riiiveeer/FAVOR-Edit.git`。

**结果与产物**

- GitHub HTTPS 直连成功；
- `ls-remote` 无 refs 输出，目标仓库当前为空；
- 决定只为本项目设置仓库级空代理覆盖，保留其他项目可能依赖的全局代理设置。

**问题 / 失败**

- 全局 Git 代理当前失效，但不在本步骤中修改用户级配置。

**下一步**

1. 为本仓库配置空代理覆盖并添加 `origin`；
2. 将 `main` 首次推送至 GitHub。

---

### 2026-08-13｜GitHub 远端首次连通性探测

**状态：BLOCKED**

**时间与环境**

- 完成时间：2026-08-13 10:20:08 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远端目标：`https://github.com/riiiveeer/FAVOR-Edit.git`

**步骤 ID**

- `LOCAL-github-probe-v01`

**操作与关键配置**

- 确认本地分支为 `main`、工作区 clean、尚无 Git remote；
- 使用 `git ls-remote https://github.com/riiiveeer/FAVOR-Edit.git` 只读探测远端。

**结果与产物**

- 本地 HEAD：`f50426d`；
- 远端探测失败，Git 尝试经 `127.0.0.1` 代理连接 GitHub 443 端口，但本机代理未监听；
- 诊断信息已记录于 `D:\lab idea\DEVLOG.md`。

**问题 / 失败**

- `Failed to connect to github.com port 443 via 127.0.0.1`；
- 本步骤未添加 `origin`，也未发生外部写入。

**下一步**

1. 检查 Git、环境变量和 Windows 代理来源；
2. 使用可用网络路径重新只读探测；
3. 连通后添加 `origin` 并推送 `main`。

---

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

---

### 2026-08-24｜同步远程仓库最新提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 18:47:14 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未连接学校 A6000

**步骤 ID**

- `LOCAL-git-pull-main-20260824-v01`

**操作与关键配置**

- 在确认 `main` 分支工作区 clean、跟踪 `origin/main` 后同步远程仓库；
- 关键命令：`git status --short --branch`、`git remote -v`、`git pull --ff-only`；
- 同步前提交：`244ffa4`；同步后提交：`8d651bc`。

**结果与产物**

- `git pull --ff-only` 成功，分支以 fast-forward 方式更新；
- 新增 E0 审计实现、E1 judge 框架、E1 配置及相关测试，共 36 个文件、3951 行新增、1 行删除；
- 产物路径：`D:\lab idea`（Git 工作树），最新代码快照 `8d651bc`。

**问题 / 失败**

- 无。

**下一步**

1. 阅读项目说明、实验方案与最新 DEVLOG；
2. 核对当前实现和产物状态；
3. 据此确定下一项本地或 A6000 实验。

---

### 2026-08-24｜同步后本地全量回归诊断

**状态：BLOCKED（本地回归未通过，已获得可操作诊断）**

**时间与环境**

- 完成时间：2026-08-24 18:49:46 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码版本：`8d651bc`
- 远程环境：未使用；未连接学校 A6000

**步骤 ID**

- `LOCAL-post-pull-regression-20260824-v01`

**操作与关键配置**

- 运行同步后的全量测试；
- 关键命令：`uv run pytest -q`；
- `uv` 重新构建并以 editable 方式安装本项目，随后执行 76 项测试。

**结果**

- 结果：66 passed、4 failed、6 errors，进程退出码 1；
- 两项 E1 runner/mock E2E 失败源于 `request_id` 含冒号并被直接用作文件名，Windows 报 `OSError: [Errno 22] Invalid argument`；
- 一项 E1 packet 测试及六项 E0 audit fixture 报错源于本机 `PATH` 找不到系统 `ffmpeg`；README 虽说明 `imageio-ffmpeg` 提供固定 ffmpeg，但新增审计/packet 实现仍硬编码调用 `ffmpeg`/`ffprobe`；
- `test_build_rejects_non50_candidates` 还暴露校验顺序问题：工具检查发生在输入数量检查之前，导致预期的 50-candidate 错误被 ffmpeg 环境错误遮蔽；
- 未产生研究指标或实验产物。

**产物路径**

- 失败栈仅在本次终端输出中；涉及代码：`src/e1_judge/runner.py`、`src/e1_judge/packets.py`、`src/w1_pipeline/e0_audit.py`。

**问题 / 失败**

- 当前提交在学校 Linux 服务器记录为 76/76，但在 README 声称支持的本地 Windows 开发环境不能全量通过；
- 此结果不影响已完成的服务器 E0 研究产物，但说明跨平台本地回归门尚未满足。

**下一步**

1. 先完成 E1 真实运行就绪差距审计，区分“跨平台回归问题”和“真实 judge 协议缺口”；
2. 在进入真实 judge smoke 前修复 request 文件名、ffmpeg 解析、prompt/plan/media identity 等阻塞项，并补针对真实 command backend 的契约测试；
3. 修复后重新运行全量测试并单独记录结果。

---

### 2026-08-24｜E1 真实运行就绪差距审计与下一阶段策略

**状态：DONE（审计/决策完成；实施尚未开始）**

**时间与环境**

- 完成时间：2026-08-24 18:51:05 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码版本：`8d651bc052a73417d074489794d664f4c11244d0`
- 远程环境：未使用；未连接学校 A6000

**步骤 ID**

- `E1-real-readiness-audit-v01`

**目标**

- 对照 `proposal.md`、`idea-logic.md`、`docs/E0_AUDIT_E1_EXECUTION.md` 和最新阶段 DEVLOG，判断 E1 是否可在权重就位后直接运行，并确定 M1 前的最短可靠路径。

**行动与关键配置**

- 静态核对 `configs/e1/`、`src/e1_judge/`、`tests/e1/` 与施工手册 §7–§21；
- 核对本地回归结果 `LOCAL-post-pull-regression-20260824-v01`；
- 仅参考官方模型卡比较离线 judge 候选：Qwen2.5-VL-7B-Instruct（Apache-2.0、7B、官方说明支持长视频/结构化输出、snapshot 约 16.6GB）与 Qwen3-VL-8B-Instruct（Apache-2.0、8B、视频能力更强但官方当前建议较新的 Transformers/source 环境）。

**结果与关键缺口**

- E0 状态保持为 PASS：50/50 候选和人工粗审已完成；不得重跑或覆盖 E0。
- E1 应重新表述为：`mock scaffold complete; real-research readiness incomplete`。除了既有的真实 judge 权重和真人标注缺口，还存在以下前置工程阻塞：
  1. 四个 prompt YAML 仅含 version/schema，占位内容未实现；`src/e1_judge/prompts.py` 仍直接抛 `NotImplementedError`。
  2. 人工标注页未使用 `packets` 参数、未展示 source/A/B 视频或 contact sheet，也未按 annotator 映射显示方向；当前工具不能产生协议要求的有效真人标注。
  3. judge plan 没有 `split`，但 runner 依赖 `split` 过滤，因此真实 dev/frozen 命令会选中 0 请求；plan 还硬编码 `backend/model=mock`、占位 packet checksum，未写媒体路径、prompt checksum、code snapshot 和真实 generation 参数。
  4. absolute 请求统一取 `pairs[0]` 的 source/instruction/task，导致除首个 sample 外的候选上下文错配。
  5. runner 未生成手册约定的 `results.jsonl`，失败缓存会被当作 cache hit 而不重试；merge 也未校验 frozen prompt checksum/model revision。
  6. 分析层把同一 pair 的多方法/多方向结果折叠为第一条，无法形成四方法主表和有效 swap 统计；absolute 阈值推对、Kendall/Spearman、分维度指标、冻结集判定、`decision.json` 与 `reward-v0.yaml` 尚未贯通。
  7. 本地 Windows 另有冒号文件名和 ffmpeg 解析问题，见上一条回归记录。
- 因此“先上传模型然后直接跑 550 请求”会在 smoke 前或分析阶段失败，不是当前正确顺序。

**策略决策**

1. 下一项开发应为 `E1-real-readiness-v01`：先在本地补齐 prompt/plan/media identity、command adapter 契约、annotation UI、结果落盘/重试、四方法分析与 decision gate，并让全量测试跨平台通过。
2. 在修复期间可并行准备外部前置，但不得启动 frozen eval：
   - 模型主候选采用 **Qwen2.5-VL-7B-Instruct**，优先稳定离线部署而非追逐更新模型；下载时再锁定 exact revision、完整 snapshot、依赖 wheels、SHA256SUMS 与 MODEL_CARD_LOCAL.md；
   - 安排两名真人各自完成 100 pair，争议 pair 由第三人裁决；只有修复后的媒体标注工具可用于正式标注。
3. 代码与权重就绪后严格执行：2 dev pair × rubric-swap 4 请求 smoke → 30 dev pair 四方法调 prompt/阈值 → 冻结 checksum → 70 frozen-eval → 同冻结配置补 dev-final → 分析与 PASS/FAIL。
4. 只有 frozen-eval 满足 accuracy≥0.70、swap consistency≥0.85、high-confidence coverage≥0.60、各类别 accuracy≥0.60，才冻结 `reward-v0.yaml` 并进入 E2 Best-of-N；否则保留结果并回到 dev 修 judge。
5. M1 截止 2026-09-01 已进入高风险窗口，优先级保持 E1→E2；暂停 E3/DPO、E4/E5 和任何大规模偏好对构造。

**产物路径**

- 本条审计记录：`D:\lab idea\DEVLOG.md`
- 被审计实现：`D:\lab idea\src\e1_judge\`、`D:\lab idea\configs\e1\`

**下一步**

1. 如获实施授权，按 `E1-real-readiness-v01` 修复真实运行前置并逐步记录 DEVLOG；
2. 同步准备固定 revision 的 Qwen2.5-VL-7B-Instruct 离线包和两名真人标注排期；
3. 修复验收后才写 A6000 smoke 前置记录并执行 4 请求真实 smoke。

---

### 2026-08-24｜E1 v2 协议、媒体与 Prompt 基础重构

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 19:57:53 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码基线：`8d651bc052a73417d074489794d664f4c11244d0` + 未提交 v2 重构
- 远程环境：未使用；未连接学校 A6000；E0 目录未写入

**步骤 ID**

- `E1-v2-protocol-media-v01`

**行动与关键配置**

- 以 schema v2 整体替换旧 E1 schema，不保留 v1 兼容层：canonical pair、source/candidate refs、共享媒体 manifest、request/result/runtime/prompt/human/frozen protocol 类型全部 strict + `extra=forbid`；
- pair 改为 canonical A/B，固定 100 pair、dev 30 / frozen-eval 70，显示随机化不再固化到 pair；
- media packet 改为 10 个共享 source + 50 个共享 candidate asset，每个资产精确解码 16 帧、保存逐帧 SHA-256 和 4×4 contact sheet，100 个 pair 只保存引用和 packet checksum；
- 四个 prompt YAML 已补全 rubric、视觉角色、严格输出 schema、parser/generation 参数；实现 loader、render、checksum 和不修补语义的严格 JSON parser；
- 增加 `runtime-mock.yaml`；E0 audit 改用 `imageio-ffmpeg` executable 并移除运行时 `ffprobe` 要求，且先做输入校验再解析媒体工具。

**结果**

- 定向命令：`uv run pytest tests/e1/test_models.py tests/e1/test_pairs_packets.py`；
- 结果：**8/8 passed**，耗时 13.84s，无 warning；
- 测试验证 100 pair、30/70 split、10 source + 50 candidate 去重资产、每资产 16 帧、650×650 contact sheet、v2 配置/runtime、IVEBench/extra-field 拒绝和严格 JSON。

**产物路径**

- `src/e1_judge/models.py`、`pairs.py`、`packets.py`、`prompts.py`
- `src/w1_pipeline/media_tools.py`、`src/w1_pipeline/e0_audit.py`
- `configs/e1/pilot.yaml`、四个 prompt、`configs/e1/runtime-mock.yaml`
- `tests/e1/conftest.py`、`test_models.py`、`test_pairs_packets.py`

**问题 / 失败**

- 首次定向测试虽 8/8 通过，但 Pillow 报 960 条 `mode` 参数弃用 warning；立即移除弃用参数并复跑，最终无 warning。

**下一步**

1. 重写 schema-v2 judge plan、批处理 backend、cache/retry/lock/results 与 CLI；
2. 增加 Qwen2.5-VL-7B 独立环境参考适配器和假 command adapter 契约测试。

---

### 2026-08-24｜E1 v2 批处理 Runner、缓存恢复与 Qwen 适配器

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:06:11 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未连接学校 A6000；未下载或加载真实模型

**步骤 ID**

- `E1-v2-runner-backend-v01`

**行动与关键配置**

- 重写 plan：每个 request 固化 split、正确 sample/source/instruction、screen-side candidate identity、16 帧及 checksum、prompt/model/parser/runtime/code fingerprint；总计 550，dev 165 / frozen 385；
- backend 改为一次 shard 启动一个批处理进程，adapter 对每个 `judge_key` 原子写 envelope；mock/replay/command 使用同一契约；
- SQLite 仅把 `succeeded` 当 cache hit，failed 保留 attempt/error/runtime/VRAM 并在下一次自动重试；partial command 输出可吸收，未输出请求记为 retryable failure；
- runner 使用 64 hex `judge_key` 文件名，重建确定性的 `results.jsonl` 和 raw-response 目录；锁记录 UTC/PID/host，显式 unlock 留审计日志；
- merge 按 method 校验 prompt/parser/model identity，并拒绝混合 runtime fingerprint；
- CLI 升级为 v2 `plan --packets --runtime`、`run --runtime --split/--request-id`，新增 `freeze` 入口；重依赖均延迟导入；
- 新增 Qwen2.5-VL-7B 离线参考 adapter：单次加载、BF16/SDPA、完整 16 帧 source/A/B、mask、确定性生成、逐请求失败隔离；本地 `--help` 不导入 torch/transformers。

**结果**

- 定向命令：`uv run pytest tests/e1/test_models.py tests/e1/test_pairs_packets.py tests/e1/test_scaffold.py tests/e1/test_cache_and_resume.py tests/e1/test_e2e_mock.py`；
- 结果：**15/15 passed**，耗时 26.27s；
- mock E2E：550/550 succeeded，第二次 550 cache hits / 0 attempted；
- 假 command adapter：首轮单进程处理 550、故意缺 1 条后得到 549 success + 1 retryable failure；第二轮只请求缺失项；第三轮全 cache hit；adapter 实际仅启动 2 次；
- Windows raw 文件全部为 `<64hex>.json`，不再使用含冒号 request ID。

**产物路径**

- `src/e1_judge/runner.py`、`cache.py`、`backends/`、`cli.py`
- `scripts/e1_judge_qwen25_vl.py`
- `configs/e1/runtime-qwen25-vl-7b.example.yaml`
- `tests/e1/test_cache_and_resume.py`、`test_e2e_mock.py`、`test_scaffold.py`

**问题 / 失败**

- 无未解决失败；本步骤仅使用 mock/fake adapter，不能替代 A6000 真实 smoke。

**下一步**

1. 重建真人标注页面、确定性 per-annotator 展示、媒体 Range 服务、断点续标；
2. 强制两名 100-pair 主标注和第三人争议裁决，输出 Cohen kappa 与完成率报告。

---

### 2026-08-24｜E1 v2 真人标注与裁决协议重构

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:10:10 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未启动真实人工标注服务

**步骤 ID**

- `E1-v2-human-annotation-v01`

**行动与关键配置**

- 标注页面改为读取真实 `media-manifest.json`，展示 source/left/right 视频、三张完整 contact sheet 和可选 mask overlay；
- 所有媒体 URL 使用 annotator-specific 24 hex opaque token，不在页面或 URL 暴露 candidate ID、seed 或文件路径；
- 实现单 byte-range HTTP 响应（200/206、Content-Range、Accept-Ranges），支持浏览器 MP4 播放；
- 展示方向按 `pair_id + annotator_id + randomization_seed` 确定，screen left/right 提交后映射回 canonical A/B；failure tags 同样映射；
- 页面提供上一条/下一条、draft localStorage、断点续标、重复提交 409、confidence/notes/failure tags 和 UTC started/submitted 时间；
- 裁决强制两个不同真人各 100 个唯一 pair；任一四维或 overall 不一致都进入争议集，第三人必须且只能覆盖完整争议集；
- 输出 adjudicated JSONL 以及完成率、逐维 agreement/Cohen kappa、争议数、tie/uncertain rate 报告。

**结果**

- 定向命令：`uv run pytest tests/e1/test_annotations.py`；
- 结果：**6/6 passed**，耗时 15.46s；
- 验证 deterministic direction、canonical mapping、opaque media 页面、Range 请求、100-pair 双人全一致裁决、争议缺第三人失败、第三人精确覆盖和已知 kappa。

**产物路径**

- `src/e1_judge/annotations.py`
- `tests/e1/test_annotations.py`
- `src/e1_judge/cli.py`（`adjudicate --report` 接口）

**问题 / 失败**

- 无未解决失败；测试标注为合成记录，未冒充真人研究标签。

**下一步**

1. 重建四方法/双 split 分析、threshold 扫描、method selection、bootstrap/ranking；
2. 实现 freeze protocol、frozen gate、decision/reward-v0、严格 verify 和完整报告。

---

### 2026-08-24｜E1 v2 冻结身份链中间回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:19:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未连接学校 A6000

**步骤 ID**

- `E1-v2-frozen-identity-regression-v01`

**行动与关键配置**

- 将 generation parameters、model name/manifest 和 frozen protocol fingerprint 纳入 request/result/lock 身份链；
- runtime fingerprint 覆盖完整模型本地身份与 adapter 配置；merge 拒绝混合 generation/model/frozen protocol；
- 新增 schema-aware verification 实现，严格比对 plan/result 身份并从 raw text 重新解析语义。

**结果**

- 定向命令：`uv run pytest tests/e1/test_models.py tests/e1/test_cache_and_resume.py tests/e1/test_e2e_mock.py tests/e1/test_scaffold.py -q`；
- 结果：**12/12 passed**；既有 runner、cache、mock E2E 与 CLI scaffold 在扩展身份字段后保持通过。

**产物路径**

- `src/e1_judge/models.py`
- `src/e1_judge/runner.py`
- `src/e1_judge/reporting.py`
- `src/e1_judge/verification.py`

**问题 / 失败**

- 无未解决失败；四方法/frozen gate 专项测试尚未执行。

**下一步**

1. 增加完整 550-result 合成 oracle，验证四方法选择、冻结计划、PASS/FAIL 与 reward 产物；
2. 完成分析报告专项回归并记录。

---

### 2026-08-24｜E1 v2 四方法分析、冻结协议与 gate 闭环

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:22:29 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；所有 judge/human 结果均为显式标记的合成 oracle

**步骤 ID**

- `E1-v2-analysis-freeze-gate-v01`

**行动与关键配置**

- 按 dev/frozen-eval 隔离四方法结果，实现 canonical swap 归一化、absolute pair delta、置信阈值/absolute delta 网格扫描、coverage/effective accuracy 决胜；
- 最终方法仅从 pairwise-swap/rubric-swap 中选择，满足 swap≥0.85、coverage≥0.60，并在差值≤0.01 时选择 rubric；
- 实现 overall、四维、分类别、位置偏差、cluster bootstrap CI、Bradley–Terry、Kendall 与 Spearman；
- freeze 复制并冻结 prompt/config/runtime，生成 550-request frozen plan、不可变 protocol lock 和显式 frozen fingerprint；
- final gate 只读取冻结方法的 70 pair / 140 directional results，并严格核验 config、prompt、runtime 与 protocol fingerprint；
- PASS 才生成 `reward-v0.yaml`，FAIL 只保留 decision/metrics；report 生成 Markdown 与本地 SVG 图。

**结果**

- 定向命令：`uv run pytest tests/e1/test_metrics.py -q`；
- 结果：**5/5 passed**，耗时 19.48s；
- 合成 oracle 覆盖 100 pair / 550 requests，dev 自动选择 `rubric-swap-v1`、阈值 0.5；
- frozen PASS 验证四项 gate 全通过并生成 reward/report；局部类别反向 oracle 保持 overall 临界但触发类别 FAIL，且不生成 reward；
- strict verifier 对 frozen 550 plan/result 与 100 adjudicated labels 完整通过；单方向翻转被归一化为 inconsistent/uncertain。

**产物路径**

- `src/e1_judge/metrics.py`
- `src/e1_judge/reporting.py`
- `src/e1_judge/verification.py`
- `tests/e1/test_metrics.py`

**问题 / 失败**

- 无未解决失败；本步骤不包含真实人工标签或模型测量，因此 PASS 只验证 gate 逻辑，不是研究结论。

**下一步**

1. 编写中文 A6000 离线准备、smoke、标注、冻结、恢复与回传执行手册；
2. 从 README/E0/E1 现有文档建立入口，并执行文档静态验收。

---

### 2026-08-24｜E1 v2 第三人争议续标闭环

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:25:38 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未启动真人标注

**步骤 ID**

- `E1-v2-third-adjudication-resume-v01`

**行动与关键配置**

- 首次裁决发现争议且未提供第三人记录时，先原子形成含 `disputed_pair_ids`、逐维一致率和 kappa 的 precheck 报告，再以明确错误停止；
- `e1 annotate --pair-filter <precheck.json>` 支持第三人只加载争议 pair，保留同一方向映射、媒体服务、自动保存和断点恢复；
- 最终裁决继续强制第三人记录与争议集合精确相等，拒绝漏标或多标。

**结果**

- 定向命令：`uv run pytest tests/e1/test_annotations.py -q`；
- 结果：**6/6 passed**，耗时 17.17s；
- 新增验证：precheck 状态为 `needs_third_annotator`，争议清单可直接作为第三人标注过滤输入。

**产物路径**

- `src/e1_judge/annotations.py`
- `src/e1_judge/cli.py`
- `tests/e1/test_annotations.py`

**问题 / 失败**

- 首次无第三人裁决按协议失败，但已产生可续标诊断产物；这是预期控制流，不是未解决故障。

**下一步**

1. 将该两阶段裁决流程写入 A6000 手册；
2. 固化服务器环境、模型与 smoke 停机门。

---

### 2026-08-24｜E1 v2 A6000 离线执行手册

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:30:03 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；手册命令未在学校服务器执行

**步骤 ID**

- `E1-v2-a6000-runbook-v01`

**行动与关键配置**

- 新增中文 E1 v2 服务器手册，固定实验根 `/DATA/DATA4/hfy/outputs/E1-judge-pilot-v02` 与 Qwen2.5-VL-7B revision `a22b9b202f87d21defc75df2652beed712e52261`；
- 固定独立 Python 3.11 / torch 2.1.2+cu118 / torchvision 0.16.2+cu118 / Transformers 4.49.0 / Accelerate 1.2.1 / qwen-vl-utils 0.0.8 环境，明确不安装 flash-attn、不改 w1-control/anyv2v；
- 覆盖联网 Linux 普通 snapshot、完整 wheelhouse、conda-pack、MODEL_CARD_LOCAL、逐文件/全包 SHA256SUMS、上传与离线验收；
- 固化 4-request smoke、两人 100-pair 标注、第三人争议续标、165 dev 四方法、选择/freeze、140 frozen selected-method、60 dev-final、merge/final gate 顺序；
- 写明 tmux 单 writer、raw/log、失败吸收、cache 重试、stale lock 审计解锁、DEVLOG 前后置模板、停止条件和回传清单；
- README 和旧 E0/E1 综合手册已链接到 v2 手册，避免继续使用 v1 目录/命令。

**结果**

- 静态检索确认手册包含固定实验 ID、完整 revision、禁止 flash-attn、pair-filter 与 frozen selected 子计划；未残留 `.venv` 硬编码或旧 v01 E1 实验 ID；
- 命令接口检查：`uv run e1 annotate --help` 与 `uv run e1 freeze --help` 均通过，手册所用 `--pair-filter`、`--output-dir` 等参数存在。

**产物路径**

- `docs/E1_A6000_RUNBOOK.md`
- `configs/e1/qwen25-vl-cu118-requirements.txt`
- `README.md`
- `docs/E0_AUDIT_E1_EXECUTION.md`

**问题 / 失败**

- 尚未进行 A6000 smoke、真人标注或模型可靠性实验；服务器路径/驱动/离线包仍须按手册现场验收。

**下一步**

1. 执行本地全量 pytest、CLI validate、550/550 mock/cache 回归与 diff/大文件检查；
2. 修复任何回归后写最终本地验收记录，再 fetch/rebase、提交和推送。

---

### 2026-08-24｜E1 v2 首轮全量回归诊断

**状态：FAILED（已定位，待修复）**

**时间与环境**

- 完成时间：2026-08-24 20:31:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E1-v2-local-regression-attempt-01`

**行动与关键配置**

- 执行全量命令：`uv run pytest`；
- 保留全部失败 traceback，未跳过或放宽测试。

**结果**

- **52 passed / 2 failed**，总耗时 62.42s；
- 两个失败均位于旧 `tests/test_build_e0_audit.py`，测试自身仍直接启动系统 `ffprobe` 与 `sha256sum`；
- 当前 Windows 环境没有这两个系统命令，生产实现已改用 ImageIO/imageio-ffmpeg 和 Python SHA-256，因此失败属于旧 fixture/验收方式未迁移，不是媒体构建失败。

**产物路径**

- 失败文件：`tests/test_build_e0_audit.py`
- 被验收实现：`src/w1_pipeline/e0_audit.py`、`src/w1_pipeline/media_tools.py`

**问题 / 失败**

- `_probe_mp4` 仍调用裸 `ffprobe`；
- SHA256SUMS 验收仍调用外部 `sha256sum -c`；
- 这与 v2 明确的“无系统 ffprobe/sha256sum”验收目标冲突。

**下一步**

1. 将测试改为项目内 `probe_video` 和 Python checksum 校验，不改 E0 产物；
2. 先重跑该文件，再重新执行完整测试集。

---

### 2026-08-24｜E0 审计测试去除系统工具依赖

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:33:00 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E1-v2-e0-cross-platform-test-fix-v01`

**行动与关键配置**

- 将旧审计测试的裸 `ffprobe` 调用替换为项目内 ImageIO `probe_video`；
- 将 `sha256sum -c` 替换为逐行解析 SHA256SUMS 并使用 Python `sha256_file` 校验；
- 未修改 E0 原始输入、审计产物格式或生产语义。

**结果**

- 定向命令：`uv run pytest tests/test_build_e0_audit.py -q`；
- 结果：**9/9 passed**，耗时 22.37s；
- 验证 22 个 MP4 可解码且为 512×256、8 fps、16 帧，50 张 contact sheet 可读，全部 SHA256SUMS 条目匹配。

**产物路径**

- `tests/test_build_e0_audit.py`

**问题 / 失败**

- 无未解决失败。

**下一步**

1. 重新执行完整 `uv run pytest`；
2. 全绿后继续 CLI、mock E2E 与仓库卫生验收。

---

### 2026-08-24｜E1 v2 第二轮全量 pytest

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:34:26 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未加载真实 Qwen 权重

**步骤 ID**

- `E1-v2-local-regression-attempt-02`

**行动与关键配置**

- 在修复旧跨平台测试后，重新执行无筛选完整命令 `uv run pytest`。

**结果**

- **54/54 passed**，耗时 65.24s；
- 覆盖 E0 审计只读行为、v2 schema/pair/media、标注/裁决、prompt parser、550-request runner/cache/fake command、四方法分析、freeze、PASS/FAIL/reward/report 与 CLI。

**产物路径**

- 测试目录：`tests/`
- 临时媒体、SQLite、结果与报告仅位于 pytest 临时目录，不在工作树。

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 执行 `uv run e1 validate` 与显式 runtime 校验；
2. 再做独立 550/550 mock 二次 cache hit 验收、diff 和大文件审计。

---

### 2026-08-24｜E1 v2 配置与 runtime 校验

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:34:46 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E1-v2-config-runtime-validate-v01`

**行动与关键配置**

- 执行 `uv run e1 validate`；
- 执行 `uv run e1 validate --runtime configs/e1/runtime-mock.yaml`。

**结果**

- 两条命令均成功；pilot schema-v2、四个完整 prompt、550 request 协议和 mock runtime 严格模型均有效。

**产物路径**

- `configs/e1/pilot.yaml`
- `configs/e1/prompt-*-v1.yaml`
- `configs/e1/runtime-mock.yaml`

**问题 / 失败**

- 无。

**下一步**

1. 运行独立 v2 mock 550/550 与第二次全 cache hit；
2. 检查 Git diff、文件大小和禁止提交的媒体/cache/权重。

---

### 2026-08-24｜E1 v2 独立 mock 550/550 cache 验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:35:30 +08:00
- 执行位置：本地 Windows pytest 临时目录
- 远程环境：未使用；backend=`mock`，`research_result=false`

**步骤 ID**

- `E1-v2-mock-e2e-final-v01`

**行动与关键配置**

- 独立执行 `uv run pytest tests/e1/test_e2e_mock.py -q`；
- 构造 100 pair、共享 media manifest 和 550-request plan，连续两次运行相同 plan/cache。

**结果**

- **1/1 passed**，耗时 25.31s；
- 首轮 550 selected / 0 cache hits / 550 attempted / 550 succeeded；
- 第二轮 550 selected / 550 cache hits / 0 attempted / 550 succeeded；
- dev/frozen 精确为 165/385，raw response 文件均为 Windows-safe 64hex 名称。

**产物路径**

- `tests/e1/test_e2e_mock.py`
- 所有生成媒体、SQLite 与结果均位于 pytest 临时目录，未进入仓库。

**问题 / 失败**

- 无；这些是接口验收结果，不是研究测量。

**下一步**

1. 执行 `git diff --check`；
2. 审计状态、未跟踪文件、禁入扩展名和大文件，再准备提交。

---

### 2026-08-24｜E1 v2 混合结果身份拒绝专项验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:36:47 +08:00
- 执行位置：本地 Windows pytest 临时目录
- 远程环境：未使用

**步骤 ID**

- `E1-v2-merge-identity-guard-v01`

**行动与关键配置**

- 扩展 merge 专项测试，分别篡改 runtime fingerprint、generation parameters、frozen protocol fingerprint 和 model manifest；
- 每个变体使用独立输入/output，避免前一失败污染后一断言。

**结果**

- 定向命令：`uv run pytest tests/e1/test_cache_and_resume.py -q`；
- 结果：**3/3 passed**，耗时 23.92s；
- 四类身份混合全部被拒绝；单进程 batch、partial resume、retry、全 cache hit 和活跃锁用例保持通过。

**产物路径**

- `tests/e1/test_cache_and_resume.py`
- `src/e1_judge/runner.py`

**问题 / 失败**

- 无。

**下一步**

1. 由于专项测试文件在全量回归后有新增，提交前再执行一次完整 pytest；
2. 随后一次性完成 diff/大文件审计并记录最终回归。

---

### 2026-08-24｜E1 v2 最终全量 pytest

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:38:18 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未加载真实模型

**步骤 ID**

- `E1-v2-local-regression-final-v01`

**行动与关键配置**

- 在加入混合 generation/frozen protocol/model manifest 拒绝用例后，重新运行最终无筛选 `uv run pytest`。

**结果**

- **54/54 passed**，耗时 64.56s；
- 最终测试树与待提交代码一致，未使用跳过、xfail 或真实权重。

**产物路径**

- `tests/`
- `src/e1_judge/`
- `src/w1_pipeline/`

**问题 / 失败**

- 无未解决失败。

**下一步**

1. 执行 `git diff --check` 和仓库卫生审计；
2. 记录最终交付摘要，然后 fetch/rebase（如需）、commit 并 push。

---

### 2026-08-24｜E1 v2 本地交付验收总结

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-24 20:38:49 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；学校 A6000 实验未启动

**步骤 ID**

- `E1-v2-local-delivery-acceptance-v01`

**行动与关键配置**

- 执行 `git diff --check`；
- 审计 `git status --short`、diff stat、全部未跟踪文件；
- 使用扩展名扫描视频、SQLite/DB、PyTorch checkpoint、safetensors/bin，并扫描排除 `.git/.venv/cache` 后超过 5 MB 的工作树文件。

**结果**

- `git diff --check`：通过，仅有 Windows autocrlf 提示，无 whitespace error；
- 工作树无 `.mp4/.avi/.mov`、`.sqlite/.sqlite3/.db`、`.pt/.pth/.ckpt/.safetensors/.bin`；
- 工作树无超过 5 MB 的交付文件；
- 未跟踪项仅为预期的小型 runtime/requirements、E1 手册、Qwen adapter、media helper 和 test fixture；
- 最终全量测试 54/54、E1 config/runtime validate、mock 550/550 与第二次 550 cache hits 均已在前置记录中通过。

**产物路径**

- 代码：`src/e1_judge/`、`src/w1_pipeline/media_tools.py`
- 模型适配器：`scripts/e1_judge_qwen25_vl.py`
- 协议/runtime：`configs/e1/`
- 手册：`docs/E1_A6000_RUNBOOK.md`
- 测试：`tests/e1/`、`tests/test_build_e0_audit.py`

**问题 / 失败**

- 无本地工程阻塞；真实 A6000 smoke、两人标注、第三人裁决和 frozen reliability gate 属于服务器后续操作，不能由本地 mock 代替。

**下一步**

1. `git fetch origin`，确认 `origin/main` 未前进；若前进则无 force rebase 并重跑全量验收；
2. 使用提交信息 `Rebuild E1 judge pipeline for real-model readiness` 形成单一提交并推送 `origin/main`。

---

### 2026-08-28｜E1 v2 source video checksum 修复授权与基线阻断

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:11:40 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码基线：`82ce0292116f229033b28b47e9a46ad731366c61`；`main` 与最新 fetch 的 `origin/main` 一致
- 远程环境：未连接学校 A6000；未修改服务器、E0、delivery、模型或 E1 产物

**步骤 ID**

- `E1-v2-source-video-checksum-fix-authorization-v01`

**行动与关键配置**

- 用户明确授权 Codex 修改本地代码、测试、文档与 DEVLOG，并在完整验收后非强制推送新的审计 baseline 到 `main`；
- 授权范围写入 `AGENTS.md`，明确禁止服务器现场 patch、改 E0、改 sealed delivery 或重写历史；
- 在 A6000 runbook 增加基线勘误门：旧提交 `82ce029...` 的 `pairs.py` 混用了 source frame-set checksum 与 source MP4 checksum，在新 baseline 下发前禁止创建 E1 根或执行 phase 3；
- 已确认的根因链：生产 `InputRecord.source_checksum` 是 16 张源帧的组合 SHA，`InputRecord.video_checksum` 是 `source.mp4` 文件 SHA；`pairs.py` 错把前者写入 `SourceRefV2.video_sha256`，随后 `packets.py` 用 MP4 文件 SHA 严格比较而必然失败；现有测试 fixture 将两者混同，未覆盖生产语义。

**结果**

- 修复权限与停止边界已形成仓库内审计记录；
- 当前仅完成授权与文档阻断，尚未修改实现，不能解除服务器 `BLOCKED_CODE_DEFECT`；
- 服务器诊断证据：10/10 source 的实际 MP4 SHA 等于 `plan.video_checksum`，10/10 frame-set 组合 SHA 等于 `plan.source_checksum`，两字段 10/10 不相等；E1 根仍不存在。

**产物路径**

- `AGENTS.md`
- `docs/E1_A6000_RUNBOOK.md`
- `DEVLOG.md`
- 服务器只读证据（未由本地修改）：`/DATA/DATA4/hfy/outputs/E1-judge-pilot-v02.SOURCE_IDENTITY_DIAGNOSIS.json`，SHA-256 `5837a9a1e07b0793e5dbc956ce20eee31b9c6e439dde6e6b158a50976360f608`

**问题 / 失败**

- 旧 baseline 已确认不适用于真实 E1 phase 3；readiness audit 的执行证据保留，但其原 `status=passed` 结论不被接受。

**下一步**

1. 修复 `pairs.py` 使用 `input.video_checksum`，并把两种 source checksum 的一致性纳入构建检查；
2. 更新测试 fixture 使 frame-set checksum 与 MP4 checksum 明确不同，并增加直接回归断言；
3. 运行定向和全量测试，每个完成步骤立即写 DEVLOG。

---

### 2026-08-28｜E1 v2 source video checksum 实现修复与定向回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:13:21 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 修复前代码基线：`82ce0292116f229033b28b47e9a46ad731366c61` + 本次未提交修复
- 远程环境：未使用；未运行模型、未创建 E1、未修改 E0 或服务器产物

**步骤 ID**

- `E1-v2-source-video-checksum-codefix-v01`

**行动与关键配置**

- `src/e1_judge/pairs.py` 的 `SourceRefV2.video_sha256` 改为读取生产 `InputRecord.video_checksum`，不再错误读取 frame-set `source_checksum`；
- 同 sample 的五条 plan input 一致性检查同时覆盖 `source_checksum` 和 `video_checksum`，拒绝同一 source 的任一身份漂移；
- 测试 fixture 现在明确构造两个不同的 64 位身份：`source_checksum` 表示 frame-set，`video_checksum` 表示 source MP4 文件 SHA；
- pair/media 回归新增直接断言：100 个 pair 的 `source.video_sha256` 全部等于 `input.video_checksum`，并全部不等于 `input.source_checksum`。

**结果**

- 定向命令：`uv run pytest tests/e1/test_pairs_packets.py -q`；
- 结果：**3/3 passed**，耗时 28.7s；
- fixture 随后完整执行 `build_pairs` 和 `build_packets`，证明生产双-checksum 语义下 10 source / 50 candidate / 100 pair 媒体构建不再触发 source MP4 checksum mismatch。

**产物路径**

- `src/e1_judge/pairs.py`
- `tests/e1/conftest.py`
- `tests/e1/test_pairs_packets.py`

**问题 / 失败**

- 无定向回归失败；尚未完成全量测试和配置/仓库卫生验收。

**下一步**

1. 执行无筛选完整 `uv run pytest`；
2. 全绿后执行 E1 config/runtime validate 和 diff/大文件审计。

---

### 2026-08-28｜E1 v2 source checksum 修复后全量回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:15:09 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码状态：`82ce029...` + 已记录的本地 source video checksum 修复
- 远程环境：未使用；未加载真实 Qwen 权重

**步骤 ID**

- `E1-v2-source-video-checksum-full-regression-v01`

**行动与关键配置**

- 在生产 checksum 语义 fixture 和修复实现上执行无筛选完整命令：`uv run pytest`；
- 未使用 skip、xfail、mock GPU 或真实模型。

**结果**

- **54/54 passed**，耗时 81.09s；
- 覆盖 E0 数据/审计、E1 schema/pair/media、标注/裁决、runner/cache、分析/freeze/gate/report 和 CLI；
- 新的 source frame-set / source MP4 双 checksum 回归包含在全量测试中并通过。

**产物路径**

- `tests/`
- `src/e1_judge/pairs.py`

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 执行 E1 schema/config 与 mock runtime validate；
2. 完成 diff、tracked/untracked、大文件和禁止产物审计。

---

### 2026-08-28｜E1 v2 修复后 config/runtime 校验

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:15:31 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E1-v2-source-video-checksum-config-validate-v01`

**行动与关键配置**

- 执行 `uv run e1 validate`；
- 执行 `uv run e1 validate --runtime configs/e1/runtime-mock.yaml`。

**结果**

- 两条命令均成功；schema-v2 pilot、四方法 prompt、550-request 协议和 mock runtime 继续通过严格校验；
- 本次 checksum 修复未改变 prompt、阈值、generation 参数、模型 revision 或方法选择协议。

**产物路径**

- `configs/e1/pilot.yaml`
- `configs/e1/runtime-mock.yaml`
- `configs/e1/prompt-*-v1.yaml`

**问题 / 失败**

- 无。

**下一步**

1. 执行 Git diff/whitespace/大文件与禁止产物审计；
2. 审计通过后形成新的本地 baseline commit。

---

### 2026-08-28｜E1 v2 source checksum 修复提交前仓库验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:16:03 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程状态：执行修复前已 `git fetch origin`，`origin/main` 仍为 `82ce0292116f229033b28b47e9a46ad731366c61`
- 远程实验环境：未使用

**步骤 ID**

- `E1-v2-source-video-checksum-repo-acceptance-v01`

**行动与关键配置**

- 执行 `git diff --check`、`git status --short`、`git diff --stat` 并逐项人工审阅实现/测试/授权/runbook diff；
- 审计全部 untracked 文件；
- 扫描 `.mp4/.avi/.mov`、SQLite/DB、PyTorch checkpoint、safetensors/bin 等禁止实验产物；
- 排除 `.git/.venv/cache` 后扫描超过 5 MB 的工作树文件。

**结果**

- `git diff --check` 无 whitespace error，仅有 Windows autocrlf 提示；
- 修改范围精确为 6 个预期文件：`AGENTS.md`、`DEVLOG.md`、E1 runbook、`pairs.py` 和两个 E1 测试文件；
- untracked=0，禁止实验产物=0，超过 5 MB 的交付文件=0；
- diff 人工核验确认只改变 source video checksum 取值/一致性检查、生产语义 fixture、回归断言和审计文档；未改变 prompt、threshold、runtime、model revision 或 E1 split/method 协议。

**产物路径**

- `AGENTS.md`
- `DEVLOG.md`
- `docs/E1_A6000_RUNBOOK.md`
- `src/e1_judge/pairs.py`
- `tests/e1/conftest.py`
- `tests/e1/test_pairs_packets.py`

**问题 / 失败**

- 无提交阻塞。

**下一步**

1. 再次 fetch 并确认 `origin/main` 未前进；
2. 创建新的 source checksum 修复 baseline commit；
3. 非强制推送到 `origin/main`，随后追加发布 DEVLOG 记录。

---

### 2026-08-28｜E1 v2 source checksum 修复 baseline 发布

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-28 22:16:58 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 发布目标：GitHub `origin/main`
- 远程实验环境：未连接；服务器工作树和 sealed delivery 未修改

**步骤 ID**

- `E1-v2-source-video-checksum-baseline-publish-v01`

**行动与关键配置**

- 发布前再次执行 `git fetch origin`，确认 `origin/main` 仍为旧 baseline `82ce0292116f229033b28b47e9a46ad731366c61`，不存在并发前进；
- 使用提交信息 `Fix E1 source video checksum identity` 创建修复提交；
- 执行普通 `git push origin main`，未使用 force、force-with-lease、reset、rebase 或历史重写。

**结果**

- 修复 commit：`3e635db6fcb205c37fe2a462885859e5c72aa47e`；
- push 成功：`origin/main` 从 `82ce029...` 前进到 `3e635db...`；
- push 后本地 `main`、本地 `origin/main` 与 HEAD 三者一致，工作树干净；
- 该 commit 包含授权/停止门文档、checksum 实现修复、生产语义 fixture、回归断言以及此前全部逐步 DEVLOG；
- 验收依据：定向 3/3、全量 54/54、两条 E1 validate、仓库卫生审计全部通过。

**产物路径**

- Git commit：`3e635db6fcb205c37fe2a462885859e5c72aa47e`
- 远端：`origin/main`
- 本记录：`DEVLOG.md`

**问题 / 失败**

- 无 push 失败或分支冲突；旧 sealed delivery 的 code bundle 仍固定为 `82ce029...`，不得把它误报为新 baseline 的交付证据。

**下一步**

1. 用 DEVLOG-only 审计提交保存本发布记录并普通推送；
2. 设计服务器代码 baseline 更新阶段：保留服务器 dirty DEVLOG，禁止现场 patch，使用可校验的新 commit/bundle 并重新执行 CPU readiness；
3. 在服务器更新和 GPU preflight 完成前，E1 根继续保持 ABSENT。

---

### 2026-08-29｜E1 v2 后续本地工程扩展授权

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 14:41:18 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 本地 baseline：`89a8a7279bc1bdaf2bb4196e02971f349129b5ab`；branch=`main`；HEAD、本地 `origin/main` 与 baseline 一致；授权记录前工作树干净
- 远程环境：未连接学校服务器；未运行真实模型；未创建服务器实验目录

**步骤 ID**

- `E1-v2-followup-local-engineering-authorization-v01`

**行动与关键配置**

- 完整读取接管说明要求的 `AGENTS.md`、README、E1 A6000 runbook、近期 checksum 修复/发布 DEVLOG、pilot/runtime、四个 prompt、pair/packet/runner/model/verification/annotation/report/CLI/adapter 实现和 `tests/e1/` 源测试；
- 只读执行 `git branch --show-current`、`git rev-parse HEAD`、`git rev-parse refs/remotes/origin/main`、`git status --porcelain=v1`、`git log` 和 baseline diff，确认正式本地身份；
- 在 `AGENTS.md` 追加 2026-08-29 扩展授权：允许后续 E1 阶段所需的本地 CPU-only 代码、测试、文档和 DEVLOG 预备；
- 明确禁止未经再次授权 commit/push，禁止修改固定研究协议，禁止连接或操作学校服务器、运行真实模型或创建服务器实验目录；
- 下一开发包固定为 `E1-v2-preparation-verifier-v01`，仅实现 phase 3 后、smoke 前的只读 preparation bundle 验收。

**结果**

- 接管身份核验通过：`main`、HEAD、本地 `origin/main` 均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`，相对该 baseline 零 diff；
- 现有 `e1 verify` 仅验证 judge plan/results/human，不等价于 preparation verifier；P0 存在真实缺口；
- 当前正式服务器 checkpoint 仍按转交记录保持：环境恢复和新代码 baseline 更新 DONE，`fixed-path-offline-preflight-v02` 为 WAIT_GPU，正式 E1 根 ABSENT；本地未改变任何服务器状态；
- 本步骤仅形成授权与审计边界，未改变 prompt、threshold、generation、model identity、30/70 split、四方法结构或最终 gate。

**产物路径**

- `AGENTS.md`
- `DEVLOG.md`

**问题 / 失败**

- 无身份冲突；无服务器或 GPU 操作；无研究结果产生。

**下一步**

1. 形成 preparation verifier 的检查 schema、不变量与失败报告设计；
2. 使用生产语义 tiny fixture 实现只读校验和 corruption/partial-output 拒绝测试；
3. 每个独立可验证步骤完成后立即追加 DEVLOG。

---

### 2026-08-29｜E1 v2 preparation verifier 设计与报告 schema

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 14:43:05 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码基线：`89a8a7279bc1bdaf2bb4196e02971f349129b5ab` + 已记录的授权/DEVLOG 工作树修改
- 远程环境：未使用；设计仅面向本地 CPU/read-only 验收

**步骤 ID**

- `E1-v2-preparation-verifier-design-v01`

**行动与关键配置**

- 审计现有 `e1 verify`、pair/packet/plan builder、strict Pydantic models、prompt/runtime fingerprint 和原子 JSONL helper，确认没有等价的 phase-3 preparation bundle verifier；
- 确定新增 `src/e1_judge/preparation.py` 与 `e1 verify-preparation`，输入固定为 pairs、packets、plan、config、runtime，可选唯一 output report；
- 报告 schema 确定包含：`status`、`generated_at`、input path/SHA、pairs/assets/frames/masks/requests counts、method/split counts、runtime/model identity、prompt checksums、code snapshot、逐项 checks、warnings、failures 和 `ready_for_smoke`；
- 失败语义确定为：尽可能累积独立硬检查；任一硬检查失败即 `status=failed`、`ready_for_smoke=false`、CLI 非零；指定 output 时仍原子写诊断 JSON，但 output 已存在时在读取/验证前拒绝覆盖；
- development `code_snapshot` 允许 40 位 commit 或 `+dirty`；`+dirty` 只有在当前 Git dirty 路径精确为 `DEVLOG.md` 时可通过，并必须写 warning，不静默忽略；unknown snapshot 一律拒绝；
- P0 只读检查现有 partial output，不改写 `build_pairs`、`build_packets`、`build_judge_plan` 或 runtime 创建流程。

**结果**

- 形成可直接实现和测试的 P0 不变量；
- 明确 preparation verifier 与结果 verifier、GPU preflight 的边界；
- 未修改 prompt、threshold、generation、model revision、30/70 split、四方法结构或最终 gate。

**产物路径**

- `DEVLOG.md`
- 计划实现：`src/e1_judge/preparation.py`、`src/e1_judge/cli.py`、`tests/e1/`

**问题 / 失败**

- `build_packets` 当前会在完成前创建正式 output dir 并逐步写入；中断会留下 partial 目录，现有重跑会因目录已存在而拒绝。P0 verifier 可识别失败但不负责事务发布；该风险留给 P1 staging/atomic wrapper。

**下一步**

1. 实现 preparation 模块、固定协议/runtime/媒体/plan 身份检查和原子报告；
2. 接入 CLI；
3. 扩充生产语义 mask fixture 并运行定向测试。

---

### 2026-08-29｜E1 v2 preparation verifier 实现与定向验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 14:52:18 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 代码状态：baseline `89a8a7279bc1bdaf2bb4196e02971f349129b5ab` + 本次未提交的 P0 本地实现
- 远程环境：未使用；未加载真实模型；全部测试使用 pytest 临时目录、tiny 视频/PNG 和 command fixture

**步骤 ID**

- `E1-v2-preparation-verifier-implementation-targeted-v01`

**行动与关键配置**

- 新增 `src/e1_judge/preparation.py`：严格复核固定 pilot/runtime/prompt、100 pair、10 source/50 candidate asset、960 frame、60 contact sheet、100 packet metadata/mask/checksum 和 550-request plan；
- source identity 通过 pairs→manifest→original MP4 实际 SHA 复算，明确不接受 E0 frame-set `source_checksum` 代替 MP4 `video_checksum`；
- plan 验证覆盖 request/judge_key 唯一性、50/100/200/200 方法量、165/385 split、15/30/60/60 dev 方法量、swap 双方向、absolute 每候选一条、media/prompt/parser/generation/runtime/model/code identity；
- 固定 runtime 校验 backend=`command`、Qwen ID/revision/path、adapter python/script、64hex model manifest；固定当前四 prompt 文件 SHA 并复核 parser/generation；
- 可选 report 使用同目录临时文件 + `os.link` 原子无覆盖发布；硬检查失败仍写 `status=failed` 诊断并抛出非零语义，已有 output 在验证前拒绝；
- CLI 新增 `e1 verify-preparation`；成功/失败均输出简洁 JSON 状态，失败退出码为 1；
- 生产语义 fixture 新增每 sample 16 张真实 tiny mask PNG、100 个 mask overlay，保留 `source_checksum != video_checksum`；
- 新增 corruption/partial 拒绝测试：source original、candidate SHA、frame missing/SHA、contact sheet、packet metadata/checksum、mask、549 plan、duplicate judge_key、mixed model identity、已有 report、输入 checksum 不变和 CLI failed report；
- 静态确认四个当前 prompt 的工作树 SHA 与 Git blob SHA 完全一致，且文件均为 LF，无 Windows 换行差异；
- 执行 `uv run python -m py_compile src/e1_judge/preparation.py src/e1_judge/cli.py tests/e1/conftest.py tests/e1/test_preparation.py`；
- 执行 `uv run pytest tests/e1/test_preparation.py tests/e1/test_pairs_packets.py tests/e1/test_annotations.py tests/e1/test_scaffold.py -q`。

**结果**

- Python 语法检查通过；
- 定向测试 **28/28 passed**；
- happy path report 为 `status=passed`、`ready_for_smoke=true`，精确报告 100 pair、60 asset、960 frame、100 mask 和 550 request；
- 每种损坏均产生 `status=failed`、`ready_for_smoke=false`，CLI 非零；指定 failed output 时保留诊断，既有 output 保持 sentinel 未被覆盖；
- 全部被引用输入文件在 verifier 前后 SHA-256 集合完全一致；
- mock/tiny 结果仅用于接口验收，不是研究结果；未改变固定研究协议。

**产物路径**

- `src/e1_judge/preparation.py`
- `src/e1_judge/cli.py`
- `tests/e1/conftest.py`
- `tests/e1/test_preparation.py`
- `tests/e1/test_pairs_packets.py`
- `tests/e1/test_annotations.py`
- `tests/e1/test_scaffold.py`

**问题 / 失败**

- 无未解决定向测试失败；完整 pytest 尚未执行。

**下一步**

1. 在 A6000 runbook 的 phase 3 和 smoke 之间加入唯一 preparation report 门；
2. 新增 phase 3 工程说明并记录四个 builder 的 partial/overwrite/恢复风险；
3. 文档完成后运行 CLI help/config validate、全量 pytest 和仓库卫生审计。

---

### 2026-08-29｜E1 v2 phase 3 runbook、工程说明与 CLI gate 验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 14:56:07 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；文档中的服务器命令仅为预备说明，未实际执行

**步骤 ID**

- `E1-v2-preparation-verifier-docs-cli-v01`

**行动与关键配置**

- 更新 `docs/E1_A6000_RUNBOOK.md`：在 phase 3 创建完成后、4-request smoke 前加入唯一 `e1 verify-preparation` gate；
- 正式 report 路径固定为 `$E1/preparation-verification-v01.json`，运行前要求 ABSENT；PASS 必须同时满足 exit 0、`status=passed`、`ready_for_smoke=true`、`failures=[]`；
- 明确 failed report/partial output 必须保留并写 FAILED DEVLOG，不得覆盖、修补或进入 smoke；明确 verifier 是 CPU/read-only 验收，不替代 GPU/offline preflight；
- 新增 `docs/E1_PHASE3_ENGINEERING.md`：记录 phase 3 输入/派生身份图、100/550 计数表、source frame-set/MP4 checksum 语义、report schema、磁盘/inode 复验、DEVLOG PLAN/COMPLETE/FAILED 模板和 runbook 边界；
- 完成原子性审计：runtime `cp`+原地重写可覆盖且非原子；`build_pairs` final JSONL 直接写；`build_packets` final dir 增量构建且中断会留 partial；`build_judge_plan` 使用 temp+replace；P0 report 使用原子无覆盖发布；
- 形成 P1 staging/atomic wrapper 八项设计不变量，但 P0 未扩大实现；
- 执行 `uv run e1 --help`、`uv run e1 verify-preparation --help`；
- 执行 `uv run e1 validate` 和 `uv run e1 validate --runtime configs/e1/runtime-mock.yaml`；
- 只读检索 runbook gate 和工程文档章节，确认关键命令/字段/边界已落盘。

**结果**

- 顶层 CLI 显示 `verify-preparation`；子命令帮助完整显示 pairs/packets/plan/config/runtime/output；
- 两条既有 schema/runtime validate 均成功；
- runbook 中 verifier 严格位于 phase 3 与 smoke 之间，最终产物树包含唯一 preparation report；
- 文档明确 P1 确有必要，首要原因是 `build_packets` partial dir 与 runtime 可覆盖风险；
- 未改变 prompt、threshold、generation、model revision、split、四方法结构或最终 gate。

**产物路径**

- `docs/E1_A6000_RUNBOOK.md`
- `docs/E1_PHASE3_ENGINEERING.md`
- `src/e1_judge/cli.py`

**问题 / 失败**

- 无 CLI/help/config validation 失败；P1 wrapper 尚未实现，符合本次 P0 范围。

**下一步**

1. 运行无筛选完整 `uv run pytest`；
2. 全绿后执行 Git diff/whitespace、untracked、禁止实验产物、大文件和协议文件 hash 审计；
3. 汇总 P0，明确不 commit、不 push，并建议下一包为 P1。

---

### 2026-08-29｜E1 v2 preparation verifier 全量本地回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 14:58:48 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未加载/下载真实 Qwen 权重；pytest 仅使用 tiny fixture、mock 与 fake command adapter

**步骤 ID**

- `E1-v2-preparation-verifier-full-regression-v01`

**行动与关键配置**

- 在全部 P0 实现、生产语义 mask fixture、CLI、runbook 和工程说明落盘后执行无筛选 `uv run pytest`；
- 未使用 skip、xfail、GPU mock 或真实研究输出替代验收。

**结果**

- **70/70 passed**，耗时 126.01s；
- 相对正式 baseline 的 54 条测试新增 16 条 preparation 专项用例；
- 覆盖 E0 只读审计、E1 strict models、100 pair/媒体、100 masks、550 plan、runner/cache、标注/裁决、metrics/freeze/final gate/report、preparation happy/corruption/read-only/CLI；
- mock/tiny 测试结果仅证明工程接口和失败门，不是 E1 研究结论；服务器 phase 3、smoke、人工标注和 final gate 状态未改变。

**产物路径**

- `tests/`
- `src/e1_judge/`
- pytest 临时媒体/report/cache 位于系统临时目录，未作为工作树产物保留

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 执行 `git diff --check`、状态/diff 审阅、未跟踪/禁止扩展名/大文件审计；
2. 核对四 prompt、pilot 和 runtime example 未发生内容漂移；
3. 记录最终 P0 仓库验收，不 commit、不 push。

---

### 2026-08-29｜E1 v2 partial manifest 结构化失败加固

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 15:01:21 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；tiny fixture / CPU-only

**步骤 ID**

- `E1-v2-preparation-verifier-partial-manifest-guard-v01`

**行动与关键配置**

- 最终失败路径审阅发现：strict manifest schema 允许 dict 数量不足；若整项缺少 source/candidate asset，后续交叉索引可能在 failed report 发布前抛 `KeyError`；
- 在 media packet 校验中先识别缺失 manifest asset 并记录精确失败，不再无保护索引；
- 新增 `pairs_ready` / `manifest_ready` 依赖门：上游身份失败时，后续 media/plan 交叉 gate 标记为 `skipped`，但原始失败继续使 report 为 failed；
- `verify_preparation` 对 media 交叉校验的意外异常也转换为结构化 failed check；
- 新增回归：删除一个 source asset，要求原子写出与异常对象一致的 `status=failed` report、`ready_for_smoke=false`，plan gate 为 skipped；
- 执行 `uv run python -m py_compile src/e1_judge/preparation.py tests/e1/test_preparation.py`；
- 执行 `uv run pytest tests/e1/test_preparation.py -q`。

**结果**

- 语法检查通过；
- preparation 专项 **17/17 passed**；
- partial manifest 不再导致无报告崩溃，缺失 asset 产生明确失败并禁止 smoke；
- 未改变任何研究协议或正式服务器状态。

**产物路径**

- `src/e1_judge/preparation.py`
- `tests/e1/test_preparation.py`

**问题 / 失败**

- 原风险已通过依赖门和回归测试关闭；因全量测试后又发生代码变更，需要重新运行完整 pytest。

**下一步**

1. 重新执行无筛选 `uv run pytest`；
2. 全绿后完成最终仓库卫生与协议漂移审计。

---

### 2026-08-29｜E1 v2 preparation verifier 加固后最终全量回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 15:04:16 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；未加载真实模型

**步骤 ID**

- `E1-v2-preparation-verifier-full-regression-final-v02`

**行动与关键配置**

- 在 partial manifest 结构化失败加固及新增回归落盘后，重新执行无筛选完整 `uv run pytest`；
- 测试树与当前待审计代码/文档一致，未使用 skip、xfail 或真实权重。

**结果**

- **71/71 passed**，耗时 147.31s；
- 新增 missing-asset partial manifest 用例包含在最终结果中；
- 此记录替代加固前 70/70 作为当前 P0 最终回归依据；
- 服务器阶段仍未执行，不能把本地全绿表述为 preparation、smoke 或研究 gate 已在服务器通过。

**产物路径**

- `tests/`
- `src/e1_judge/`

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 执行最终 Git diff/whitespace、untracked、协议文件 hash、禁止产物和大文件审计；
2. 写 P0 最终仓库验收记录；不 commit、不 push。

---

### 2026-08-29｜E1 v2 preparation verifier P0 最终仓库验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 15:05:21 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- Git 身份：branch=`main`；HEAD 与本地 `origin/main` 均仍为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`
- 远程环境：未连接；未 commit；未 push

**步骤 ID**

- `E1-v2-preparation-verifier-repo-acceptance-v01`

**行动与关键配置**

- 执行 `git diff --check`、`git status --short --branch`、`git diff --name-status`、`git diff --stat`、`git diff --numstat`；
- 枚举 `git ls-files --others --exclude-standard`；
- 对 `configs/e1/pilot.yaml`、runtime Qwen example 和四个 prompt YAML 执行相对 HEAD 的 `git diff --quiet`，并记录当前 SHA-256；
- 对 changed+untracked 集合扫描 `.mp4/.avi/.mov/.sqlite/.sqlite3/.db/.pt/.pth/.ckpt/.safetensors/.bin`；
- 排除 `.git/.venv/.pytest_cache/__pycache__` 后扫描工作区禁止扩展名和超过 5 MB 文件；
- 使用 `git check-ignore -v` 核对接管前已存在的 `artifacts/` E0 mock MP4/SQLite 由 `.gitignore:11` 排除，未把用户既有 artifact 误归为本次产物，也未删除或修改；
- 核对三个新增文件大小：工程文档 9,552 bytes、verifier 45,172 bytes、专项测试 13,997 bytes。

**结果**

- `git diff --check` 无 whitespace error；仅出现预期 Windows LF→CRLF 提示；
- 待交付范围为 8 个 tracked modification + 3 个 untracked source/doc/test 文件，共 11 个文件；
- 本次 changed/untracked 集合禁止实验/模型扩展名=0；超过 5 MB 文件=0；
- 全工作区超过 5 MB 文件=0；
- 工作区扫描命中的 MP4/SQLite 全部位于接管前已有且被 ignore 的 `artifacts/` mock 目录，不属于本次 P0 diff；
- 固定 pilot、runtime example 和四 prompt 相对 baseline **零 diff**；prompt SHA 仍为 `7f690446...`、`9fe3d4bb...`、`da9a25b...`、`973180e6...`；
- 最终代码验收依据为 preparation 定向 17/17、最终全量 71/71、CLI help、两条 validate 和输入 checksum 不变测试；
- 未改变 prompt、threshold、generation、model identity、30/70 split、四方法结构或最终 gate；未产生任何研究结果；未宣称服务器 phase 3/smoke DONE。

**产物路径**

- 授权/审计：`AGENTS.md`、`DEVLOG.md`
- 实现：`src/e1_judge/preparation.py`、`src/e1_judge/cli.py`
- 测试：`tests/e1/conftest.py`、`tests/e1/test_preparation.py`、`tests/e1/test_annotations.py`、`tests/e1/test_pairs_packets.py`、`tests/e1/test_scaffold.py`
- 文档：`docs/E1_A6000_RUNBOOK.md`、`docs/E1_PHASE3_ENGINEERING.md`

**问题 / 失败**

- P0 无未解决本地工程失败；现有 phase-3 builder 仍有已记录的非事务/partial-output 风险，需要 P1 atomic wrapper；
- `artifacts/` 的旧 ignored mock 文件属于用户既有状态，本次未触碰。

**下一步**

1. 向用户汇报 P0 结果、工作树 diff 和明确的未 commit/未 push 状态；
2. 建议下一开发包为 P1 atomic phase-3 preparation wrapper；开始前再次确认是否仍有真实缺口；
3. 未经用户再次明确授权，不创建 commit、不 push，不执行任何服务器操作。

---

### 2026-08-29｜E1 v2 P1 原子 phase 3 wrapper 实施授权与固定设计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:23:42 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- Git 身份：branch=`main`；HEAD 与本地 `origin/main` 均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`
- 工作树：保留已验收但未提交的 P0 修改；未发现新的用户侧冲突修改
- 远程环境：禁止使用；不连接学校服务器、不运行真实模型、不创建服务器实验目录

**步骤 ID**

- `E1-v2-atomic-phase3-wrapper-authorization-design-v01`

**行动与关键配置**

- 用户明确要求实现既定 P1 计划，并确认 P1 验收后 `e1 prepare-phase3` 是 runbook 唯一正式 phase 3 创建入口；
- CLI 固定接收 E0 plan/candidates/audit、pilot config、runtime template、现场 `MODEL_SHA256SUMS` 文件、唯一 output root 和 prepare ID；模型 manifest SHA 必须由文件现场计算，不接受手抄值；
- 固定发布布局：runtime、pairs、media packets、550 plan、preparation report、phase3 receipt、`PREPARATION_SHA256SUMS` 与 human/runs/logs 目录；
- staging/failure/final 均执行 ABSENT 门；Linux 仅允许 `renameat2(RENAME_NOREPLACE)`，Windows 使用拒绝既有目标的原子 rename；能力不可用时失败关闭；
- 已确认 staging 不能直接 rename：现有 packet builder 把绝对路径写入 manifest/metadata/plan；P1 必须重基为 final 路径、重算 packet checksum/judge key，并让 P0 verifier 通过 final→staging 物理路径映射做发布前验收；
- 固定失败语义：任一异常非零，partial staging 不删除；优先原子改名为显式 failed artifact，改名失败则保留原 staging 并准确报告；
- 固定边界：不改 prompt、threshold、generation、model revision、30/70 split、四方法或 final gate；未经再次授权不 commit、不 push。

**结果**

- P1 接口、路径语义、原子发布、失败保留、checksum/receipt 和正式 runbook 迁移方案已 decision-complete；
- 本步骤只记录实施边界，尚未修改 P1 代码；服务器 checkpoint 未改变。

**产物路径**

- `DEVLOG.md`

**问题 / 失败**

- 无身份冲突；关键绝对路径风险已纳入实现，不允许以简单目录 rename 绕过。

**下一步**

1. 扩展 P0 verifier 的内部 path mapping，同时保持公开 CLI 不变；
2. 以 tiny fixture 验证映射前后 report/文件 SHA 行为；
3. 完成后立即写独立 DEVLOG，再实现 wrapper。

---

### 2026-08-29｜E1 v2 verifier prepublish path mapping

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:25:59 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only unit/tiny fixture

**步骤 ID**

- `E1-v2-preparation-verifier-path-mapping-v01`

**行动与关键配置**

- 新增内部 `PreparationPathMapping`：保持 final declared path，不解析 symlink；只把 final root 下的声明路径映射到同布局 staging physical path；E0/repo 外部路径保持不变；
- asset original/linked video、16 frames、contact sheet、mask overlay 和 packet metadata 的存在性/SHA 读取全部支持该映射；身份比较、packet checksum 和 plan media identity 继续使用 final 声明值；
- input report 路径由 staging 重写为 final，但 SHA 从 staging 实体文件计算；
- report 新增 `verification_context`，明确区分 `direct` 与 `prepublish-staging`，并记录 declared/physical root；
- `verify_preparation` 仅增加 keyword-only 内部参数；公开 `e1 verify-preparation` CLI 及普通调用行为不变；
- 新增 final/staging/external path 双向映射回归；
- 执行 `uv run python -m py_compile src/e1_judge/preparation.py tests/e1/test_preparation.py`；
- 执行 `uv run pytest tests/e1/test_preparation.py -q`。

**结果**

- 语法检查通过；
- preparation 专项 **18/18 passed**；
- 原 P0 direct 验证、failed report、不可覆盖和只读 checksum 测试全部继续通过；
- 尚未发布任何真实 phase 3 root，未改变研究协议。

**产物路径**

- `src/e1_judge/preparation.py`
- `tests/e1/test_preparation.py`

**问题 / 失败**

- 无未解决测试失败；完整 final-path rebase/packet checksum/judge key 将由 P1 wrapper 集成测试覆盖。

**下一步**

1. 实现 phase3 orchestration、runtime materialization、路径重基和 receipt/checksum；
2. 实现 Linux/Windows no-replace publish 与失败 artifact 保留；
3. 接入 CLI 后运行 P1 定向测试。

---

### 2026-08-29｜E1 v2 atomic phase 3 wrapper 实现与定向验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:33:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；全部执行为 CPU-only tiny fixture / mock control path

**步骤 ID**

- `E1-v2-atomic-phase3-wrapper-implementation-targeted-v01`

**行动与关键配置**

- 新增 `src/e1_judge/phase3.py` 和公开 CLI `e1 prepare-phase3`；输入固定为 E0 plan/candidates/audit、pilot、runtime template、`MODEL_SHA256SUMS` 文件、output root 和 prepare ID；
- wrapper 现场计算模型 manifest 文件 SHA，只允许替换 audited runtime placeholder，并严格拒绝 backend/model/revision/path/adapter/timeout/replay 漂移；
- final/staging/failure 三重 ABSENT 门；staging/failure 使用 prepare ID，prepare ID 有严格安全字符/长度限制；
- Windows 使用拒绝既有目标的 `os.rename`；Linux 使用 libc `renameat2(RENAME_NOREPLACE)`；其他平台/缺能力时失败关闭；
- staging 内构建 runtime、100 pairs、60 media assets、100 packet、550 plan；创建 human/runs/logs 空目录；
- 将 staging 内部 video/frame/contact/mask/metadata 路径重基到 final root，重建 100 metadata 和 packet checksum，再生成 final-identity judge plan/judge key；E0 original media 路径不改；
- 使用 final→staging mapping 运行 P0 verifier，PASS 后生成 `phase3-preparation-v01.json` receipt 和覆盖全树的排序 `PREPARATION_SHA256SUMS`；
- 对 E0 三文件、10 source、50 candidate、160 mask 共 223 个外部文件在构建前、发布前和发布后复算完整 checksum inventory；任一变化失败；
- 任一发布前失败写 `PREPARATION_FAILED.json`，优先 no-replace 改名为显式 failed artifact；改名失败保留原 staging；不删除 partial；发布竞争失败者同样保留；
- CLI 成功/失败均输出结构化 JSON；失败非零并显示 stage/failure/staging/published root；
- 新增 `tests/e1/test_phase3.py`，覆盖完整 atomic happy path、发布后 direct P0 reverify、无 staging 前缀、packet/judge/checksum 复算、runtime/model manifest、外部输入不变、既有路径门、runtime drift、packet partial、同 ID 重试、no-replace 和 CLI 退出码；
- 执行 Python `py_compile`；执行 `uv run pytest tests/e1/test_phase3.py tests/e1/test_preparation.py tests/e1/test_scaffold.py -q`。

**结果**

- 语法检查通过；
- P1/P0/CLI 定向组合 **34/34 passed**；
- happy path 原子发布完整 100/550 bundle，final root direct `verify_preparation` PASS；manifest/metadata/plan/report 均不含 staging 路径；
- 100 packet checksum、550 judge key 和全树 checksum 均可复算；
- runtime model manifest SHA 精确等于传入文件 SHA；223 个外部输入前后完全一致；
- candidate SHA 故障在 `build-packets` 留下显式 failed artifact 与 partial tree，final root 保持 ABSENT，同 prepare ID 重试被拒绝；
- mock/tiny 结果仅为工程验收，不是研究测量；未改变服务器或固定协议。

**产物路径**

- `src/e1_judge/phase3.py`
- `src/e1_judge/preparation.py`
- `src/e1_judge/cli.py`
- `tests/e1/test_phase3.py`
- `tests/e1/test_preparation.py`
- `tests/e1/test_scaffold.py`

**问题 / 失败**

- 无未解决定向失败；Linux `renameat2` 尚未在本地 Windows 实际调用，已由 fail-closed 分支和服务器前正式 CPU preflight 边界约束，不能用 Windows 测试冒充 Linux 执行证据。

**下一步**

1. 用 `prepare-phase3` 替换 runbook 手工 phase 3 创建链；
2. 更新工程说明的 P1 状态、failure 命名、receipt/checksum 和 final reverify 门；
3. 执行 CLI help、两条 validate、全量 pytest 与仓库审计。

---

### 2026-08-29｜E1 v2 atomic phase 3 wrapper 文档与 CLI 验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:38:24 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only CLI/config 静态验收

**步骤 ID**

- `E1-v2-atomic-phase3-wrapper-docs-cli-v01`

**行动与关键配置**

- 将 `docs/E1_A6000_RUNBOOK.md` 的正式 phase 3 手工 `mkdir/cp/build-*` 链替换为唯一 `e1 prepare-phase3` 入口；
- 增加 final/staging/failure 三重 ABSENT、现场 `MODEL_SHA256SUMS`、wrapper exit 0、prepublish report PASS、`sha256sum -c PREPARATION_SHA256SUMS` 和 final root direct verifier 门；
- 明确同 prepare ID 不可重试、failed/staging artifact 永久保留、publish 后异常不得进入 smoke，以及当前本地未提交代码不能直接作为服务器执行依据；
- 更新 `docs/E1_PHASE3_ENGINEERING.md`：P1 标为本地已实现，记录 final-path rebase、223 外部输入复算、receipt/tree checksum、no-replace 平台语义和 prepublish 映射；保留底层 builder 的 partial 风险说明；
- 执行 `uv run e1 --help`；
- 执行 `uv run e1 prepare-phase3 --help`；
- 执行 `uv run e1 validate`；
- 执行 `uv run e1 validate --runtime configs/e1/runtime-mock.yaml`。

**结果**

- 主 CLI help 和 `prepare-phase3` help 均退出 0；8 个计划参数完整可见；
- 两条固定协议校验均退出 0；pilot config 保持有效；
- runbook 已将 wrapper 确立为唯一正式 phase 3 创建入口，smoke 前四类验收条件均显式记录；
- 工程说明不再把 P1 描述为未实现，同时没有把本地验收冒充服务器交付或 Linux 运行证据；
- 未连接服务器、未创建正式 E1 root、未加载模型。

**产物路径**

- `docs/E1_A6000_RUNBOOK.md`
- `docs/E1_PHASE3_ENGINEERING.md`
- `DEVLOG.md`

**问题 / 失败**

- 无未解决 CLI/config 失败；Linux `renameat2` 能力仍必须在未来已审计代码交付后做服务器 CPU-only preflight。

**下一步**

1. 运行完整 `uv run pytest`；
2. 完成 diff、固定协议漂移、大文件与禁止产物审计；
3. 将每个验收步骤独立写入 DEVLOG，不 commit、不 push。

---

### 2026-08-29｜E1 v2 atomic phase 3 wrapper 全量测试

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:41:09 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only unit/integration/tiny fixture

**步骤 ID**

- `E1-v2-atomic-phase3-wrapper-full-pytest-v01`

**行动与关键配置**

- 在完整 P0/P1 工作树上执行 `uv run pytest`；
- 测试范围包含 schema/config、pair/media/plan builders、runner/merge/analysis/freeze/report、P0 preparation verifier、P1 atomic wrapper、CLI help/退出码与 tiny 媒体集成路径；
- 未使用真实模型、GPU、服务器或正式实验数据输出根。

**结果**

- 完整测试 **85/85 passed**；
- 总耗时 `121.74s`；exit code 0；
- P1 新增测试与全部既有回归同时通过，无跳过的已知失败、无中断。

**产物路径**

- 测试源码：`tests/e1/`
- 实现源码：`src/e1_judge/`
- 测试临时目录由 pytest 管理，未写入正式 E1 root。

**问题 / 失败**

- 无。

**下一步**

1. 执行 `git diff --check` 和状态/差异审计；
2. 确认固定 protocol/prompt/runtime identity 文件零漂移；
3. 审计大文件与禁止生成物后写最终验收 DEVLOG。

---

### 2026-08-29｜E1 v2 runbook preparation 重试身份消歧

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:43:39 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；文档静态审计

**步骤 ID**

- `E1-v2-phase3-prepare-id-retry-doc-clarification-v01`

**行动与关键配置**

- 在最终 runbook 审计中发现顶部旧泛化表述“失败重试仍使用同一身份和 cache”可能与 P1 的同 prepare ID 禁止重试规则产生歧义；
- 将其严格限定为 Judge job 的同实验身份/cache 重试；phase 3 preparation 失败明确跳转第 5 节，保留现场并使用新的 prepare ID；
- 执行 `rg` 交叉检查顶部规则与第 5 节 failure 规则；
- 执行 `git diff --check -- docs/E1_A6000_RUNBOOK.md docs/E1_PHASE3_ENGINEERING.md`。

**结果**

- 顶部停止规则与第 5 节现均明确：同一 prepare ID 永久不可重试，恢复使用新 ID；
- 文档 diff check 退出 0，仅有 Windows 工作树 LF→CRLF 提示，无 whitespace error；
- 不改变研究协议、实验身份或代码行为。

**产物路径**

- `docs/E1_A6000_RUNBOOK.md`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 重新执行最终仓库审计以纳入本条 DEVLOG 与文档修正；
2. 记录最终状态，不 commit、不 push。

---

### 2026-08-29｜E1 v2 atomic phase 3 wrapper 最终仓库审计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 20:44:17 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；只读 Git/文件系统审计

**步骤 ID**

- `E1-v2-atomic-phase3-wrapper-final-repository-audit-v01`

**行动与关键配置**

- 执行 `git diff --check`；
- 对 `configs/e1/pilot.yaml`、固定 runtime template 和四个固定 prompt YAML 逐文件执行 `git diff --quiet`；
- 合并 tracked diff 与 non-ignored untracked 路径，审计模型 checkpoint、视频、图片、NumPy/Parquet 等禁止产物扩展名；
- 递归审计工作区中大于 5 MiB 的文件，排除 `.git`、`.venv`、pytest/cache 和既有 ignored `artifacts`；
- 核对 `HEAD` 与本地 `refs/remotes/origin/main`，并记录最终 `git status --short`；未执行 fetch/pull/push。

**结果**

- `git diff --check` exit 0；仅出现既有 Windows LF→CRLF 工作树提示，无 whitespace error；
- 固定 protocol/runtime/prompt identity 漂移数 **0**；
- 变更与 non-ignored untracked 路径共 **13** 个，均为授权范围内现有 P0/P1 code/test/docs/DEVLOG/AGENTS 工作树内容；
- 禁止产物扩展名数 **0**；排除既有缓存/ignored artifact 后，大于 5 MiB 文件数 **0**；
- `HEAD` 与本地 `origin/main` 均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`，证明本次未创建 commit；
- 服务器未连接，未创建/修改正式 E1 输出，未 commit、未 push。

**产物路径**

- 审计记录：`DEVLOG.md`
- P1 实现：`src/e1_judge/phase3.py`、`src/e1_judge/preparation.py`、`src/e1_judge/cli.py`
- P1 测试：`tests/e1/test_phase3.py`、`tests/e1/test_preparation.py`
- 文档：`docs/E1_A6000_RUNBOOK.md`、`docs/E1_PHASE3_ENGINEERING.md`

**问题 / 失败**

- 无未解决本地验收失败；Linux `renameat2(RENAME_NOREPLACE)` 未在 Windows 本机实际执行，必须在未来已审计代码交付后的服务器 CPU-only preflight 中验证，不能把本地 Windows 结果冒充该平台证据。

**下一步**

1. 保持当前未提交工作树供用户审阅；
2. 不连接服务器、不 commit、不 push；
3. 经用户后续明确授权后再进行独立的交付/服务器 preflight。

---

### 2026-08-29｜E1 P0/P1 发布与本地 E2 CPU-only 工程授权

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:09:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- Git 身份：branch=`main`；HEAD 与本地 `origin/main` 均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`
- 远程实验环境：未连接；未访问 DATA4；未加载模型或使用 GPU

**步骤 ID**

- `E1-E2-local-publication-engineering-authorization-v01`

**行动与关键配置**

- 用户明确授权将当前已验收的 E1 preparation verifier / atomic phase 3 wrapper 形成审计提交并普通推送到 `main`，禁止 force-push；
- 用户明确授权按批准计划在本地开展完整 E2 Best-of-N CPU-only 工程，并按独立里程碑审计、提交、普通推送到 `main`；
- 本地允许范围固定为 tiny fixture、mock/replay、fake command adapter、静态检查、CPU 测试、文档、报告和 DEVLOG；
- 学校服务器、DATA4、Linux 现场检查、真实候选生成、真实 Judge、正式服务器标注数据、GPU 和远程实验根全部交付服务器端 agent 执行；本地 Codex 不连接、不操作；
- E1 未产生合法 `PASS_PROVISIONAL` 与 `reward-v0.yaml` 前，E2 只能形成工程和合成验收，不得产生或宣称正式研究测量；不进入 E3/DPO；
- 在 `AGENTS.md` 固化上述授权与边界。

**结果**

- 当前 E1 发布权限、E2 本地工程范围、分阶段 `main` 推送策略和服务器端职责分界均已明确；
- 未改变 E0 数据、E1 prompt/threshold/model/split/gate，未运行实验。

**产物路径**

- `AGENTS.md`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 更新 E1 runbook，使正式 preparation PASS 后可在 GPU smoke 前启动两名主标注者，同时保持 Judge dev/frozen 必须等待 smoke；
2. 重新执行完整本地验收和仓库审计；
3. 审计通过后创建并普通推送 E1 P0/P1 基线提交。

---

### 2026-08-29｜E1 preparation PASS 后前移正式人标顺序

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:12:00 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未连接；仅修改本地执行手册

**步骤 ID**

- `E1-v2-preparation-before-smoke-annotation-order-v01`

**行动与关键配置**

- 更新 `docs/E1_A6000_RUNBOOK.md`：正式 phase 3 preparation 的 wrapper、prepublish report、direct verifier 与全树 checksum 全部 PASS 后，允许两名主标注者在真实 Judge smoke 前开始 100-pair 盲标；
- 固定前移条件：两份主标注输出必须 ABSENT，标注者不得看到任何 Judge 结果，preparation 身份/SHA 必须先写 DEVLOG，DATA4 服务与标注文件只由服务器端 agent 操作；
- 明确 smoke 仍是 dev/frozen Judge 的硬门；smoke 失败时不得运行 dev。仅当 pair、媒体 checksum 和标注协议不变时，已开始的盲标才可保留/继续；相关身份改变时必须停止并重新判断有效性；
- 此调整只改变两个独立任务的执行顺序，不改变样本、pair、30/70 split、标注协议、prompt、threshold、model identity 或 final gate。

**结果**

- GPU 被占用期间可并行推进正式人工标签，不会把人标进度误报为 Judge smoke 或研究 gate 通过；
- 第 8 节已明确可在第 7 节前执行，第 9 节仍显式要求 smoke PASS。

**产物路径**

- `docs/E1_A6000_RUNBOOK.md`
- `DEVLOG.md`

**问题 / 失败**

- 无；服务器端实际 preparation、人标和 smoke 均未执行。

**下一步**

1. 运行 E1 P0/P1 完整本地回归、CLI/config 校验；
2. 完成协议身份和仓库卫生审计；
3. 审计通过后创建并推送 E1 基线提交。

---

### 2026-08-29｜E1 P0/P1 发布前完整本地回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:13:01 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only pytest/tiny fixture/mock/fake command adapter

**步骤 ID**

- `E1-v2-P0-P1-prepublish-full-pytest-v01`

**行动与关键配置**

- 在当前 E1 preparation verifier、atomic phase 3 wrapper、新授权和人标顺序文档工作树上执行无筛选完整命令 `uv run pytest`；
- 未使用真实模型、GPU、服务器、DATA4、skip 或已知失败豁免。

**结果**

- **85/85 passed**，耗时 `119.78s`，exit code 0；
- E0、E1 schema/pairs/media、runner/cache、标注/裁决、metrics/freeze/gate/report、P0 verifier、P1 atomic wrapper 和 CLI 回归同时通过；
- 文档顺序调整未改变任何代码测试结果。

**产物路径**

- `tests/`
- `src/e1_judge/`

**问题 / 失败**

- 无。

**下一步**

1. 执行 E1 主 CLI、`prepare-phase3` help 和两条 config/runtime validate；
2. 完成协议 identity、Git diff、禁止产物与大文件审计；
3. 审计通过后发布基线。

---

### 2026-08-29｜E1 P0/P1 发布前 CLI 与配置验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:13:23 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only CLI/config 静态验收

**步骤 ID**

- `E1-v2-P0-P1-prepublish-cli-config-v01`

**行动与关键配置**

- 执行 `uv run e1 --help`；
- 执行 `uv run e1 prepare-phase3 --help`；
- 执行 `uv run e1 validate`；
- 执行 `uv run e1 validate --runtime configs/e1/runtime-mock.yaml`。

**结果**

- 四条命令均 exit 0；
- 主 CLI 显示 `prepare-phase3` 与 `verify-preparation`，`prepare-phase3` 的8个正式参数完整；
- 固定 E1 pilot 与 mock runtime 均继续通过严格校验；
- 未加载模型、未产生研究结果。

**产物路径**

- `src/e1_judge/cli.py`
- `configs/e1/`

**问题 / 失败**

- 无。

**下一步**

1. 执行最终协议 identity 与仓库卫生审计；
2. fetch 并确认 `origin/main` 未前进；
3. 创建 E1 P0/P1 审计提交并普通推送。

---

### 2026-08-29｜E1 P0/P1 最终仓库审计首次脚本失败

**状态：FAILED（已定位，未改变仓库）**

**时间与环境**

- 失败时间：2026-08-29 22:13:56 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E1-v2-P0-P1-final-repo-audit-attempt-01`

**行动与关键配置**

- 尝试用单个只读 PowerShell 脚本执行 `git diff --check`、固定协议漂移、pending 路径、禁止扩展名、大文件和 prompt SHA 审计；
- 脚本在 `Where-Object` 内把外部命令与 `$LASTEXITCODE` 放入括号表达式，PowerShell parser 在命令执行前拒绝。

**结果**

- exit code 非零；错误为 `ParserError: Missing closing ')' in expression`；
- 失败发生在解析阶段，未执行审计命令，未修改任何文件或 Git 状态；
- 诊断表明需把逐文件 `git diff --quiet` 改为显式 `foreach` 循环。

**产物路径**

- 仅本 DEVLOG 诊断记录；无审计产物。

**问题 / 失败**

- PowerShell 组合表达式语法无效；不是代码或协议失败。

**下一步**

1. 使用显式循环重跑同一只读仓库审计；
2. 审计通过后记录最终结果；
3. 再执行 fetch/发布。

---

### 2026-08-29｜E1 P0/P1 最终仓库审计重跑通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:14:28 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程实验环境：未使用；只读 Git/文件系统审计

**步骤 ID**

- `E1-v2-P0-P1-final-repo-audit-attempt-02`

**行动与关键配置**

- 使用显式 PowerShell `foreach` 修正首次脚本语法问题并重跑 `git diff --check`；
- 对 pilot、Qwen runtime template 和四个 prompt 执行相对 HEAD 的逐文件零漂移检查；
- 合并 tracked diff 与 non-ignored untracked 路径，扫描视频、数据库、模型权重、NumPy/Parquet 等禁止扩展名；
- 排除 `.git/.venv/.pytest_cache/__pycache__/artifacts` 后扫描超过 5 MiB 文件；
- 记录四个 prompt 当前 SHA-256 和待提交路径集合。

**结果**

- `git diff --check` exit 0，仅有 Windows LF→CRLF 提示，无 whitespace error；
- pending 路径恰为 **13** 个预期 E1 code/test/docs/AGENTS/DEVLOG 文件；
- 固定 protocol/runtime/prompt identity 漂移数 0；禁止 pending 产物数 0；大于 5 MiB 文件数 0；
- prompt SHA 仍为 `7f690446...`、`9fe3d4bb...`、`da9a25b...`、`973180e6...`；
- HEAD 与本地 `origin/main` 均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`。

**产物路径**

- `AGENTS.md`
- `DEVLOG.md`
- `docs/E1_A6000_RUNBOOK.md`
- `docs/E1_PHASE3_ENGINEERING.md`
- `src/e1_judge/`
- `tests/e1/`

**问题 / 失败**

- 无未解决审计失败；首次 PowerShell parser 失败已由本次成功重跑闭环。

**下一步**

1. 执行 `git fetch origin` 并重新确认远端未前进；
2. 创建 E1 P0/P1 实现基线提交；
3. 普通推送到 `main`，随后写发布记录。

---

### 2026-08-29｜E1 P0/P1 发布前远端身份确认

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:14:56 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远端：GitHub `origin`
- 远程实验环境：未连接

**步骤 ID**

- `E1-v2-P0-P1-prepublish-origin-identity-v01`

**行动与关键配置**

- 执行 `git fetch origin`；
- 读取本地 HEAD、`refs/remotes/origin/main` 和 `git status --short --branch`；
- 未执行 pull、rebase、reset、merge 或服务器操作。

**结果**

- fetch 成功；
- 本地 HEAD 与最新 `origin/main` 仍均为 `89a8a7279bc1bdaf2bb4196e02971f349129b5ab`，不存在并发前进；
- branch=`main`，待提交集合仍为已审计的13个 E1 路径。

**产物路径**

- Git remote-tracking ref `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无远端冲突。

**下一步**

1. 创建 `Add atomic E1 phase 3 preparation` 实现提交；
2. 普通推送到 `origin/main`；
3. 追加发布结果并形成 DEVLOG-only 审计提交。

---

### 2026-08-29｜E1 P0/P1 实现基线提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:15:21 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程实验环境：未使用

**步骤 ID**

- `E1-v2-P0-P1-implementation-commit-v01`

**行动与关键配置**

- 将最终审计通过的13个 E1 P0/P1 code/test/docs/authorization/DEVLOG 路径显式加入 index；
- 使用提交信息 `Add atomic E1 phase 3 preparation` 创建本地提交；
- 未使用 amend、rebase、reset 或历史重写。

**结果**

- 实现 commit：`cb5d4ffaf95ef230df4762d73813181f6c5cef1c`；
- 13 files changed，3935 insertions，33 deletions；新增 preparation verifier、atomic phase 3 wrapper、工程说明和两组专项测试；
- 本地 `main` 相对 `origin/main` ahead 1；本记录是提交后的唯一新工作树修改。

**产物路径**

- Git commit `cb5d4ffaf95ef230df4762d73813181f6c5cef1c`
- `DEVLOG.md`

**问题 / 失败**

- 无提交失败。

**下一步**

1. 普通推送 `main` 到 `origin`；
2. 核对远端与本地 commit；
3. 写发布结果并形成 DEVLOG-only 提交。

---

### 2026-08-29｜E1 P0/P1 实现基线发布

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:15:44 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 发布目标：GitHub `origin/main`
- 远程实验环境：未连接；未访问 DATA4

**步骤 ID**

- `E1-v2-P0-P1-implementation-publish-v01`

**行动与关键配置**

- 执行普通 `git push origin main`；
- 未使用 force、force-with-lease、rebase、reset 或历史重写；
- push 后读取本地 HEAD、本地 remote-tracking `origin/main` 和 branch status。

**结果**

- push 成功：`origin/main` 从 `89a8a727...` 前进到 `cb5d4ffaf95ef230df4762d73813181f6c5cef1c`；
- 本地 HEAD 与 `origin/main` 精确一致；
- 发布依据为 85/85 full pytest、CLI/help、两条 validate、固定协议零漂移和仓库卫生审计；
- push 后唯一工作树修改为本条发布 DEVLOG 记录。

**产物路径**

- Git commit `cb5d4ffaf95ef230df4762d73813181f6c5cef1c`
- GitHub `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无 push 失败或分支冲突。

**下一步**

1. 创建并推送 DEVLOG-only 发布记录提交；
2. 确认工作树干净；
3. 开始 E2 milestone 1 的固定协议与本地 CPU-only 实现。

---

### 2026-08-29｜E1 P0/P1 DEVLOG-only 发布记录提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:16:12 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程实验环境：未使用

**步骤 ID**

- `E1-v2-P0-P1-publication-devlog-commit-v01`

**行动与关键配置**

- 将实现 commit 与 push 结果的发布记录加入 `DEVLOG.md`；
- 使用提交信息 `Record E1 phase 3 baseline publication` 创建 DEVLOG-only 提交；
- 未 amend 或重写已发布实现 commit。

**结果**

- DEVLOG-only commit：`4c70b162824ed4decab1dec8c869c3dc7a07d443`；
- 本地 `main` 相对 `origin/main` ahead 1；本记录是提交后的唯一工作树修改。

**产物路径**

- Git commit `4c70b162824ed4decab1dec8c869c3dc7a07d443`
- `DEVLOG.md`

**问题 / 失败**

- 无提交失败。

**下一步**

1. 普通推送 DEVLOG-only commit；
2. 核对远端一致性；
3. 开始 E2 milestone 1。

---

### 2026-08-29｜E1 P0/P1 DEVLOG-only 提交发布完成

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:16:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 发布目标：GitHub `origin/main`
- 远程实验环境：未连接

**步骤 ID**

- `E1-v2-P0-P1-publication-devlog-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main` 发布 DEVLOG-only commit；
- push 后核对本地 HEAD、`origin/main` 和 branch status。

**结果**

- push 成功：`origin/main` 从 `cb5d4ff...` 前进到 `4c70b162824ed4decab1dec8c869c3dc7a07d443`；
- 本地 HEAD 与 `origin/main` 精确一致；
- 本记录是 E2 milestone 1 开始前唯一未提交工作树修改。

**产物路径**

- Git commit `4c70b162824ed4decab1dec8c869c3dc7a07d443`
- GitHub `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 固定 E2 milestone 1 schema/config/generation-extension/pool/audit 设计；
2. 实现本地 CPU-only 代码与 tiny fixture 测试；
3. 验收并分阶段推送 `main`。

---

### 2026-08-29｜E2 milestone 1 固定协议与接口设计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:17:00 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；设计仅面向本地 CPU-only 工程和未来服务器端 agent 交付

**步骤 ID**

- `E2-bon-m1-protocol-interface-design-v01`

**行动与关键配置**

- 固定 E2 pilot schema v1：DAVIS-2017 train 当前10输入；base seeds=`101/202/303/404/505`，extension seeds=`606/707/808`，每输入8候选；N=`1/2/4/8`；8轮 balanced-cyclic；
- 固定 milestone 1 公共接口：`e2 validate`、`e2 plan-generation`、`e2 build-pool`；分别负责严格配置、30任务扩展计划和80候选不可变池；
- `plan-generation` 以 E0 plan 为唯一生成身份来源，只允许 seed/artifact path/generation key/code snapshot 改变；模型、AnyV2V commit、图像编辑器、分辨率、帧数、fps、inversion/PnP/CFG 等语义配置必须继承；
- `build-pool` 强制 E0 plan/candidates/audit 为50唯一候选，extension plan/candidates/audit 为30唯一候选；每输入8 seeds 精确一致，全部 succeeded、audit usable、视频 checksum 64hex 且实际文件 SHA 可选严格复算；
- E0 50候选与原 audit 保持只读，新增30候选使用独立 extension root/audit；pool 输出已存在即拒绝，采用原子无覆盖文件发布；
- 固定后续接口契约：正式 E2 必须等待 E1 `PASS_PROVISIONAL`/`reward-v0`，milestone 1 只产生计划和合成工程证据；
- 固定职责：本地实现/tests/docs，不访问 DATA4；真实 extension 计划执行、30候选生成、audit 与 pool 构建由服务器端 agent 在唯一目录完成。

**结果**

- milestone 1 的输入、输出、计数、身份、失败关闭和本地/服务器边界已 decision-complete；
- 未修改 E0/E1 协议或数据，未生成候选，未运行模型。

**产物路径**

- `DEVLOG.md`
- 计划新增：`configs/e2/`、`src/e2_bon/`、`tests/e2/`

**问题 / 失败**

- 当前真实 E0 每输入只有5候选；新增30候选仍需要未来服务器 GPU。本地只用 tiny fixture 验证8候选协议。

**下一步**

1. 实现 E2 strict models/config validation；
2. 实现 generation extension planner 与80-candidate pool builder；
3. 接入独立 `e2` CLI 并运行 milestone 1 定向测试。

---

### 2026-08-29｜E2 milestone 1 实现与定向验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:21:32 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only tiny fixture

**步骤 ID**

- `E2-bon-m1-implementation-targeted-v01`

**行动与关键配置**

- 新增独立 `e2` CLI/package 和固定 `configs/e2/pilot.yaml`，接入 pyproject console script 与 wheel package；
- 实现 strict `E2ConfigV1`、`PoolCandidateV1`、`CandidatePoolV1`，拒绝额外字段和固定协议漂移；
- 实现 `e2 validate`：E2 dataset/split/base seeds/sample order 必须与 `configs/w1_manifest.yaml` 精确一致；
- 实现 `e2 plan-generation`：从10 inversion/50 E0 task 继承全部 input/generation 语义，只生成 seeds 606/707/808 的30个 W1-runner-compatible task；
- 实现 `e2 build-pool`：合并50+30 plan/candidate/audit，严格检查80唯一 ID、8 seeds/sample、全部 succeeded/usable、task/config/key、16 frame 和视频/帧 SHA，并原子无覆盖写 candidate pool；
- 新增同目录 hard-link 原子无覆盖 JSON helper；
- 新增 tiny fixture 和5条专项测试，覆盖30任务、语义漂移、80候选 happy path、checksum/audit corruption、不可覆盖和 CLI help/validate；
- 执行 `py_compile` 和 `uv run pytest tests/e2 -q`。

**结果**

- 语法检查通过；E2 milestone 1 专项 **5/5 passed**；
- fixture 仅写 pytest 临时目录，使用假视频/PNG 字节和 mock generation config；
- `uv` 因缓存与环境 hardlink 不可用回退 copy，只是安装性能 warning，不影响代码原子发布测试；
- 未访问 DATA4、未生成真实候选、未产生 E2 研究测量。

**产物路径**

- `configs/e2/pilot.yaml`
- `src/e2_bon/`
- `tests/e2/`
- `pyproject.toml`

**问题 / 失败**

- 无未解决定向失败；真实 extension 仍需服务器端 agent 在 GPU 可用时执行。

**下一步**

1. 执行 `e2` CLI help/validate；
2. 运行完整 pytest 确认 E0/E1 零回归；
3. 完成 milestone 1 仓库审计并发布。

---

### 2026-08-29｜E2 milestone 1 CLI 与固定配置验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:22:01 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only CLI/config 验收

**步骤 ID**

- `E2-bon-m1-cli-config-v01`

**行动与关键配置**

- 执行 `uv run e2 --help`；
- 执行 `uv run e2 validate`，默认读取 `configs/e2/pilot.yaml` 与 `configs/w1_manifest.yaml`。

**结果**

- 两条命令 exit 0；
- CLI 显示 `validate/plan-generation/build-pool` 三个 milestone 1 命令；
- validate 返回 `valid=true`、`experiment_id=E2-bon-pilot-v01`、`candidates=80`；
- 固定10 sample 顺序与五个 E0 base seeds 精确匹配 W1 manifest。

**产物路径**

- `configs/e2/pilot.yaml`
- `src/e2_bon/cli.py`

**问题 / 失败**

- 无。

**下一步**

1. 运行无筛选完整 pytest；
2. 审计 pending 路径、协议漂移、禁止产物和大文件；
3. 发布 milestone 1。

---

### 2026-08-29｜E2 milestone 1 全量本地回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:24:50 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only full pytest

**步骤 ID**

- `E2-bon-m1-full-pytest-v01`

**行动与关键配置**

- 在完整 E1 已发布基线 + E2 milestone 1 工作树上执行无筛选 `uv run pytest`；
- 未使用 GPU、服务器、DATA4、真实模型、skip 或 xfail。

**结果**

- 完整测试 **90/90 passed**，耗时 `142.02s`，exit code 0；
- 新增5条 E2 测试与既有85条 E0/E1 回归同时通过；
- 当前 E2 结果仅证明 schema/planner/pool 工程正确，不是候选生成或 Best-of-N 研究测量。

**产物路径**

- `tests/`
- `src/e2_bon/`

**问题 / 失败**

- 无。

**下一步**

1. 执行 milestone 1 Git/协议/禁止产物/大文件审计；
2. fetch 并确认 `origin/main` 未前进；
3. 创建并发布 milestone 1 实现基线和 DEVLOG-only 记录。

---

### 2026-08-29｜E2 milestone 1 最终仓库审计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:25:22 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；只读 Git/文件系统审计

**步骤 ID**

- `E2-bon-m1-final-repository-audit-v01`

**行动与关键配置**

- 执行 `git diff --check`；
- 对 W1 manifest、E1 pilot/runtime/四 prompt 执行相对 HEAD 的零漂移检查；
- 合并 tracked diff 与 non-ignored untracked 路径，扫描视频/数据库/模型/NumPy/Parquet 禁止扩展名；
- 排除仓库元数据、虚拟环境、pytest/cache 和既有 ignored artifacts 后扫描超过 5 MiB 文件；
- 核对 HEAD、`origin/main` 和完整 pending 集合。

**结果**

- `git diff --check` exit 0，仅有预期 LF→CRLF 提示；
- pending 恰为 **11** 个 E2 config/code/test、pyproject 和逐步 DEVLOG 文件；
- W1/E1 固定 identity 漂移数 0；禁止产物数 0；超过 5 MiB 文件数 0；
- HEAD 与 `origin/main` 均为 `4c70b162824ed4decab1dec8c869c3dc7a07d443`。

**产物路径**

- `configs/e2/pilot.yaml`
- `src/e2_bon/`
- `tests/e2/`
- `pyproject.toml`
- `DEVLOG.md`

**问题 / 失败**

- 无未解决审计失败。

**下一步**

1. fetch 并确认远端未前进；
2. 创建并普通推送 milestone 1 实现提交；
3. 追加并发布 DEVLOG-only 记录。

---

### 2026-08-29｜E2 milestone 1 发布前远端身份确认

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:25:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远端：GitHub `origin`

**步骤 ID**

- `E2-bon-m1-prepublish-origin-identity-v01`

**行动与关键配置**

- 执行 `git fetch origin` 并读取 HEAD 与 `origin/main`；
- 未执行合并、变基或历史重写。

**结果**

- fetch 成功；HEAD 与最新 `origin/main` 均为 `4c70b162824ed4decab1dec8c869c3dc7a07d443`；
- 无并发前进，允许发布已审计 milestone 1。

**产物路径**

- Git remote-tracking ref `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 创建 milestone 1 实现提交；
2. 普通推送 `main`；
3. 写发布记录。

---

### 2026-08-29｜E2 milestone 1 实现基线提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:26:09 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程实验环境：未使用

**步骤 ID**

- `E2-bon-m1-implementation-commit-v01`

**行动与关键配置**

- 将已验收的 E2 config/schema/generation planner/pool builder/CLI/tests 和逐步 DEVLOG 显式加入 index；
- 使用提交信息 `Add E2 candidate pool planning` 创建实现提交。

**结果**

- commit：`6d8c4a2dbc87956e2c059804ac56537102381657`；
- 11 files changed，1063 insertions，1 deletion；
- 本地 `main` ahead 1；本记录是提交后的唯一工作树修改。

**产物路径**

- Git commit `6d8c4a2dbc87956e2c059804ac56537102381657`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送实现 commit；
2. 记录远端一致性；
3. 创建 DEVLOG-only 发布提交。

---

### 2026-08-29｜E2 milestone 1 实现基线发布

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:26:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 发布目标：GitHub `origin/main`
- 远程实验环境：未连接

**步骤 ID**

- `E2-bon-m1-implementation-publish-v01`

**行动与关键配置**

- 普通执行 `git push origin main`；
- push 后核对 HEAD 与 `origin/main`。

**结果**

- push 成功：`origin/main` 从 `4c70b16...` 前进到 `6d8c4a2dbc87956e2c059804ac56537102381657`；
- 本地 HEAD 与 remote-tracking ref 一致；
- 发布依据为 E2 定向5/5、全量90/90、CLI/validate 和仓库审计。

**产物路径**

- Git commit `6d8c4a2dbc87956e2c059804ac56537102381657`
- GitHub `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 创建并推送 DEVLOG-only 发布提交；
2. 固定 milestone 2 preparation/runner/rubric qualification 设计；
3. 开始本地 CPU-only 实现。

---

### 2026-08-29｜E2 milestone 1 DEVLOG-only 发布提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:26:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`

**步骤 ID**

- `E2-bon-m1-publication-devlog-commit-v01`

**行动与关键配置**

- 使用 `Record E2 milestone 1 publication` 创建 DEVLOG-only 提交。

**结果**

- commit：`c941ee496d0e39a1196ee4bfe629cc197624f186`；本地 main ahead 1。

**产物路径**

- Git commit `c941ee496d0e39a1196ee4bfe629cc197624f186`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送该提交；
2. 核对远端一致性；
3. 开始 milestone 2。

---

### 2026-08-29｜E2 milestone 1 DEVLOG-only 发布完成

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:27:29 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 发布目标：GitHub `origin/main`

**步骤 ID**

- `E2-bon-m1-publication-devlog-push-v01`

**行动与关键配置**

- 普通推送 `c941ee496d0e39a1196ee4bfe629cc197624f186` 到 `origin/main` 并核对 refs。

**结果**

- push 成功；本地 HEAD 与 `origin/main` 精确一致；
- 本记录是 milestone 2 开始前唯一未提交修改。

**产物路径**

- GitHub `origin/main`
- `DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 记录 milestone 2 固定设计；
2. 实现 preparation/runner/rubric qualification；
3. 完成本地验收和分阶段发布。

---

### 2026-08-29｜E2 milestone 2 preparation、runner 与 rubric 资格设计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:28:00 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；本步骤为 CPU-only 工程设计

**步骤 ID**

- `E2-bon-m2-preparation-runner-qualification-design-v01`

**行动与关键配置**

- 固定 `e2 prepare` 输入：80 candidate pool、E2 config、E1 `decision.json`、`reward-v0.yaml`、frozen config/protocol/runtime、可选 `auxiliary-rubric-v0.yaml`、唯一 output root 和 prepare ID；
- 准备前硬门固定为 E1 decision=`PASS_PROVISIONAL`、reward provisional=true、selected method/model/prompt/parser/runtime/protocol identity 互相一致；任一不符失败关闭；
- 固定80候选构造280无序 pair、10 source/80 candidate asset、280 packet、8轮×10 sample=80 design trial；primary swap plan 精确560请求；
- selected method 为 rubric 时分维度直接复用 primary；selected method 为 pairwise 时，只有独立 `auxiliary-rubric-v0` PASS 才生成额外560 rubric 请求，否则后续多目标状态必须 `NOT_APPLICABLE`；
- `e2 qualify-rubric` 固定使用 E1 frozen 70 pair、两人/第三人 adjudicated labels、140个 rubric swap result 和 dev metrics 中预先选择的 rubric threshold，执行 E1 同一 accuracy/swap/coverage/category 四门；PASS/FAIL 均原子写审计 artifact，绝不替换 `reward-v0`；
- 新 E2 request/result 使用 `split=e2-pilot` 与 stage=`primary/auxiliary-rubric`，不扩宽 E1 Pydantic split；E2 runner 复用相同 backend/runtime/cache/envelope 语义但使用独立 `.e2-run.lock`；
- preparation 使用同文件系统 staging、failed artifact、final 三重 ABSENT 和 Linux/Windows no-replace publish；内部 manifest 声明 final 路径，prepublish verifier 通过 final→staging 物理映射验收；
- 正式 command/runtime 只能由服务器端 agent 执行；本地只运行 mock/fake adapter，summary 必须标记 `research_measurements=0`。

**结果**

- milestone 2 的依赖门、精确计数、plan identity、辅助 rubric 边界、runner 契约、原子失败语义与服务器职责已固定；
- 未运行真实 Judge、未创建 DATA4 输出。

**产物路径**

- `DEVLOG.md`
- 计划扩展：`src/e2_bon/`、`tests/e2/`、`e2` CLI

**问题 / 失败**

- pairwise 主方法本身无四维输出；若 auxiliary rubric 未通过同等级资格门，多目标分析只能诚实输出不可用。

**下一步**

1. 实现 E2 pair/request/result/design schema 和 preparation；
2. 实现独立 runner 与 rubric qualification；
3. 执行定向 mock/atomic/gate 测试。

---

### 2026-08-29｜E2 milestone 2 首轮定向测试夹具失败

**状态：FAILED（已定位）**

**时间与环境**

- 失败时间：2026-08-29 22:38:56 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/mock

**步骤 ID**

- `E2-bon-m2-targeted-attempt-01`

**行动与关键配置**

- 完成 E2 pair/design/request/result schema、atomic preparation、独立 runner、rubric qualification、CLI 和4条 milestone 2 测试；
- 执行 `py_compile`；
- 执行 `uv run pytest tests/e2/test_m1.py tests/e2/test_m2.py -q`。

**结果**

- 语法检查通过；9个组合用例中8个通过、1个失败；
- preparation 280 pair/80 trial/560 plan、mock runner 560 cache、E1 gate failure preservation 等路径已通过；
- 唯一失败位于 rubric qualification 测试辅助函数 `_write_jsonl`：目标 `tmp/.../good/` 未在写入前创建，触发 `FileNotFoundError`；
- 失败发生在构造测试输入阶段，尚未进入 qualification 实现，不代表指标或 gate 逻辑失败。

**产物路径**

- `src/e2_bon/preparation.py`
- `src/e2_bon/runner.py`
- `src/e2_bon/qualification.py`
- `tests/e2/test_m2.py`

**问题 / 失败**

- 测试 JSONL helper 缺少 `path.parent.mkdir(parents=True, exist_ok=True)`。

**下一步**

1. 修复测试 helper 创建父目录；
2. 重跑 milestone 2 定向组合；
3. 若仍失败，逐项记录并修复。

---

### 2026-08-29｜E2 milestone 2 定向验收重跑通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:40:56 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/mock

**步骤 ID**

- `E2-bon-m2-targeted-attempt-02`

**行动与关键配置**

- 在测试 JSONL helper 中增加父目录创建；
- 原命令重跑 `uv run pytest tests/e2/test_m1.py tests/e2/test_m2.py -q`。

**结果**

- milestone 1+2 定向组合 **9/9 passed**；
- 280 pair、80 balanced trial、560 primary request、final 路径声明、atomic publish/ABSENT、mock 560/560、第二次560 cache hit、research_measurements=0、E1 FAIL failed artifact、rubric qualification PASS/category FAIL 均通过；
- 首次 fixture 失败已闭环，无未解决定向失败。

**产物路径**

- `src/e2_bon/`
- `tests/e2/`

**问题 / 失败**

- 无。

**下一步**

1. 增加 pairwise-primary + qualified auxiliary-rubric 560计划专项；
2. 执行 E2 CLI/help 和完整 pytest；
3. 完成 milestone 2 审计发布。

---

### 2026-08-29｜E2 pairwise primary 与 qualified rubric 双计划验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:42:49 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only tiny fixture

**步骤 ID**

- `E2-bon-m2-pairwise-auxiliary-plan-v01`

**行动与关键配置**

- 增加专项测试覆盖 E1 selected method=`pairwise-swap-v1`；
- 无 auxiliary artifact 时 preparation 必须发布 primary 560 plan、标记 `NOT_APPLICABLE` 且不生成 rubric plan；
- 提供与 E1 protocol fingerprint 匹配的 `PASS_AUXILIARY_RUBRIC` artifact 时，必须同时生成560 primary pairwise 和560 auxiliary rubric 请求；
- 运行单项 pytest。

**结果**

- 专项 **1/1 passed**；
- primary/auxiliary method、stage、请求数与 artifact gate 均符合固定设计；
- 未经资格门的 rubric 不会被静默用于多目标分析。

**产物路径**

- `tests/e2/test_m2.py`
- `src/e2_bon/preparation.py`

**问题 / 失败**

- 无。

**下一步**

1. 执行 E2 CLI help/prepare/run/qualify help；
2. 运行完整 pytest；
3. 完成仓库审计和 milestone 2 发布。

---

### 2026-08-29｜E2 milestone 2 CLI 与配置验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-29 22:43:23 +08:00
- 执行位置：本地 Windows 工作区 `D:\lab idea`
- 远程环境：未使用；CPU-only CLI/config

**步骤 ID**

- `E2-bon-m2-cli-config-v01`

**行动与关键配置**

- 执行 `e2 --help`、`e2 prepare --help`、`e2 run --help`、`e2 qualify-rubric --help` 和 `e2 validate`。

**结果**

- 五条命令均 exit 0；
- 主 CLI 显示 milestone 1+2 共7个命令；
- prepare 的 pool/E1 gate/frozen/runtime/output/prepare-id/auxiliary 参数完整；run 与 rubric qualification 参数完整；
- E2 fixed config 继续返回 valid=true、80 candidates。

**产物路径**

- `src/e2_bon/cli.py`
- `configs/e2/pilot.yaml`

**问题 / 失败**

- 无。

**下一步**

1. 运行完整 pytest；
2. 审计 milestone 2 pending 和固定协议；
3. 发布实现与 DEVLOG-only 提交。

---

### 2026-08-30｜E2 milestone 2 全量回归会话中断审计

**状态：INTERRUPTED / RESULT UNKNOWN**

**时间与环境**

- 审计时间：2026-08-30 09:48:37 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only

**步骤 ID**

- `E2-bon-m2-full-regression-attempt-01`

**行动与关键配置**

- 2026-08-29 夜间曾启动 `uv run pytest` 全量回归；
- 会话 `49463` 仅返回了持续的部分测试进度点，尚未捕获 pytest 汇总与进程退出码时，Codex 会话因额度中断；
- 2026-08-30 恢复后轮询该会话得到 `Unknown process id 49463`，无法从原会话恢复最终状态；
- 复查工作树、`HEAD` 与 `origin/main`：E2 milestone 2 未提交改动仍完整，`HEAD == origin/main == c941ee496d0e39a1196ee4bfe629cc197624f186`。

**结果**

- 不把部分进度输出视为测试通过；本次全量回归结果明确记为未知；
- 未发现部分提交、部分推送或远端基线漂移；
- 必须从头重跑全量 pytest 后才可继续发布验收。

**产物路径**

- `DEVLOG.md`
- 本地未提交 E2 milestone 2 工作树

**问题 / 失败**

- 原 pytest 进程及最终退出码不可恢复，这是会话中断而非已确认的代码测试失败。

**下一步**

1. 从头运行 `uv run pytest` 并捕获完整汇总与退出码；
2. 立即记录重跑结果；
3. 结果通过后执行 milestone 2 仓库审计与发布。

---

### 2026-08-30｜E2 milestone 2 全量回归重跑通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 09:53:36 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/mock

**步骤 ID**

- `E2-bon-m2-full-regression-attempt-02`

**行动与关键配置**

- 从头执行 `uv run pytest`；
- 未复用前一晚退出状态未知的测试会话；
- 捕获完整 pytest 汇总与进程退出码。

**结果**

- **95/95 passed**；
- 运行时间 `253.55s (0:04:13)`；
- 进程 exit code 0；
- E0/W1/E1 既有测试与 E2 milestone 1/2 测试全量通过。

**产物路径**

- `tests/`
- 本地 E2 milestone 2 工作树

**问题 / 失败**

- 无；前一晚未知结果已由本次完整重跑取代，但历史中断记录永久保留。

**下一步**

1. 执行 milestone 2 diff、协议身份、禁止产物、大文件与 untracked 审计；
2. `git fetch origin` 并确认远端基线无并发前进；
3. 创建并普通推送 milestone 2 实现基线。

---

### 2026-08-30｜E2 milestone 2 Python 编译验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 09:54:41 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only static check

**步骤 ID**

- `E2-bon-m2-compileall-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src tests`。

**结果**

- exit code 0；`src/` 与 `tests/` 中 Python 文件全部可编译；
- 未产生需要纳入版本控制的编译产物。

**产物路径**

- `src/`
- `tests/`

**问题 / 失败**

- 无编译错误。

**下一步**

1. 加固 E1 reward/frozen threshold 身份门；
2. 增加阈值漂移拒绝测试；
3. 重跑定向与全量测试。

---

### 2026-08-30｜E2 milestone 2 发布前依赖门审阅诊断

**状态：FIX REQUIRED**

**时间与环境**

- 诊断时间：2026-08-30 09:54:41 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；本地只读代码审阅

**步骤 ID**

- `E2-bon-m2-e1-threshold-identity-review-v01`

**行动与关键配置**

- 对照计划中“正式 E2 preparation 必须验证 E1 reward、frozen protocol、prompt/runtime/model fingerprints，缺失或不一致失败关闭”的要求，逐项检查 `src/e2_bon/preparation.py::_dependencies`；
- 核对 E1 `reward-v0.yaml` 生成字段与 `FrozenProtocolV2` 字段。

**结果**

- 已有门禁会核对 PASS_PROVISIONAL、全部可靠性门、selected method、runtime fingerprint、model revision、prompt/parser identity；
- 发现 `reward-v0` 的 `confidence_threshold` 与 `absolute_delta_threshold` 尚未和 frozen protocol、frozen config 三方精确对齐；
- 这不会使已有 mock 测试失败，但会留下阈值身份漂移未被 preparation 拒绝的缺口，故 milestone 2 暂不发布。

**产物路径**

- `src/e2_bon/preparation.py`
- `src/e1_judge/metrics.py`
- `src/e1_judge/models.py`

**问题 / 失败**

- E1 冻结阈值身份门不完整。

**下一步**

1. 在 preparation 依赖门中精确核对 reward/protocol/config 的两项冻结阈值；
2. 新增任一阈值漂移均失败并保留 failed artifact 的测试；
3. 重新执行受影响测试与全量回归。

---

### 2026-08-30｜E2 milestone 2 冻结依赖身份门加固实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 09:56:38 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only code/test fixture

**步骤 ID**

- `E2-bon-m2-frozen-identity-hardening-v01`

**行动与关键配置**

- 将 E1 decision 的可靠性门收紧为四个固定键且值必须逐项为布尔 `true`，避免空门集合被 `all()` 接受；
- 核对 frozen protocol 的 config checksum、全部 prompt checksum 和由 code snapshot/config/runtime/prompt/selection 重算的 protocol fingerprint；
- 将 `reward-v0`、frozen config、frozen protocol 的 confidence/absolute-delta threshold 做三方精确对齐；
- auxiliary rubric artifact 同样要求四个固定可靠性门全部为真；
- 更新测试 fixture 使用真实重算的 protocol fingerprint，并新增两项 reward threshold 漂移的参数化拒绝测试，要求失败现场永久保留。

**结果**

- 实现与测试用例已写入工作树；
- 尚未宣称通过，等待定向与全量 pytest。

**产物路径**

- `src/e2_bon/preparation.py`
- `tests/e2/test_m2.py`

**问题 / 失败**

- 无已知实现阻塞；测试待执行。

**下一步**

1. 运行 `uv run pytest tests/e2/test_m2.py -q`；
2. 若通过，重新运行无筛选全量 pytest；
3. 再执行最终仓库审计。

---

### 2026-08-30｜E2 milestone 2 冻结身份门定向回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 09:58:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/mock

**步骤 ID**

- `E2-bon-m2-frozen-identity-targeted-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/e2/test_m2.py -q`；
- 覆盖真实 protocol fingerprint 重算、confidence/absolute-delta 两类阈值漂移拒绝、PASS gate、rubric qualification、280 pair/560 request、cache resume 与 atomic failure preservation。

**结果**

- **7/7 passed**，进程 exit code 0；
- 两种冻结阈值漂移均失败关闭并保留 `PREPARATION_FAILED.json`；
- 原有 milestone 2 行为无定向回归。

**产物路径**

- `src/e2_bon/preparation.py`
- `tests/e2/test_m2.py`

**问题 / 失败**

- 无。

**下一步**

1. 从头运行无筛选 `uv run pytest`；
2. 全绿后完成最终仓库审计；
3. fetch 并发布 milestone 2。

---

### 2026-08-30｜E2 milestone 2 身份门加固后最终全量回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:04:18 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/mock

**步骤 ID**

- `E2-bon-m2-final-full-regression-v01`

**行动与关键配置**

- 在冻结依赖门加固后从头执行无筛选 `uv run pytest`；
- 捕获完整测试汇总与退出码。

**结果**

- **97/97 passed**；
- 运行时间 `282.03s (0:04:42)`；
- 进程 exit code 0；
- 相比加固前95项，新增的两项 reward threshold 漂移拒绝测试均纳入全量回归且通过。

**产物路径**

- `tests/`
- 本地 E2 milestone 2 工作树

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 执行最终 Git/diff/固定身份/禁止产物/大文件审计；
2. fetch 并确认 `origin/main` 未并发前进；
3. 发布 milestone 2 实现基线。

---

### 2026-08-30｜E2 milestone 2 最终仓库审计首次脚本计数失败

**状态：INVALID / RETRY REQUIRED**

**时间与环境**

- 完成时间：2026-08-30 10:08:02 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；只读 Git/文件系统审计

**步骤 ID**

- `E2-bon-m2-final-repository-audit-attempt-01`

**行动与关键配置**

- 执行 `git diff --check`、固定 W1/E1 identity drift、pending/禁止扩展名/大文件/HEAD 身份组合审计；
- pending 组合表达式使用了 `@((git diff ...), (git ls-files ...))`。

**结果**

- `git diff --check` exit 0，仅有预期 LF→CRLF 提示；
- 固定 identity 漂移、禁止产物、大文件均返回0；HEAD 与本地 tracking main 均为 `c941ee496d0e39a1196ee4bfe629cc197624f186`；
- 但 pending 被保留为两个嵌套数组，错误输出 `PendingCount=2`，而数组内实际共有9条路径；因此本次组合审计整体判定无效，不作为发布依据。

**产物路径**

- `DEVLOG.md`

**问题 / 失败**

- PowerShell pending 数组未展平，计数错误。

**下一步**

1. 分别初始化 tracked 数组并追加 untracked 数组后排序去重；
2. 重跑完整只读审计并要求精确 pending=9；
3. 审计通过后再 fetch。

---

### 2026-08-30｜E2 milestone 2 最终仓库审计通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:08:33 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；只读 Git/文件系统审计

**步骤 ID**

- `E2-bon-m2-final-repository-audit-attempt-02`

**行动与关键配置**

- 用显式 tracked 数组初始化并追加 non-ignored untracked 数组，排序去重后重跑 pending 审计；
- 执行 `git diff --check`；
- 对 `configs/w1_manifest.yaml` 与完整 `configs/e1/` 相对 HEAD 做固定 identity 零漂移检查；
- 对 pending 扫描视频、数据库、模型、NumPy、Parquet 等禁止扩展名；
- 排除 `.git`、`.venv`、pytest/cache、`__pycache__` 与既有 ignored `artifacts` 后扫描超过 5 MiB 文件；
- 核对 HEAD 与本地 tracking main。

**结果**

- `git diff --check` exit 0，仅有预期 Windows LF→CRLF 工作树提示；
- pending 精确为 **9** 个：`DEVLOG.md`、3个 E2 module 修改/新增共5个源文件、3个 E2 测试修改/新增；
- W1/E1 fixed identity drift **0**；禁止产物 **0**；超过5 MiB文件 **0**；
- HEAD 与本地 `origin/main` 均为 `c941ee496d0e39a1196ee4bfe629cc197624f186`；
- 服务器未连接，DATA4 未访问，未创建真实研究产物。

**产物路径**

- `src/e2_bon/`
- `tests/e2/`
- `DEVLOG.md`

**问题 / 失败**

- 无未解决审计失败；首次错误计数记录保留但已由本次有效重跑闭环。

**下一步**

1. 执行 `git fetch origin`；
2. 确认远端 `main` 仍为预期里程碑1基线；
3. 创建并普通推送 milestone 2 实现提交。

---

### 2026-08-30｜E2 milestone 2 发布前远端身份确认

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:09:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅访问 Git remote；未连接学校服务器、未访问 DATA4

**步骤 ID**

- `E2-bon-m2-prefetch-origin-identity-v01`

**行动与关键配置**

- 执行 `git fetch origin`；
- fetch 成功后分别执行 `git rev-parse HEAD` 与 `git rev-parse origin/main`，并查看远端最近3条历史。

**结果**

- fetch exit code 0；
- `HEAD == origin/main == c941ee496d0e39a1196ee4bfe629cc197624f186`；
- 远端未发生并发前进，仍为已发布的 E2 milestone 1 DEVLOG 基线；
- 允许按计划创建普通提交，禁止 force-push 的约束保持不变。

**产物路径**

- Git remote `origin/main`
- 本地 Git refs

**问题 / 失败**

- 无。

**下一步**

1. 创建 E2 milestone 2 实现基线提交；
2. 记录精确提交 SHA；
3. 普通推送到 `origin/main` 并核对远端一致性。

---

### 2026-08-30｜E2 milestone 2 实现基线提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:09:31 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E2-bon-m2-implementation-commit-v01`

**行动与关键配置**

- 精确 stage milestone 2 的9个预期 code/test/DEVLOG 文件；
- 执行 staged `git diff --cached --check`；
- 创建普通提交 `git commit -m "Add E2 atomic judge orchestration"`。

**结果**

- staged diff check 通过；
- 提交成功：`d64c24425de9288e356ab5bd4619436847793f65`；
- 提交统计：9 files changed，2048 insertions，4 deletions；新增 preparation、qualification、runner 和 milestone 2 测试；
- 提交后本地 `main` 相对 `origin/main` ahead 1，除本条待记录 DEVLOG 外无其他新开发改动。

**产物路径**

- Git commit `d64c24425de9288e356ab5bd4619436847793f65`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送 `main` 到 `origin/main`；
2. 核对远端 SHA 与本地实现 SHA 一致；
3. 创建 DEVLOG-only 发布记录提交并推送。

---

### 2026-08-30｜E2 milestone 2 实现基线普通推送

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:10:01 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅 GitHub remote；未连接学校服务器、未访问 DATA4

**步骤 ID**

- `E2-bon-m2-implementation-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main`；
- 推送后核对本地 HEAD、`origin/main` 与工作树状态；
- 未使用 force-push。

**结果**

- push 成功：`origin/main` 从 `c941ee496d0e39a1196ee4bfe629cc197624f186` 前进到 `d64c24425de9288e356ab5bd4619436847793f65`；
- 本地 HEAD 与 `origin/main` 精确一致；
- 发布依据为97/97 full pytest、CLI/config验收、冻结身份门定向测试与最终仓库审计；
- push 后唯一工作树修改为本条及前一条提交/推送 DEVLOG 记录。

**产物路径**

- Git commit `d64c24425de9288e356ab5bd4619436847793f65`
- Git remote `origin/main`

**问题 / 失败**

- 无。

**下一步**

1. 创建 DEVLOG-only milestone 2 发布记录提交；
2. 普通推送该记录；
3. 核对工作树 clean 后进入 milestone 3 本地 CPU-only 实现。

---

### 2026-08-30｜E2 milestone 2 DEVLOG-only 发布记录提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:10:26 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E2-bon-m2-devlog-publication-commit-v01`

**行动与关键配置**

- 用 `git diff --name-only` guard 确认待提交路径严格只有 `DEVLOG.md`；
- 执行 staged diff check；
- 创建 `git commit -m "Record E2 milestone 2 publication"`。

**结果**

- DEVLOG-only guard 与 staged diff check 通过；
- 提交成功：`f9a03b521adc0c187ccb8e3d3c408943964b77b3`；
- 提交统计：1 file changed，87 insertions；
- 本地 `main` 相对远端 ahead 1，等待普通推送。

**产物路径**

- Git commit `f9a03b521adc0c187ccb8e3d3c408943964b77b3`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送 DEVLOG-only commit；
2. 核对 HEAD 与 `origin/main`；
3. 进入 E2 milestone 3 设计与实现。

---

### 2026-08-30｜E2 milestone 2 DEVLOG-only 发布记录普通推送

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:10:54 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅 GitHub remote；未连接学校服务器、未访问 DATA4

**步骤 ID**

- `E2-bon-m2-devlog-publication-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main` 推送 DEVLOG-only commit；
- 推送后核对本地 HEAD、`origin/main` 与工作树状态；
- 未使用 force-push。

**结果**

- push 成功：`origin/main` 从 `d64c24425de9288e356ab5bd4619436847793f65` 前进到 `f9a03b521adc0c187ccb8e3d3c408943964b77b3`；
- 本地 HEAD 与 `origin/main` 精确一致；
- E2 milestone 2 的“实现基线 + DEVLOG-only 发布记录”双提交链完成；
- 唯一工作树修改为本条 push 后 DEVLOG 记录，将随 milestone 3 实现基线纳入下一提交。

**产物路径**

- Git commit `f9a03b521adc0c187ccb8e3d3c408943964b77b3`
- Git remote `origin/main`

**问题 / 失败**

- 无。

**下一步**

1. 固化 milestone 3 本地接口与 fail-closed 设计；
2. 实现选择、人标、统计、报告、verifier；
3. 编写只交给服务器端 agent 的独立 runbook。

---

### 2026-08-30｜E2 milestone 3 选择、人标与统计接口设计冻结

**状态：DECIDED / IMPLEMENTATION PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:13:27 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；本地协议/接口设计

**步骤 ID**

- `E2-bon-m3-interface-design-v01`

**行动与关键配置**

- 固化 `select` 输入为 E2 config/design/pairs/primary results/reward-v0，以及可选 rubric results/qualified auxiliary artifact；
- primary pair 每个无序 pair 必须有两条成功方向结果，先映射到 canonical candidate，再要求双向 preference 一致；只有 decisive 且最小 confidence 达到 E1 frozen reward threshold 的比较进入按 sample 独立拟合的 ridge-stabilized Bradley–Terry；
- random baseline 用 fixed config seed + trial/N 做 deterministic hash sampling；主 reward 以 BT utility 再 candidate ID 升序破同分；
- rubric 可用时，四个维度分别执行相同 swap/confidence/BT 流程并映射为0..1 utility；等权线性按四维均值，鲁棒方法按 Pareto 非支配层→最小维度 utility→几何平均→candidate ID 升序确定性破同分；rubric 未经资格门时两者显式 `NOT_APPLICABLE`；
- human plan 固定从 primary reward 的同一 trial 提取 N=4 与 N=1 共80组；相同 checksum 自动 `identical_selection` tie，不进入人工 UI；其余项按 fixed seed/annotator identity 确定性随机左右方向，UI 不显示 N 身份；
- 两名不同主标注者必须完整覆盖全部非同一视频项；任何五字段争议均要求不同第三人完整覆盖；最终 adjudicated 输出恢复成80项；
- 主 tie-aware overall score 固定为 N4 win=1、tie=0.5、uncertain=0.5、N1 win=0，并同时报告 decisive win rate、tie/uncertain、四维偏好、agreement 与 Cohen kappa，防止 neutral-imputed 主值掩盖 uncertain；
- 95% CI 以10个 sample 为 cluster、固定 seed、2000次有放回重采样；`meets_m1_target` 只检查 point estimate>=0.60，不自动声明显著；faithfulness/preservation bootstrap 上界低于0.5时单独发 degradation warning；
- 理论成本按10 sample×8轮的 N、双向全 pair 请求计数，实际成本报告完整80候选/560主请求及可选560 rubric请求的总计与每trial摊销；mock/replay 全链保持 `research_measurements=0`。

**结果**

- milestone 3 数据链和统计解释已冻结，可进入实现；
- 未改变 E1/E0 protocol、threshold、prompt、model revision、30/70 split 或 research gate。

**产物路径**

- `DEVLOG.md`

**问题 / 失败**

- 尚未实现与测试；正式人标 UI 和 GPU/Judge 运行仍只允许服务器端 agent 按 runbook 执行。

**下一步**

1. 新增 milestone 3 strict models 与 selection/annotation/analysis/report/verify modules；
2. 扩展 `e2` CLI；
3. 增加 known BT、Pareto、blind/adjudication、identical tie、cluster bootstrap 与 mock E2E 测试。

---

### 2026-08-30｜E2 milestone 3 选择引擎实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:17:12 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only Python implementation

**步骤 ID**

- `E2-bon-m3-selection-engine-v01`

**行动与关键配置**

- 新增 strict selection、human comparison、human annotation、adjudicated comparison schema；
- 新增 ridge-stabilized Newton Bradley–Terry 拟合，输出 centered log ability；
- 实现 E2 560结果的 method/stage/split/artifact/protocol/candidate/双方向完整身份检查；
- 实现 canonical swap 合并、冻结 confidence filtering、按sample独立 BT；
- 实现 fixed-seed random、primary BT、四维等权线性与 Pareto→max-min→geometric→ID 选择；
- 实现未资格 rubric `NOT_APPLICABLE`、primary rubric 和 qualified auxiliary rubric 两条合法路径；
- 生成80项 primary N=4 vs N=1 human plan，并以视频 checksum 决定 `identical_selection`；
- selection 输出使用 atomic no-replace JSON，mock/replay 强制 `research_measurements=0`。

**结果**

- `src/e2_bon/models.py` 与新 `src/e2_bon/selection.py` 已实现；
- 尚未执行测试，不宣称选择引擎通过。

**产物路径**

- `src/e2_bon/models.py`
- `src/e2_bon/selection.py`

**问题 / 失败**

- 待定向测试验证 BT 收敛、swap/threshold 过滤、Pareto破同分和完整选择数量。

**下一步**

1. 实现 E2 blind annotation UI/adjudication；
2. 实现 analysis/report/verifier；
3. 完成 CLI 后统一编译与定向测试。

---

### 2026-08-30｜E2 milestone 3 盲标与第三人裁决实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:19:19 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；本地 CPU-only engineering

**步骤 ID**

- `E2-bon-m3-human-annotation-v01`

**行动与关键配置**

- 新增 E2 专用本地 HTTP blind annotation UI，页面仅显示 source、Candidate Left/Right、instruction/target，不显示 N=4/N=1 或 candidate ID；
- 按 comparison ID、annotator ID、fixed seed 确定性随机左右方向，并保存 canonical a/b/tie/uncertain；
- 自动从 UI 排除 `identical_selection`，支持第三人用 disputed comparison filter 只标争议项；
- adjudicator 强制两个主文件来自不同 annotator 且完整覆盖全部非同一视频项；五项字段任一不一致即争议；
- 第三人必须是不同身份并精确覆盖全部且仅争议项；缺失时写 no-replace preliminary report 后失败关闭；
- 最终输出将相同 checksum 项自动补为 annotation-free tie，保证恰好80项，并输出逐维 agreement/Cohen kappa、tie/uncertain 与争议审计。

**结果**

- `src/e2_bon/annotations.py` 已实现；
- 尚未启动 UI 或执行正式人标；正式 server-hosted annotation 仍只交付服务器端 agent；
- 尚未执行本地测试，不宣称模块通过。

**产物路径**

- `src/e2_bon/annotations.py`

**问题 / 失败**

- 待测试 blind HTML、方向映射、完整覆盖、第三人约束和自动 tie。

**下一步**

1. 实现 cluster-bootstrap analysis 与成本报告；
2. 实现 Markdown/SVG/CSV reporting 和 verifier；
3. 完成 CLI 与定向测试。

---

### 2026-08-30｜E2 milestone 3 统计、成本、报告与 verifier 实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:22:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only Python/report engineering

**步骤 ID**

- `E2-bon-m3-analysis-report-verify-v01`

**行动与关键配置**

- 实现80项 adjudicated identity 校验与 sample-cluster percentile bootstrap（10 clusters×8 rounds、fixed seed、config固定2000次）；
- 实现 overall/四维 tie-aware rate、decisive rate、tie/uncertain、M1 target flag 和 faithfulness/preservation CI退化告警；
- 实现理论独立 trial 生成/Judge计数，以及完整80候选/560 primary/可选560 rubric的实际 runtime 与每trial摊销成本；
- analysis 输出采用 final/staging/failed 三路径 ABSENT 与 no-replace publish；
- 实现 Markdown、win-rate SVG、cost SVG、cost CSV 与 report manifest，报告明确 mock/replay 无研究测量；
- 实现 preparation SHA256SUMS、selection依赖、80人标、2000次cluster bootstrap、成本计数、report artifact 与 mock/replay research flag 的 fail-closed verifier；
- verifier 输出使用 atomic no-replace JSON，只有 formal-command 且全项通过才标记 ready for research interpretation。

**结果**

- 新增 analysis、reporting、verification 三个模块；
- 尚未执行编译/测试，不宣称通过。

**产物路径**

- `src/e2_bon/analysis.py`
- `src/e2_bon/reporting.py`
- `src/e2_bon/verification.py`

**问题 / 失败**

- 待测试2000次聚类重采样、atomic no-overwrite、mock report和全链 verifier。

**下一步**

1. 扩展 `e2` CLI 的 select/annotate/adjudicate/analyze/report/verify；
2. 编写服务器端 agent runbook；
3. 增加完整 milestone 3 测试并执行编译/回归。

---

### 2026-08-30｜E2 milestone 3 CLI 与服务器交付 runbook 实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:23:43 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；仅编写服务器端 agent 操作说明

**步骤 ID**

- `E2-bon-m3-cli-server-runbook-v01`

**行动与关键配置**

- 为 `e2` CLI 新增 `select`、`annotate`、`adjudicate`、`analyze`、`report`、`verify` 六个公共命令；
- select 暴露 `mock|replay|formal-command` measurement mode 与可选 qualified rubric 双参数；
- annotate 暴露 packets/annotator/host/port/filter，adjudicate 强制可重复 `--annotation` 两文件；
- analyze/report/verify 显式接收全部身份依赖与可选 rubric artifact；verify失败返回非零；
- 新增服务器端 agent 专用 runbook，固定三个 DATA4 根、E1 PASS gate、Linux no-replace preflight、30候选GPU生成、人工粗审、原子 preparation、真实 Judge、双人盲标/第三人、分析回传顺序；
- 手册明确三个根及 staging/failed 必须预先 ABSENT，失败现场保留，E1无合法 reward-v0 时不得创建正式 E2 根，不得进入 E3/DPO。

**结果**

- CLI 与 runbook 已写入工作树；
- 本地 agent 未执行 runbook、未连接学校服务器、未访问 DATA4、未加载真实模型；
- 尚未执行 CLI/编译/测试，不宣称通过。

**产物路径**

- `src/e2_bon/cli.py`
- `docs/E2_SERVER_RUNBOOK.md`

**问题 / 失败**

- 待测试 Typer 参数、全链数据 identity 与报告/verifier。

**下一步**

1. 编写 milestone 3 synthetic/mock tests；
2. 先运行 compileall 和定向 pytest；
3. 修复后运行完整 mock E2E 与全量回归。

---

### 2026-08-30｜E2 milestone 3 首轮 Python 编译检查

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:24:12 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only static check

**步骤 ID**

- `E2-bon-m3-compileall-attempt-01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src/e2_bon`。

**结果**

- exit code 0；milestone 3 新增/修改的 E2 Python 模块均可编译；
- 未发现语法或 import-time compile error。

**产物路径**

- `src/e2_bon/`

**问题 / 失败**

- 无编译错误；行为与数据契约仍待测试。

**下一步**

1. 新增 milestone 3 synthetic/mock tests；
2. 运行定向 pytest；
3. 逐项记录并修复行为失败。

---

### 2026-08-30｜E2 milestone 3 synthetic/mock 测试实现

**状态：IMPLEMENTED / EXECUTION PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:27:17 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；tiny synthetic/mock only

**步骤 ID**

- `E2-bon-m3-test-implementation-v01`

**行动与关键配置**

- 新增10 sample×8 candidate、280 pair、80 balanced trial、560双方向 mock-format result 的纯 synthetic fixture；
- 覆盖 known Bradley–Terry ordering、centered ability、Pareto dominated removal 与 candidate ID破同分；
- 覆盖 swap inconsistency、低confidence过滤、pairwise rubric `NOT_APPLICABLE`、rubric primary四方法1280选择、atomic no-overwrite；
- 覆盖 fixed blind direction、HTML不泄露N/candidate ID、70非同一视频双人完整标注、1项第三人争议、10项自动 identical tie；
- 覆盖80项 overall rate、2000次10-cluster bootstrap、mock research=0、analysis no-overwrite、Markdown/SVG/CSV report 和 end-to-end verifier；
- 加固 adjudicator：逐条重算并核对每位 primary/third annotator 的显示方向；
- 加固 verifier：明确要求 `e2-preparation-v01.json` 与 `preparation-verification-v01.json` 均为 passed。

**结果**

- `tests/e2/test_m3.py` 及两项实现加固已写入工作树；
- 尚未运行测试，不宣称通过。

**产物路径**

- `tests/e2/test_m3.py`
- `src/e2_bon/annotations.py`
- `src/e2_bon/verification.py`

**问题 / 失败**

- 待 pytest 捕获 schema、BT数值、Typer、统计和 verifier 行为问题。

**下一步**

1. 运行 `uv run pytest tests/e2/test_m3.py -q`；
2. 逐项记录任何失败并修复；
3. 定向全绿后运行 milestone 1+2+3 E2组合与全量 pytest。

---

### 2026-08-30｜E2 milestone 3 首轮定向回归通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:28:13 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only synthetic/mock

**步骤 ID**

- `E2-bon-m3-targeted-attempt-01`

**行动与关键配置**

- 执行 `uv run pytest tests/e2/test_m3.py -q`。

**结果**

- **5/5 passed**，进程 exit code 0；
- known BT/Pareto、swap/threshold、pairwise/rubric selection、blind direction/third adjudication/identical tie、2000次cluster bootstrap、report与mock verifier E2E全部通过；
- mock全链 `research_measurements=0`，final verification通过但 `ready_for_research_interpretation=false`，符合非研究输出约束。

**产物路径**

- `tests/e2/test_m3.py`
- `src/e2_bon/`

**问题 / 失败**

- 无定向失败；仍需 E2组合与全仓库回归。

**下一步**

1. 运行 `uv run pytest tests/e2 -q`；
2. 修复任何 milestone 1/2 回归；
3. E2组合通过后执行 CLI/help 与全量 pytest。

---

### 2026-08-30｜E2 milestone 1+2+3 组合回归通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:31:05 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/synthetic/mock

**步骤 ID**

- `E2-bon-all-milestones-targeted-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/e2 -q`，组合 milestone 1候选池、milestone 2 preparation/runner/qualification 与 milestone 3 selection/human/analysis/report/verify。

**结果**

- **17/17 passed**，进程 exit code 0；
- milestone 1/2 既有 E2 contract 无回归；
- milestone 3 新 schema/CLI imports 未破坏候选池、atomic preparation、cache resume 或 rubric qualification。

**产物路径**

- `tests/e2/`
- `src/e2_bon/`

**问题 / 失败**

- 无 E2 组合失败；仍需公共 CLI逐条验收与全仓库回归。

**下一步**

1. 执行 E2主 help/validate及六个新增命令help；
2. 运行无筛选完整 pytest；
3. 全绿后进行 milestone 3 最终协议/仓库审计。

---

### 2026-08-30｜E2 milestone 3 CLI 组合验收脚本输出截断

**状态：INVALID / RETRY REQUIRED**

**时间与环境**

- 完成时间：2026-08-30 10:31:35 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only CLI check

**步骤 ID**

- `E2-bon-m3-cli-acceptance-attempt-01`

**行动与关键配置**

- 尝试在 PowerShell foreach 中依次执行主 `--help`、`validate` 和六个新增命令 `--help`；
- 每条 Typer/Rich 输出通过管道连接 `Select-Object -First 8` 以限制日志。

**结果**

- 仅捕获第一条 `e2 --help` 的前8行；没有捕获后续命令标记或最终 `E2_CLI_ACCEPTANCE=PASS`；
- 外层进程虽 exit 0，但不能证明八条命令全部执行，故本次结果无效；
- 诊断为 `Select-Object -First` 提前关闭 Rich/Typer 输出管道导致组合脚本未留下完整执行证据。

**产物路径**

- `DEVLOG.md`

**问题 / 失败**

- CLI验收编排脚本不可靠，不是已确认的 E2 CLI 功能失败。

**下一步**

1. 将八条命令作为相互独立的进程执行；
2. 逐项核对 exit code 与关键命令名/参数；
3. 有效重跑通过后再进入全量 pytest。

---

### 2026-08-30｜E2 milestone 3 CLI 独立重跑验收通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:32:05 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only CLI/config

**步骤 ID**

- `E2-bon-m3-cli-acceptance-attempt-02`

**行动与关键配置**

- 将 `e2 --help`、`e2 validate`、`e2 select --help`、`annotate --help`、`adjudicate --help`、`analyze --help`、`report --help`、`verify --help` 作为八个相互独立进程执行；
- 逐项捕获完整输出和 exit code。

**结果**

- 八条命令全部 exit 0；
- 主 help 列出 milestone 1+2+3 共13个命令；
- `validate` 返回 valid=true、experiment_id固定、candidates=80；
- select 的measurement mode/rubric双参数、annotate filter、adjudicate重复annotation、analyze/report/verify依赖参数均完整；
- 首次管道截断问题已闭环，本次为有效验收依据。

**产物路径**

- `src/e2_bon/cli.py`
- `configs/e2/pilot.yaml`

**问题 / 失败**

- 无。

**下一步**

1. 运行无筛选完整 `uv run pytest`；
2. 全绿后执行代码/协议/仓库卫生审阅；
3. 发现缺口则补测试并重新全量回归。

---

### 2026-08-30｜E2 milestone 3 首轮全仓库回归通过

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:36:59 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/synthetic/mock

**步骤 ID**

- `E2-bon-m3-full-regression-attempt-01`

**行动与关键配置**

- 执行无筛选完整 `uv run pytest`；
- 捕获完整汇总与进程退出码。

**结果**

- **102/102 passed**；
- 运行时间 `260.71s (0:04:20)`；
- 进程 exit code 0；
- E0/W1/E1 既有测试与 E2 milestone 1/2/3 全部通过。

**产物路径**

- `tests/`
- 本地 E2 milestone 3 工作树

**问题 / 失败**

- 无未解决测试失败；仍需发布前代码与仓库审计。

**下一步**

1. 审阅正式模式依赖身份、统计口径和 runbook边界；
2. 执行 diff/protocol/禁止产物/大文件/untracked审计；
3. 如有加固改动，补测试并重新全量回归。

---

### 2026-08-30｜E2 milestone 3 正式 measurement provenance 审阅诊断

**状态：FIX REQUIRED**

**时间与环境**

- 诊断时间：2026-08-30 10:37:55 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；本地只读代码/测试审阅

**步骤 ID**

- `E2-bon-m3-measurement-provenance-review-v01`

**行动与关键配置**

- 审阅 E2 request→runner result→select→analysis 的 backend/provenance 传递；
- 对照“mock/replay只能 research_measurements=0”和正式 E2 model/runtime/prompt fingerprints fail-closed 要求检查 result schema 与 selection identity gate。

**结果**

- E2 request 有 `backend`，但独立 E2 result schema/runner 未保留该字段；
- `select --measurement-mode formal-command` 当前只能相信调用参数，无法从 result record 证明结果确由 command backend 产生；
- selection 会核对 artifact/protocol/pair/方向，但尚未强制560条结果的 backend/model/runtime/prompt/parser identity 单一，也未把结果 model/prompt identity 与 `reward-v0` 对齐；
- 因而存在把 mock/replay 结果误标成正式 research measurements，或混合身份结果进入选择的风险；milestone 3 暂不发布。

**产物路径**

- `src/e2_bon/models.py`
- `src/e2_bon/runner.py`
- `src/e2_bon/selection.py`
- `tests/e2/test_m3.py`

**问题 / 失败**

- 正式 measurement provenance 与结果 identity gate 不完整；这不是已执行研究结果问题，本地尚无研究测量。

**下一步**

1. 在独立 E2 result schema/runner中持久化 backend；
2. selection绑定 measurement mode↔backend，强制结果 identity单一并与reward对齐；
3. 新增 mock伪装formal与混合identity拒绝测试，重跑定向/组合/全量。

---

### 2026-08-30｜E2 milestone 3 measurement provenance 加固实现

**状态：IMPLEMENTED / TEST PENDING**

**时间与环境**

- 完成时间：2026-08-30 10:38:54 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only code/test fixture

**步骤 ID**

- `E2-bon-m3-measurement-provenance-hardening-v01`

**行动与关键配置**

- 在独立 `E2JudgeResultV1` schema 中增加固定 backend 字段，并由 E2 runner 从原 request 持久化；
- selection要求560个 request ID与judge key均唯一，且 backend/model name/model revision/model manifest/runtime/prompt/parser identity全文件单一；
- measurement mode 与 backend 固定绑定：mock→mock、replay→replay、formal-command→command，禁止仅靠调用参数把mock/replay伪装为正式测量；
- 主结果的 model revision、prompt version/checksum、parser version 必须与 `reward-v0` 精确一致；
- auxiliary rubric 的 backend必须匹配measurement mode，model/runtime identity必须与primary一致；
- synthetic reward/result fixture补齐冻结身份，新增mock伪装formal和混合model revision两项拒绝测试。

**结果**

- provenance加固与测试用例已写入工作树；
- 尚未执行测试，不宣称通过。

**产物路径**

- `src/e2_bon/models.py`
- `src/e2_bon/runner.py`
- `src/e2_bon/selection.py`
- `tests/e2/test_m3.py`

**问题 / 失败**

- 待确认 milestone 2 runner/cached result schema 和 milestone 3 全链均兼容新 backend字段。

**下一步**

1. 运行 `uv run pytest tests/e2/test_m2.py tests/e2/test_m3.py -q`；
2. 定向通过后运行 E2组合；
3. 最终重新运行全仓库 pytest。

---

### 2026-08-30｜E2 measurement provenance 加固后定向回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:41:20 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only synthetic/mock

**步骤 ID**

- `E2-bon-m2-m3-provenance-targeted-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/e2/test_m2.py tests/e2/test_m3.py -q`；
- 联合覆盖milestone 2 runner/cache与milestone 3 result provenance/selection/human/analysis/report/verify。

**结果**

- **13/13 passed**，进程 exit code 0；
- E2 runner生成的新 backend字段可被cache与result schema正确恢复；
- mock结果伪装formal-command与混合model revision均按预期失败关闭；
- 既有atomic preparation、qualification和mock E2E无回归。

**产物路径**

- `tests/e2/test_m2.py`
- `tests/e2/test_m3.py`
- `src/e2_bon/`

**问题 / 失败**

- 无定向失败；仍需完整E2与全仓库最终回归。

**下一步**

1. 运行完整 `uv run pytest tests/e2 -q`；
2. 运行无筛选 `uv run pytest`；
3. 全绿后完成最终仓库审计。

---

### 2026-08-30｜E2 三里程碑 provenance 加固后组合回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:44:13 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/synthetic/mock

**步骤 ID**

- `E2-bon-all-milestones-final-targeted-v01`

**行动与关键配置**

- 在 measurement provenance 加固后执行完整 `uv run pytest tests/e2 -q`。

**结果**

- **18/18 passed**，进程 exit code 0；
- milestone 1候选扩展/80池、milestone 2 atomic preparation/runner/qualification、milestone 3 selection/human/statistics/report/verifier全部通过；
- provenance新增拒绝用例已进入组合回归。

**产物路径**

- `tests/e2/`
- `src/e2_bon/`

**问题 / 失败**

- 无。

**下一步**

1. 从头运行最终无筛选 `uv run pytest`；
2. 记录完整汇总；
3. 执行最终协议/仓库卫生审计并发布milestone 3。

---

### 2026-08-30｜E2 milestone 3 provenance 加固后最终全仓库回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:49:01 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only tiny fixture/synthetic/mock

**步骤 ID**

- `E2-bon-m3-final-full-regression-v01`

**行动与关键配置**

- 在 backend provenance与mixed identity gate加固后，从头执行无筛选完整 `uv run pytest`；
- 捕获完整pytest汇总与退出码。

**结果**

- **103/103 passed**；
- 运行时间 `259.38s (0:04:19)`；
- 进程 exit code 0；
- 相比首轮102项，新增mock伪装formal/混合身份拒绝测试已纳入，E0/W1/E1与全部E2测试无回归。

**产物路径**

- `tests/`
- 本地 E2 milestone 3 工作树

**问题 / 失败**

- 无未解决测试失败。

**下一步**

1. 重新执行 compileall 和最终 Git/protocol/runbook/仓库卫生审计；
2. fetch并确认远端无并发前进；
3. 创建并普通推送 milestone 3 实现与DEVLOG-only发布记录。

---

### 2026-08-30｜E2 milestone 3 最终 Python 编译验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:49:23 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；CPU-only static check

**步骤 ID**

- `E2-bon-m3-final-compileall-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src tests`。

**结果**

- exit code 0；全部源代码与测试Python文件可编译；
- 未产生需要版本控制的编译产物。

**产物路径**

- `src/`
- `tests/`

**问题 / 失败**

- 无。

**下一步**

1. 执行最终Git diff/protocol/runbook/禁止产物/大文件审计；
2. 审计通过后fetch；
3. 发布milestone 3。

---

### 2026-08-30｜E2 milestone 3 最终仓库与授权边界审计

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:50:09 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；只读 Git/文件系统/runbook审计

**步骤 ID**

- `E2-bon-m3-final-repository-boundary-audit-v01`

**行动与关键配置**

- 执行 `git diff --check`；
- 合并 tracked diff 与 non-ignored untracked，和11条预期milestone 3路径精确比较；
- 对 `configs/w1_manifest.yaml` 与完整 `configs/e1/` 相对HEAD执行fixed identity零漂移检查；
- 对pending扫描视频、数据库、模型、NumPy、Parquet等禁止扩展名；排除仓库元数据、虚拟环境、cache和ignored artifacts后扫描超过5 MiB文件；
- 搜索本地 `src/e2_bon`、`tests/e2` 中 DATA4/ssh/scp 引用，确认服务器路径只存在于server runbook；
- 核对runbook三个固定DATA4根、ABSENT前置和“不得进入E3/DPO”边界；
- 核对HEAD与本地tracking main。

**结果**

- `git diff --check` PASS，仅有预期Windows LF→CRLF提示；
- pending精确为 **11** 个，和预期集合差异 **0**；
- W1/E1 fixed identity drift **0**；禁止产物 **0**；超过5 MiB文件 **0**；
- 本地E2 source/test服务器操作引用 **0**；runbook三个固定根无缺失，包含ABSENT/no-overwrite和禁止E3/DPO约束；
- `HEAD == origin/main == f9a03b521adc0c187ccb8e3d3c408943964b77b3`（尚未fetch）；
- 学校服务器未连接、DATA4未访问、真实模型未加载、正式研究根未创建。

**产物路径**

- `src/e2_bon/`
- `tests/e2/`
- `docs/E2_SERVER_RUNBOOK.md`
- `DEVLOG.md`

**问题 / 失败**

- 无未解决审计失败。

**下一步**

1. 执行 `git fetch origin`；
2. 确认远端仍为milestone 2 DEVLOG基线；
3. 创建并普通推送milestone 3实现基线。

---

### 2026-08-30｜E2 milestone 3 发布前远端身份确认

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:50:36 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅Git remote；未连接学校服务器、未访问DATA4

**步骤 ID**

- `E2-bon-m3-prefetch-origin-identity-v01`

**行动与关键配置**

- 执行 `git fetch origin`；
- fetch后分别核对本地HEAD、`origin/main`与远端最近历史。

**结果**

- fetch exit code 0；
- `HEAD == origin/main == f9a03b521adc0c187ccb8e3d3c408943964b77b3`；
- 远端无并发前进，仍为E2 milestone 2 DEVLOG-only发布基线；
- 可按授权创建普通提交，继续禁止force-push。

**产物路径**

- Git remote `origin/main`
- 本地 Git refs

**问题 / 失败**

- 无。

**下一步**

1. 创建E2 milestone 3实现基线提交；
2. 记录精确SHA并普通推送；
3. 创建并推送DEVLOG-only发布记录。

---

### 2026-08-30｜E2 milestone 3 实现基线提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:51:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E2-bon-m3-implementation-commit-v01`

**行动与关键配置**

- 精确stage最终审计的11个milestone 3 code/test/docs/DEVLOG文件；
- 执行 staged `git diff --cached --check`；
- 创建普通提交 `git commit -m "Complete E2 Best-of-N pilot framework"`。

**结果**

- staged diff check通过；
- 提交成功：`539083e89ca9b0ee0a4a25681d1ef3a7264ab615`；
- 提交统计：11 files changed，2964 insertions，2 deletions；
- 新增selection、annotations、analysis、reporting、verification、test_m3和server runbook；
- 提交后本地`main`相对`origin/main` ahead 1，除本条待记录DEVLOG外无其他开发改动。

**产物路径**

- Git commit `539083e89ca9b0ee0a4a25681d1ef3a7264ab615`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送实现commit到`origin/main`；
2. 核对远端SHA；
3. 创建DEVLOG-only发布记录提交并推送。

---

### 2026-08-30｜E2 milestone 3 实现基线普通推送

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:51:38 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅GitHub remote；未连接学校服务器、未访问DATA4

**步骤 ID**

- `E2-bon-m3-implementation-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main`；
- 推送后核对本地HEAD、`origin/main`与工作树；
- 未使用force-push。

**结果**

- push成功：`origin/main`从`f9a03b521adc0c187ccb8e3d3c408943964b77b3`前进到`539083e89ca9b0ee0a4a25681d1ef3a7264ab615`；
- 本地HEAD与`origin/main`精确一致；
- 发布依据为103/103 full pytest、18/18 E2组合、CLI独立验收、compileall、measurement provenance gate和最终仓库/授权边界审计；
- push后唯一工作树修改为本条及前一条commit/push DEVLOG记录。

**产物路径**

- Git commit `539083e89ca9b0ee0a4a25681d1ef3a7264ab615`
- Git remote `origin/main`

**问题 / 失败**

- 无。

**下一步**

1. 创建DEVLOG-only milestone 3发布记录提交；
2. 普通推送该记录；
3. 核对最终工作树clean与远端一致性。

---

### 2026-08-30｜E2 milestone 3 DEVLOG-only 发布记录提交

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:52:05 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `E2-bon-m3-devlog-publication-commit-v01`

**行动与关键配置**

- 用路径计数guard确认待提交范围严格只有`DEVLOG.md`；
- 执行staged diff check；
- 创建`git commit -m "Record E2 milestone 3 publication"`。

**结果**

- DEVLOG-only guard与staged diff check通过；
- 提交成功：`b2cffed46f353b5d7b4727c8db5e69d2c27740e2`；
- 提交统计：1 file changed，88 insertions；
- 本地`main`相对远端ahead 1，等待普通推送。

**产物路径**

- Git commit `b2cffed46f353b5d7b4727c8db5e69d2c27740e2`

**问题 / 失败**

- 无。

**下一步**

1. 普通推送DEVLOG-only commit；
2. 核对HEAD与`origin/main`；
3. 记录最终发布状态。

---

### 2026-08-30｜E2 milestone 3 DEVLOG-only 发布记录普通推送

**状态：DONE**

**时间与环境**

- 完成时间：2026-08-30 10:52:59 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅GitHub remote；未连接学校服务器、未访问DATA4

**步骤 ID**

- `E2-bon-m3-devlog-publication-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main` 推送DEVLOG-only commit；
- 推送后核对本地HEAD、`origin/main`与工作树；
- 未使用force-push。

**结果**

- push成功：`origin/main`从`539083e89ca9b0ee0a4a25681d1ef3a7264ab615`前进到`b2cffed46f353b5d7b4727c8db5e69d2c27740e2`；
- 本地HEAD与`origin/main`精确一致；
- E2 milestone 3“实现基线 + DEVLOG-only发布记录”双提交链完成；
- E1发布、E2 milestone 1/2/3本地CPU-only工程均已发布到main；
- 本条是第二次push后的本地最终回执，也是唯一未提交工作树修改；不再创建第三个发布提交，避免为记录DEVLOG-only提交的push产生无限递归记录。

**产物路径**

- Git commit `b2cffed46f353b5d7b4727c8db5e69d2c27740e2`
- Git remote `origin/main`
- `docs/E2_SERVER_RUNBOOK.md`

**问题 / 失败**

- 无；正式E2仍被E1 PASS_PROVISIONAL/reward-v0 gate阻挡，且所有DATA4/GPU/真实Judge/正式人标操作仍必须由服务器端agent执行。

**下一步**

1. 将精确实现commit `539083e89ca9b0ee0a4a25681d1ef3a7264ab615`、发布commit `b2cffed46f353b5d7b4727c8db5e69d2c27740e2`和server runbook交给服务器端agent；
2. 服务器端agent先完成E1 gate与Linux no-replace/DATA4 ABSENT preflight；
3. A6000可用后按runbook生成30候选、运行真实Judge并回传正式审计包。

---

### 2026-09-01｜Defense MVP 本地 CPU 工程与发布授权落盘

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 21:39:28 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；未连接学校服务器、未访问 DATA4、未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-authorization-v01`

**行动与关键配置**

- 根据用户在当前会话中的明确授权，在 `AGENTS.md` 新增 Defense MVP 本地 CPU 工程与发布授权；
- 固定暂定题目为“基于约束式多目标排序的指令视频编辑候选选择与盲评系统”，目标交付日期为 2026-09-08；
- 授权覆盖本地代码、测试、配置、文档、DEVLOG、CPU-only 分析、报告、slides、录屏支持、审计提交与普通推送；
- 固定禁止边界：本地 agent 不操作学校服务器/DATA4/GPU，不修改 sealed E0，不改变或绕过 E1/E2 固定门禁，不把 mock/synthetic/replay 冒充真实测量；
- 执行 `rg -n -A 14 '^## Current Defense MVP' AGENTS.md` 与 `git diff --check -- AGENTS.md` 验证授权文本和 whitespace。

**结果**

- 授权边界已写入 `AGENTS.md`；
- 静态文本检查与 `git diff --check` 通过，仅有 Windows LF/CRLF 提示，不构成 whitespace error；
- 项目完成标准固定为：可复现系统、三方法完整比较、双人盲评、诚实统计报告和答辩材料；不要求算法必须得到正向胜率。

**产物路径**

- `D:\\lab idea\\AGENTS.md`
- `D:\\lab idea\\DEVLOG.md`

**问题 / 失败**

- 无。

**下一步**

1. 编写独立 Defense MVP 详细施工方案，覆盖数据回传、算法、模块、里程碑、验收与降级边界；
2. 静态校验施工方案后立即追加独立 DEVLOG 记录；
3. 先交用户审阅方案，不启动功能代码。

---

### 2026-09-01｜Defense MVP 施工方案首次补丁解析失败

**状态：FAILED（未修改目标文档）**

**时间与环境**

- 失败时间：2026-09-01 21:44:28 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-plan-document-patch-attempt-v01`

**行动与关键配置**

- 尝试通过单个长 `apply_patch` 新增 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`；
- 补丁正文包含算法公式、数据协议、逐日计划和验收边界；
- 嵌套工具脚本在执行补丁前发生 JavaScript `SyntaxError: Unexpected identifier 'text'`。

**结果**

- `apply_patch` 未执行，目标施工文档不存在；
- 只读复核 `plan_file_exists=False`；
- `AGENTS.md`、既有 `DEVLOG.md` 内容和其他工作树文件未被本次失败修改。

**产物路径**

- 无目标文档产物；诊断记录写入 `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 单个超长 JavaScript template literal 的转义/解析失败，必须避免继续使用同一组织方式。

**下一步**

1. 将施工文档拆分为多个较小 `apply_patch`；
2. 使用逐行数组拼接补丁字符串，避免 template literal 解析；
3. 文件完成后执行结构、关键词、编码和 `git diff --check` 验收。

---

### 2026-09-01｜Defense MVP 详细施工方案编写与静态验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 21:47:28 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；未连接学校服务器、未访问 DATA4、未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-construction-plan-v01`

**行动与关键配置**

- 新增 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`，固定 2026-09-08 交付、独立 `defense_mvp` 模块、7+3 数据边界、三种选择方法、N=1/2/4、42×2 双人盲评、负结果接受标准和本地 CPU-only 边界；
- 写明 E0 只读回传包最小文件集、本地 ignore 路径、F/P/T/Q 代理指标、约束式 Pareto/max-min、分歧聚合、Bradley–Terry、2,000 次 sample-cluster bootstrap、CLI/模块结构和 9 月 1–8 日逐日里程碑；
- 写明风险降级、DEVLOG/commit/push 审计、slides/录屏/讲稿结构与功能代码开工 gate；
- 运行 PowerShell 静态校验，检查 20 个必需标记、heading、code fence 配对、UTF-8 replacement character；
- 执行 `git diff --check -- AGENTS.md DEVLOG.md docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md` 和工作树范围核对。

**结果**

- 施工方案共 534 行、57 个 Markdown heading、8 个 code fence，20/20 必需标记存在；
- code fence 配对、UTF-8、结构与 `git diff --check` 全部通过；仅有 Windows LF/CRLF 提示，不构成 whitespace error；
- 当前改动严格为 `AGENTS.md`、`DEVLOG.md` 和新增施工方案；
- 本步骤未启动功能代码、测试、CPU 正式测量、人评、slides 或服务器操作。

**产物路径**

- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`
- `D:\\lab idea\\AGENTS.md`
- `D:\\lab idea\\DEVLOG.md`

**问题 / 失败**

- 无未解决失败；首次长补丁解析失败已由上一条独立记录保留，拆分补丁后成功。

**下一步**

1. 将施工方案交用户审阅，等待确认开工 gate；
2. 用户/服务器端 agent 按第 3.3 节准备 E0 只读回传包；
3. 用户确认方案后从 D1 scaffold + ingest 开始，每个可验证步骤即时记录 DEVLOG。

---

### 2026-09-01｜服务器 E0 回传提示词首次补丁格式失败

**状态：FAILED（未修改目标文档）**

**时间与环境**

- 失败时间：2026-09-01 21:54:22 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-data-handoff-prompt-patch-attempt-v01`

**行动与关键配置**

- 尝试在同一 `apply_patch` 中更新施工方案状态并新增服务器 agent 回传提示词；
- JavaScript 补丁数组的一行删除标记未作为字符串封装，被求值为 `NaN`；
- `apply_patch` 在 verification 阶段以 `invalid hunk` 拒绝。

**结果**

- 目标提示词文件不存在，施工方案状态仍为待审阅；
- 多文件补丁未部分应用，现有文件未被此次失败修改。

**产物路径**

- 无目标产物；诊断记录写入 `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 多文件 patch 数组中混入非字符串表达式。

**下一步**

1. 单独更新施工方案状态；
2. 单独新增提示词文件并分块追加；
3. 每个补丁行都使用显式字符串，完成后静态验收。

---

### 2026-09-01｜Defense MVP 施工方案正式批准开工

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 21:54:46 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-construction-plan-approval-v01`

**行动与关键配置**

- 用户明确要求设计服务器数据回传提示词并“按方案开工”；
- 将施工方案状态从待审阅更新为“用户已于 2026-09-01 确认方案并授权开工”；
- 执行状态文本核对与 `git diff --check -- docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`。

**结果**

- D0 开工 gate 的用户确认条件满足；
- 文档状态与当前授权一致，whitespace 验收通过。

**产物路径**

- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`

**问题 / 失败**

- 无。

**下一步**

1. 新增服务器端 E0 回传包 agent 提示词；
2. 提示词验收和 DEVLOG 完成后进入 D1 scaffold。

---

### 2026-09-01｜学校服务器 E0 回传包 Agent 提示词设计与验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 21:56:32 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用；未连接学校服务器、未访问 DATA4、未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-e0-handoff-agent-prompt-v01`

**行动与关键配置**

- 新增可直接交给服务器端 agent 的 E0 回传包提示词；
- 固定 package ID/目标、只读源发现、14 项硬输入门、唯一 staging、no-replace 发布、稳定相对路径布局、PACKAGE_MANIFEST/PACKAGE_VERIFICATION/PACKAGE_SHA256SUMS 和 POSIX tar；
- 固定硬计数为 10 sample、50 candidate、60 MP4、160 source frames、160 masks、800 candidate frames；
- 明确禁止修改 E0、启动 GPU、补造 audit、复制模型/cache/latent、覆盖既有 package 或修改服务器 Git worktree；
- 运行 15 个必需标记、heading、code fence、UTF-8、破坏性指令扫描和 `git diff --check`。

**结果**

- 提示词共 301 行、12 个 heading、6 个 code fence；
- 15/15 必需标记、围栏配对、UTF-8、破坏性指令扫描和 whitespace 验收通过；
- 施工方案状态已更新为用户确认开工；
- 本地未执行任何服务器命令。

**产物路径**

- `D:\\lab idea\\docs\\defense_mvp\\DATA_HANDOFF_AGENT_PROMPT.md`
- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`

**问题 / 失败**

- 无未解决失败；首次多文件补丁格式失败已由前置独立记录保留。

**下一步**

1. 用户将提示词第 2–11 节交给服务器端 agent；
2. 本地进入 D1 scaffold，新增 `defense_mvp` package、config、CLI 和 tiny fixture；
3. 在真实 tar 回传前只运行 tiny/CPU 工程测试，不产生正式测量。

---

### 2026-09-01｜Defense MVP 独立包、冻结配置与 CLI 骨架

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 21:59:11 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用；未连接学校服务器、未访问 DATA4、未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d1-scaffold-v01`

**行动与关键配置**

- 新增独立 `src/defense_mvp` package、`defense` CLI entry point 与 `configs/defense_mvp/pilot.yaml`；
- 用 Pydantic 严格冻结 7+3 sample、5 seeds、N=1/2/4、5 replicates、42 comparison/annotator、2,000 bootstrap、mask 阈值和 7 个 HSV color rule；
- 新增配置漂移拒绝与 CLI 计数测试；
- `uv run` 因 pyproject entry/package 变化重新构建并安装本地 editable package；无新增第三方依赖、无 uv.lock 变化；
- 依次运行配置测试、`defense validate-config`、`defense --help`、compileall 和 `git diff --check`。

**结果**

- `tests/defense_mvp/test_config_cli.py`：3/3 passed；
- CLI 固定输出 10 sample、50 candidate、35 quantitative、15 qualitative、42 comparison/annotator；
- CLI help 显示 `version` 与 `validate-config`；
- `src/defense_mvp` / `tests/defense_mvp` compileall 与 whitespace 验收通过；
- uv hardlink 不可用时回退 full copy，仅为性能提示，不影响安装或测试。

**产物路径**

- `D:\\lab idea\\configs\\defense_mvp\\pilot.yaml`
- `D:\\lab idea\\src\\defense_mvp\\`
- `D:\\lab idea\\tests\\defense_mvp\\test_config_cli.py`
- `D:\\lab idea\\pyproject.toml`

**问题 / 失败**

- 无未解决失败。

**下一步**

1. 实现 package manifest 的严格 schema；
2. 实现只读 ingest verifier、路径安全、SHA/count/cardinality 检查和原子 no-replace receipt；
3. 使用 tiny handoff fixture 覆盖成功与篡改失败路径。

---

### 2026-09-01｜回传提示词 manifest 精确字段补丁解析失败

**状态：FAILED（未修改目标提示词）**

**时间与环境**

- 失败时间：2026-09-01 22:08:08 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-handoff-schema-doc-patch-attempt-v01`

**行动与关键配置**

- 在 ingest 5 个完整树测试通过后，尝试给服务器提示词补充严格 JSON 字段模板；
- 补丁数组中一个 `@@` hunk marker 未作为字符串封装，JavaScript 在调用 `apply_patch` 前报 `SyntaxError: Invalid or unexpected token`。

**结果**

- 目标提示词未改变，精确字段模板标记不存在；
- 已通过的 ingest 测试结果和代码文件未受影响。

**产物路径**

- 无本次目标产物；诊断记录写入 `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 补丁脚本语法错误。

**下一步**

1. 使用仅含单个明确 context 的小补丁追加 JSON schema；
2. 静态验收提示词与 Pydantic schema 一致；
3. 再运行 Defense MVP 组合测试与 CLI smoke。

---

### 2026-09-01｜Defense MVP E0 回传包 ingest verifier 与原子 receipt

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:11:46 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用；未连接学校服务器、未访问 DATA4、未使用 GPU、未读取真实 E0

**步骤 ID**

- `DEFENSE-MVP-d1-ingest-v01`

**行动与关键配置**

- 扩展严格 package schema：安全 POSIX 相对路径、sample/candidate/media/frame set、source identity、固定 count 与 payload inventory；
- 实现全树 `PACKAGE_SHA256SUMS` 排序/唯一/覆盖校验、symlink/path escape 拒绝、逐文件 SHA/size、combined frame checksum、10×5 sample/seed 矩阵和 original plan/candidates/audit 交叉身份验证；
- 固定仅接受 `status=succeeded`、backend=anyv2v 的真实 E0 candidate；
- 实现 `verify-delivery` 与 `ingest` CLI、read-only source before/after identity、normalized manifest、ingest receipt、INGEST_SHA256SUMS 和跨 Windows/Linux no-replace directory publish；
- 新增完整 cardinality tiny handoff factory：60 MP4、160 source frames、160 masks、800 candidate frames，文件内容仅为测试字节；
- 覆盖 happy ingest、媒体篡改、unsafe `../` path、既有输出拒绝和 CLI verifier；
- 将服务器 agent 提示词补充为与 Pydantic 对齐的精确 JSON 字段及 payload/admin checksum 边界；
- 运行 `uv run pytest tests/defense_mvp -q`、CLI validate/help、compileall、提示词 schema/fence 检查和 `git diff --check`。

**结果**

- Defense MVP 组合测试：8/8 passed；
- full-tree tiny fixture 验证 1,180 个唯一媒体引用，篡改与路径逃逸均 fail-closed；
- `defense --help` 已显示 `version/validate-config/verify-delivery/ingest`；
- compileall、提示词精确 schema、code fence 和 whitespace 验收通过；
- 未产生真实 CPU 指标、正式人评或研究结论。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\models.py`
- `D:\\lab idea\\src\\defense_mvp\\io.py`
- `D:\\lab idea\\src\\defense_mvp\\ingest.py`
- `D:\\lab idea\\src\\defense_mvp\\cli.py`
- `D:\\lab idea\\tests\\defense_mvp\\conftest.py`
- `D:\\lab idea\\tests\\defense_mvp\\test_ingest.py`
- `D:\\lab idea\\docs\\defense_mvp\\DATA_HANDOFF_AGENT_PROMPT.md`

**问题 / 失败**

- 无未解决实现失败；提示词 JSON schema 补丁的首次脚本语法失败已由前置独立记录保留。

**下一步**

1. 补充 archive/tar 安全检查与更快的低层 checksum 单测（如 D1 审阅要求）；
2. 运行全仓库 pytest，确认独立 package 未破坏 W1/E1/E2；
3. 执行仓库卫生审计，形成 D1 审计提交并普通推送。

---

### 2026-09-01｜Defense MVP archive 安全接收首次补丁解析失败

**状态：FAILED（未修改 archive 目标文件）**

**时间与环境**

- 失败时间：2026-09-01 22:14:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-archive-receiver-patch-attempt-v01`

**行动与关键配置**

- 尝试用单一补丁新增 archive 安全检查、CLI 命令和 4 个测试；
- 多 hunk JavaScript 数组中再次存在未字符串化的 `@@`，脚本在 `apply_patch` 前报 SyntaxError。

**结果**

- `src/defense_mvp/archive.py` 与 `tests/defense_mvp/test_archive.py` 均不存在；
- CLI、ingest 实现和既有 8/8 测试结果未受影响。

**产物路径**

- 无本次目标产物；诊断记录写入 `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 复合补丁脚本格式错误。

**下一步**

1. 分别新增 archive 模块、更新 CLI、增加 tests；
2. 每个补丁只使用单一 hunk 或 Add File；
3. 完成后运行 archive 定向与 Defense MVP 组合回归。

---

### 2026-09-01｜Archive 测试 Python 3.9 类型注解修补脚本失败

**状态：FAILED（未应用兼容性修补）**

**时间与环境**

- 失败时间：2026-09-01 22:15:40 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-archive-test-typing-patch-attempt-v01`

**行动与关键配置**

- archive 模块、CLI 命令和测试文件已分别成功落盘；
- 随后尝试把测试中的 `str | None` 改为 Python 3.9 兼容的 `Optional[str]`；
- 第二个 hunk marker 未字符串化，脚本在调用 `apply_patch` 前失败。

**结果**

- 类型注解仍为 `str | None`；
- archive 实现和测试主体未受影响，测试尚未执行。

**产物路径**

- 已存在但尚未验收：`D:\\lab idea\\src\\defense_mvp\\archive.py`、`D:\\lab idea\\tests\\defense_mvp\\test_archive.py`。

**问题 / 失败**

- 复合修补脚本格式错误。

**下一步**

1. 单独添加 `Optional` import；
2. 单独替换 `_sidecar` 注解；
3. 运行 archive 定向测试。

---

### 2026-09-01｜Defense MVP tar 安全接收与 no-replace 解包

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:16:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用；测试 archive 仅含本地 tiny fixture

**步骤 ID**

- `DEFENSE-MVP-d1-archive-receiver-v01`

**行动与关键配置**

- 新增 `extract-delivery`：校验 tar sidecar SHA、固定 top-level package ID、最多 5,000 members、最多 20 GiB expanded bytes；
- 拒绝绝对路径、`..`、反斜杠、NUL、非 canonical path、重复 member、symlink、hardlink、device 和 FIFO；
- 手工流式解包 regular file，不调用不受控 `extractall`；
- 解包后再次运行完整 `verify_delivery`，只在 package verifier PASS 且 archive before/after SHA 不变时 no-replace 发布；
- 失败 staging 写入诊断并保留为唯一 `.failed` artifact；
- 测试覆盖完整 package 解包复验、tar SHA 不符、path escape 和 symlink。

**结果**

- `tests/defense_mvp/test_archive.py`：4/4 passed；
- `defense --help` 显示 `extract-delivery`；
- compileall 与 `git diff --check` 通过；
- Python 3.9 兼容类型注解已修复。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\archive.py`
- `D:\\lab idea\\src\\defense_mvp\\cli.py`
- `D:\\lab idea\\tests\\defense_mvp\\test_archive.py`

**问题 / 失败**

- 无未解决失败；首次复合补丁和随后类型注解补丁脚本失败均已在前置记录中保留。

**下一步**

1. 运行全部 Defense MVP 测试；
2. 运行全仓库 pytest 和 compileall；
3. 核对配置、CLI、文档、忽略规则和 Git diff 后发布 D1 基线。

---

### 2026-09-01｜Ingest 语义身份加固复合补丁解析失败

**状态：FAILED（语义加固未应用）**

**时间与环境**

- 失败时间：2026-09-01 22:18:11 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-ingest-semantic-hardening-patch-attempt-v01`

**行动与关键配置**

- 代码审阅后已成功把全树 checksum 排除规则从“任意同 basename”收紧为“只排除根 PACKAGE_SHA256SUMS”；
- 随后尝试在一个复合补丁中增加 original candidate config/snapshot、source identity 列表和 sample metadata/crop 交叉验证；
- 复合数组仍含未字符串化 hunk marker，脚本在 `apply_patch` 前失败。

**结果**

- checksum basename 修复已应用；
- 语义身份加固标记不存在，相关代码未部分应用；
- 已通过的 archive/ingest 测试未被本次失败重跑。

**产物路径**

- 已修改待验收：`D:\\lab idea\\src\\defense_mvp\\ingest.py`。

**问题 / 失败**

- 复合 patch 脚本格式错误。

**下一步**

1. 分别补入 candidate、source identity、plan/sample 三组检查；
2. 增加 metadata drift 失败测试；
3. 运行 ingest/Defense/full regression。

---

### 2026-09-01｜Ingest semantic drift 测试补丁解析失败

**状态：FAILED（测试未新增；加固代码待验收）**

**时间与环境**

- 失败时间：2026-09-01 22:19:13 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-ingest-semantic-drift-test-patch-attempt-v01`

**行动与关键配置**

- candidate generation/config/snapshot、source identity lists、plan seed/config 与 sample metadata/crop 加固已通过分块补丁应用；
- 随后尝试新增 manifest instruction drift 失败测试；
- 测试补丁含未字符串化 hunk marker，脚本解析失败。

**结果**

- `ingest.py` 已含语义身份检查；
- `test_manifest_semantic_drift` 尚不存在；
- 加固代码尚未运行测试。

**产物路径**

- 待验收：`D:\\lab idea\\src\\defense_mvp\\ingest.py`。

**问题 / 失败**

- 测试 patch 脚本格式错误。

**下一步**

1. 在单一函数定义前插入 semantic drift 测试；
2. 运行 ingest 定向测试；
3. 通过后记录 semantic hardening 完成。

---

### 2026-09-01｜Semantic drift 测试插入产生重复测试诊断

**状态：FAILED（机械重复；尚未运行测试）**

**时间与环境**

- 诊断时间：2026-09-01 22:19:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-semantic-test-duplicate-diagnosis-v01`

**行动与关键配置**

- semantic drift 测试已插入；
- 只读行审阅发现原 `test_ingest_rejects_existing_output` 被保留，同时生成了内容相同的 `_legacy_removed` 函数。

**结果**

- 测试文件语法完整，但会重复创建/校验同一完整 fixture，徒增运行时间；
- 尚未运行该状态下的测试。

**产物路径**

- 待修：`D:\\lab idea\\tests\\defense_mvp\\test_ingest.py`。

**问题 / 失败**

- 补丁 context 替换方式导致旧函数体被复制。

**下一步**

1. 删除第 76–81 行重复函数；
2. 运行 ingest 定向测试；
3. 记录 semantic hardening 验收。

---

### 2026-09-01｜Ingest original-record 语义身份门加固与定向验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:21:21 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-d1-ingest-semantic-hardening-v01`

**行动与关键配置**

- 收紧 PACKAGE_SHA256SUMS 排除规则，只排除 package 根的 checksum 文件；
- 交叉核验 original candidates 与 package candidate 的 generation_key、code_snapshot、完整 generation config；
- 核验 manifest source identity 中 code/model/AnyV2V commit 集合；
- 核验 original plan candidate/sample/seed/config、sample sequence/task/instruction/target/crop 与 source/mask checksum；
- 新增 instruction drift fail-closed 测试，并删除误生成的重复 existing-output 测试；
- 运行完整 ingest 定向测试。

**结果**

- `tests/defense_mvp/test_ingest.py`：6/6 passed；
- happy ingest、媒体篡改、路径逃逸、semantic drift、既有输出和 CLI verifier 全部覆盖；
- 语义漂移不会在 SHA 更新后绕过 original-record identity gate。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\ingest.py`
- `D:\\lab idea\\tests\\defense_mvp\\test_ingest.py`

**问题 / 失败**

- 无未解决失败；前置 patch 脚本错误和重复测试诊断均已单独保留。

**下一步**

1. 运行全部 Defense MVP 测试；
2. 运行全仓库回归、compileall、CLI/config/doc 静态验收；
3. 完成仓库卫生审计并发布 D1 基线。

---

### 2026-09-01｜Defense MVP D1 全仓库回归

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:28:49 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用；未读取真实 E0、未运行正式 CPU 指标

**步骤 ID**

- `DEFENSE-MVP-d1-full-regression-v01`

**行动与关键配置**

- 在 config/ingest/archive 定向测试全部通过后运行无筛选 `uv run pytest`；
- 测试树包含既有 W1/E1/E2 与新增 Defense MVP 13 项测试；
- 未使用 skip、xfail、mock 冒充正式研究结果或真实媒体。

**结果**

- **116/116 passed**；
- runtime：391.16 秒（6 分 31 秒）；
- Defense MVP 独立 package 未破坏 W1/E1/E2 既有回归。

**产物路径**

- `D:\\lab idea\\tests\\`
- `D:\\lab idea\\src\\defense_mvp\\`

**问题 / 失败**

- 无。

**下一步**

1. 运行 compileall、全部 Defense CLI/config 和文档静态验收；
2. 执行 Git/大文件/忽略规则/路径卫生审计；
3. 形成 D1 审计提交并普通推送。

---

### 2026-09-01｜Defense MVP D1 CLI、编译与文档静态验收

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:29:19 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`，CPU-only
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-d1-static-validation-v01`

**行动与关键配置**

- 运行 `uv run python -m compileall -q src tests`；
- 运行 `uv run defense version`、`uv run defense validate-config` 与 help smoke；
- 检查施工方案/服务器提示词 UTF-8、code fence 配对、行数和 package/checksum/no-replace/800-frame/schema 标记；
- 运行全工作树 `git diff --check`。

**结果**

- compileall 通过；Defense 版本 `0.1.0`；
- 配置输出 10/50/35/15/42 固定计数；
- 施工方案 534 行/8 fences，服务器提示词 341 行/8 fences，UTF-8 与必需标记通过；
- `git diff --check` 通过，仅有 Windows LF/CRLF 提示。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\`
- `D:\\lab idea\\configs\\defense_mvp\\pilot.yaml`
- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`
- `D:\\lab idea\\docs\\defense_mvp\\DATA_HANDOFF_AGENT_PROMPT.md`

**问题 / 失败**

- 无。

**下一步**

1. 扫描待提交路径、ignored/large/binary/absolute-path 泄漏；
2. 核对远端身份和 staged diff；
3. 创建 D1 审计提交并普通推送。

---

### 2026-09-01｜Defense MVP D1 仓库卫生审计

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:29:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未使用

**步骤 ID**

- `DEFENSE-MVP-d1-repository-hygiene-v01`

**行动与关键配置**

- 列出全部 modified/untracked 路径并验证未跟踪项只位于 Defense config/docs/src/tests；
- 扫描新增目录中的视频、数据库、checkpoint、模型、archive 和超过 5 MiB 文件；
- 核对 `uv.lock` 未变化；
- 确认 `data/raw/defense_mvp` 与 `artifacts/defense_mvp` 仍受 gitignore；
- 扫描 code/config/tests 中 Windows 机器绝对路径泄漏；
- 核对最终 `git status --short --branch`。

**结果**

- 待发布范围为 3 个 modified 文件与 14 个 Defense 新文件；
- 无大文件、媒体、模型、数据库、archive 或意外 untracked；
- `__pycache__/*.pyc` 仅为本地 ignored 编译产物，不进入 Git；
- uv.lock 无变化，无新增第三方依赖；
- data/artifacts ignore 与绝对路径扫描通过。

**产物路径**

- 待提交代码与文档：`D:\\lab idea\\configs\\defense_mvp`、`docs\\defense_mvp`、`src\\defense_mvp`、`tests\\defense_mvp`；
- 仓库状态：`D:\\lab idea\\.git`。

**问题 / 失败**

- 无。

**下一步**

1. `git fetch origin` 并核对 `main`/`origin/main` 身份；
2. staged path guard、staged diff 和 staged whitespace；
3. 创建 D1 实现基线提交并普通推送。

---

### 2026-09-01｜Defense MVP D1 发布前远端身份确认

**状态：DONE**

**时间与环境**

- 完成时间：2026-09-01 22:30:28 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：仅 GitHub origin；未连接学校服务器

**步骤 ID**

- `DEFENSE-MVP-d1-prepublish-remote-identity-v01`

**行动与关键配置**

- 执行 `git fetch origin`；
- 核对本地 HEAD、`origin/main` 与 merge-base；
- 远端若前进则 fail-closed，不进入 staging。

**结果**

- HEAD = `b2cffed46f353b5d7b4727c8db5e69d2c27740e2`；
- origin/main = `b2cffed46f353b5d7b4727c8db5e69d2c27740e2`；
- merge-base 相同，无需 rebase/merge；
- 工作树改动仍严格为已审计 Defense D0/D1 范围。

**产物路径**

- Git remote `origin/main`；
- 本地仓库 `D:\\lab idea`。

**问题 / 失败**

- 无。

**下一步**

1. staged path guard 与 staged diff/whitespace；
2. 创建 D1 基线提交；
3. 普通推送到 main 并记录回执。

---

## Defense MVP D1 首次暂存检查（发现 Markdown 行尾空格）

- 完成时间：2026-09-01 22:32:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d1-staged-guard-attempt-01`

**行动与关键配置**

- 使用显式路径暂存 Defense MVP D0/D1 范围，未使用 `git add .`；
- 执行 `git diff --cached --name-status`、`git diff --cached --check`、`git diff --cached --stat`；
- 预期暂存 17 个文件。

**结果**

- 暂存文件数量与范围正确：3 个既有文件修改、14 个 Defense MVP 新文件，共 17 个；
- `git diff --cached --check` 未通过：施工方案第 3–7 行及服务器交接提示词第 3–4 行存在共 7 处 Markdown 行尾空格；
- 未创建提交，未推送。

**产物路径**

- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`；
- `D:\\lab idea\\docs\\defense_mvp\\DATA_HANDOFF_AGENT_PROMPT.md`；
- Git 暂存区。

**问题 / 失败**

- Markdown blockquote 使用了行尾双空格作为换行，但仓库 whitespace guard 将其判为 trailing whitespace；需要改为普通独立引用行。

**下一步**

1. 移除 7 处行尾空格；
2. 重新暂存受影响文档及 DEVLOG；
3. 重跑完整 staged path/whitespace guard。

---

## Defense MVP D1 Markdown whitespace 修复

- 完成时间：2026-09-01 22:32:31 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d1-markdown-whitespace-fix-v01`

**行动与关键配置**

- 移除施工方案顶部 5 处及服务器交接提示词顶部 2 处 Markdown 行尾双空格；
- 保留每项为独立 blockquote 行，文本语义不变。

**结果**

- 7 处已知 trailing whitespace 已清除；
- 未改变施工协议、数据回传契约、代码或测试逻辑。

**产物路径**

- `D:\\lab idea\\docs\\DEFENSE_MVP_CONSTRUCTION_PLAN.md`；
- `D:\\lab idea\\docs\\defense_mvp\\DATA_HANDOFF_AGENT_PROMPT.md`。

**问题 / 失败**

- 无。

**下一步**

1. 重新暂存两份文档和 DEVLOG；
2. 运行最终 staged scope 与 whitespace guard；
3. 创建 D1 基线提交。

---

## Defense MVP D1 最终暂存范围审计

- 完成时间：2026-09-01 22:33:01 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d1-final-staged-guard-v01`

**行动与关键配置**

- 重新暂存修复后的两份文档与 DEVLOG；
- 用显式 17 路径 allowlist 对比 `git diff --cached --name-only`；
- 执行 `git diff --cached --check`；
- 解析 `git diff --cached --numstat` 检查二进制文件。

**结果**

- 预期 17 个文件，实际 17 个；missing=0，extra=0；
- staged whitespace guard 通过；
- staged binary count=0；
- 暂存区仅包含已审计的 Defense MVP D0/D1 文档、配置、代码、测试及授权/日志变更。

**产物路径**

- Git 暂存区；
- `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 无。

**下一步**

1. 将本条记录重新暂存；
2. 创建 Defense MVP D1 基线提交；
3. 普通推送到 `origin/main` 并记录提交与推送回执。

---

## Defense MVP D1 基线提交

- 完成时间：2026-09-01 22:33:25 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d1-baseline-commit-v01`

**行动与关键配置**

- 在最终 staged allowlist 与 whitespace guard 通过后创建提交；
- 提交命令：`git commit -m "Add Defense MVP audited ingest foundation"`；
- 未使用 amend、rebase 或 force push。

**结果**

- 提交成功；
- commit：`f5d5e12c162f19ddae22ea015d3cef368fe23dae`；
- 共提交 17 个文件，3268 insertions、1 deletion；
- 提交完成后工作树干净。

**产物路径**

- Git commit `f5d5e12c162f19ddae22ea015d3cef368fe23dae`；
- 本地分支 `main`。

**问题 / 失败**

- 无。

**下一步**

1. 执行普通 `git push origin main`；
2. 核对远端 SHA；
3. 记录发布回执并创建 DEVLOG-only 审计提交。

---

## Defense MVP D1 基线普通推送回执

- 完成时间：2026-09-01 22:33:52 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：GitHub `origin`；未连接学校服务器

**步骤 ID**

- `DEFENSE-MVP-d1-baseline-push-v01`

**行动与关键配置**

- 执行普通 `git push origin main`；
- 随后使用 `git ls-remote origin refs/heads/main` 核对远端分支身份；
- 未使用 force push。

**结果**

- 推送成功：`b2cffed..f5d5e12  main -> main`；
- 本地 HEAD：`f5d5e12c162f19ddae22ea015d3cef368fe23dae`；
- 远端 `origin/main`：`f5d5e12c162f19ddae22ea015d3cef368fe23dae`；
- 本地与远端 SHA 完全一致。

**产物路径**

- GitHub `origin/main`；
- commit `f5d5e12c162f19ddae22ea015d3cef368fe23dae`。

**问题 / 失败**

- 无。

**下一步**

1. 对当前 DEVLOG-only 变更执行 whitespace 与范围检查；
2. 创建发布回执审计提交并普通推送；
3. 留存最终推送回执，避免无限递归提交日志。

---

## Defense MVP D1 发布回执审计提交与最终推送

- 完成时间：2026-09-01 22:34:35 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：GitHub `origin`；未连接学校服务器

**步骤 ID**

- `DEFENSE-MVP-d1-publication-receipt-push-v01`

**行动与关键配置**

- 确认基线发布后的未提交范围仅有 `DEVLOG.md`；
- 对 DEVLOG-only 变更执行 staged whitespace 与路径检查；
- 创建提交 `git commit -m "Record Defense MVP D1 publication"`；
- 执行普通 `git push origin main` 并用 `git ls-remote` 核对远端 SHA。

**结果**

- 审计提交成功：`c381cc7d1fac268c9df12976b879de1e2451314a`；
- 推送成功：`f5d5e12..c381cc7  main -> main`；
- 本地 HEAD 与远端 `origin/main` 均为 `c381cc7d1fac268c9df12976b879de1e2451314a`；
- 本条最终回执按既有日志策略留在工作树，不再为记录自身递归创建提交。

**产物路径**

- GitHub `origin/main`；
- commit `c381cc7d1fac268c9df12976b879de1e2451314a`；
- `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 无。

**下一步**

1. 用户将服务器交接提示词第 2–11 节发送给服务器端 agent；
2. 服务器端 agent 只读生成固定 ID 的 E0 回传包及 sidecar；
3. 本地使用 `defense extract-delivery` 验收归档，再进入 D2 候选分析与可视化。

---

## Defense MVP 真实 E0 tar 只读兼容性审计

- 完成时间：2026-09-02 22:23:53 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-real-tar-readonly-audit-v01`

**行动与关键配置**

- 对工作区根目录的 `DEFENSE-MVP-E0-HANDOFF-v01.tar` 与 `.tar.sha256` 执行只读检查；
- 验证外层 SHA-256、tar 成员安全性、成员数量、内部 `PACKAGE_SHA256SUMS` 覆盖与逐文件 SHA；
- 在系统临时目录安全解包，按本地固定 schema 临时规范化后运行完整 `verify_delivery`；
- 临时目录限定在系统 temp 下并在验证后删除；原 tar、sidecar、仓库和正式数据目录均未修改。

**结果**

- 外层 tar SHA-256 与 sidecar 一致：`0aa0bd951f4609ef779013d78e424fa373201823a8e16e29cbdd070f3a66abdb`；
- tar 包含 1265 个安全常规文件、0 个特殊成员、0 个重复路径，展开字节数 481708044；
- payload 完整：10 sample、50 candidate、60 MP4、160 source frames、160 masks、800 candidate frames、1259 payload files；
- 内部 SHA 清单含 1264 行、排序唯一、无 tree missing/extra；唯一不匹配文件为 `PACKAGE_VERIFICATION.json`，声明 SHA `548fa365...`、实际 SHA `2c6477c7...`；
- 另确认三类 wire-format 偏差：root-flat tar、verification 缺 `status`、manifest 帧字段/额外 role_counts/样本顺序与本地严格 schema 不同；
- 在临时副本中仅规范化上述控制格式后，完整本地验收通过，全部媒体、original plan/candidates/audit 身份一致；
- 用户选择固定指纹的本地兼容接收，不重新下载 484 MB 媒体。

**产物路径**

- `D:\\lab idea\\DEFENSE-MVP-E0-HANDOFF-v01.tar`；
- `D:\\lab idea\\DEFENSE-MVP-E0-HANDOFF-v01.tar.sha256`；
- 临时审计目录已安全删除，无正式派生产物。

**问题 / 失败**

- 当前严格 `extract-delivery` 会正确拒绝该归档；实施前必须加入只绑定本次精确指纹的显式兼容 profile，且不得放宽默认严格模式。

**下一步**

1. 实现 `server-agent-20260902-v01` 固定指纹 profile；
2. 增加 root-flat 安全提取、控制清单兼容验证与内存规范化；
3. 完成定向测试后才允许真实 extract/ingest。

---

## Defense MVP D2 施工计划状态工具不可用诊断

- 完成时间：2026-09-02 22:23:53 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-plan-tool-unavailable-v01`

**行动与关键配置**

- 尝试调用会话计划状态更新工具登记五阶段施工状态。

**结果**

- 工具返回 `TypeError: tools.update_plan is not a function`；
- 不影响仓库实现或协议，改用 commentary + DEVLOG 维护施工状态。

**产物路径**

- `D:\\lab idea\\DEVLOG.md`。

**问题 / 失败**

- 当前会话未暴露计划状态工具。

**下一步**

1. 不再重试不可用工具；
2. 直接进入兼容 profile 的本地实现；
3. 每个独立步骤继续即时写入 DEVLOG。

---

## Defense MVP 固定指纹兼容接收实现

- 完成时间：2026-09-02 22:31:14 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-pinned-compat-implementation-v01`

**行动与关键配置**

- 新增 `src/defense_mvp/compat.py`，定义 `server-agent-20260902-v01` 固定指纹 profile；
- 将 profile 绑定到真实 archive、manifest、PACKAGE_SHA256SUMS、verification 的精确 SHA、成员数、展开字节数和 checksum 行数；
- 为 archive 增加显式 profile 下的 root-flat 安全检查、no-replace 提取与 sibling compatibility receipt；
- 为 ingest 增加唯一已知 verification checksum 漂移放行、legacy manifest 内存规范化、15 项 server check 验证及 compatibility receipt；
- CLI 的 verify-delivery、ingest、extract-delivery 增加可选 `--compat-profile`，默认严格路径不变；
- 新增 tiny legacy root-flat fixture 测试，覆盖严格拒绝、兼容通过、指纹漂移拒绝和媒体篡改拒绝。

**结果**

- 实现与定向测试代码已写入工作树，尚未运行测试；
- 原始 tar、sidecar、正式 raw/artifacts 目录未修改或创建；
- E0/E1/E2 代码与协议未修改。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\compat.py`；
- `D:\\lab idea\\src\\defense_mvp\\archive.py`；
- `D:\\lab idea\\src\\defense_mvp\\ingest.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_archive.py`。

**问题 / 失败**

- 代码尚未经编译与定向测试，不得用于真实提取。

**下一步**

1. 运行 compileall 与 Defense archive/ingest/config CLI 定向测试；
2. 记录任何失败并修复；
3. 定向测试通过后才对真实 tar 执行兼容 extract。

---

## Defense MVP 固定指纹兼容接收定向验证

- 完成时间：2026-09-02 22:34:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-pinned-compat-targeted-tests-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src/defense_mvp`；
- 执行 `uv run pytest tests/defense_mvp/test_archive.py tests/defense_mvp/test_ingest.py tests/defense_mvp/test_config_cli.py -q`；
- 测试覆盖严格 archive、固定 profile root-flat archive、legacy manifest 规范化、ingest、CLI、指纹与 payload 篡改拒绝。

**结果**

- compileall 通过；
- 定向 pytest 退出码 0，全部用例通过；
- 默认严格模式继续拒绝 root-flat，兼容模式必须显式传入 profile 且固定指纹匹配；
- 尚未执行真实 extract/ingest。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp`；
- `D:\\lab idea\\tests\\defense_mvp`；
- pytest 临时目录由测试框架管理。

**问题 / 失败**

- 无。

**下一步**

1. 对真实 tar 与 sidecar 记录提取前 SHA；
2. 使用固定 `server-agent-20260902-v01` profile no-replace 提取到 raw 目录；
3. 验证提取 receipt 后执行 no-replace ingest。

---

## Defense MVP 真实 E0 tar 固定兼容提取

- 完成时间：2026-09-02 22:36:02 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-real-extract-compat-v01`

**行动与关键配置**

- 执行 `uv run defense extract-delivery --archive DEFENSE-MVP-E0-HANDOFF-v01.tar --checksum DEFENSE-MVP-E0-HANDOFF-v01.tar.sha256 --output data/raw/defense_mvp/e0-delivery-v01 --compat-profile server-agent-20260902-v01`；
- 目标和 sibling receipt 均在执行前确认不存在；
- 提取使用安全成员检查、固定指纹、staging、完整 `verify_delivery` 与 no-replace 发布；
- 执行前后复核 tar 与 sidecar SHA。

**结果**

- 提取成功，status=passed、ready_for_ingest=true；
- archive members=1265，expanded bytes=481708044；
- raw manifest SHA=`6c41bdd0f4d8c35445a2ce6fa26a7d9606226ea5aefb9c1888318ee5d4a4856e`；
- raw package sums SHA=`1ce2e1b87838092e0382489d6ac983c784f6f0fc088d3c29c642c69997e48be5`；
- tar 前后 SHA 均为 `0aa0bd951f4609ef779013d78e424fa373201823a8e16e29cbdd070f3a66abdb`；
- sidecar 前后 SHA 均为 `5155e42e63ffde4fb079c8bef6897e9a0f834db16cd14d35b4c79687d8e034cd`；
- 四条兼容偏差已写入独立 receipt，原始传输输入未改变。

**产物路径**

- `D:\\lab idea\\data\\raw\\defense_mvp\\e0-delivery-v01`；
- `D:\\lab idea\\data\\raw\\defense_mvp\\e0-delivery-v01.compatibility-receipt.json`；
- 原始 tar 与 sidecar 保持在工作区根目录。

**问题 / 失败**

- 无；该 raw 目录仍保留服务器原始 wire shape，后续验证必须继续显式使用同一 compatibility profile。

**下一步**

1. 对提取目录执行 no-replace ingest 到 Defense MVP artifacts；
2. 检查 normalized manifest、compatibility receipt 与 INGEST_SHA256SUMS；
3. 再次确认 raw control hashes 未变化。

---

## Defense MVP 真实 E0 规范化 ingest

- 完成时间：2026-09-02 22:37:02 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；未使用 GPU

**步骤 ID**

- `DEFENSE-MVP-d2-real-ingest-compat-v01`

**行动与关键配置**

- 执行 `uv run defense ingest --delivery data/raw/defense_mvp/e0-delivery-v01 --output artifacts/defense_mvp/DEFENSE-MVP-v01/ingest --compat-profile server-agent-20260902-v01`；
- 使用 staging、内存规范化与 no-replace 发布；
- 输出 normalized manifest、ingest receipt、compatibility receipt 与 INGEST_SHA256SUMS；
- 执行前后复核 raw manifest、sums、verification 三个控制文件 SHA。

**结果**

- ingest 成功，status=passed、ready_for_scoring=true；
- 规范化计数：10 sample、50 candidate、60 MP4、160 source frames、160 masks、800 candidate frames；
- 生成 4 个 ingest 文件；
- raw manifest 前后 SHA 均为 `6c41bdd0f4d8c35445a2ce6fa26a7d9606226ea5aefb9c1888318ee5d4a4856e`；
- raw sums 前后 SHA 均为 `1ce2e1b87838092e0382489d6ac983c784f6f0fc088d3c29c642c69997e48be5`；
- raw verification 前后 SHA 均为 `2c6477c7ae1f66f8af17f8cd81ad1dfc11b0e25d90d6a56bfed79cf1f18bafcc`；
- external_inputs_unchanged=true，兼容偏差已显式保留。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\ingest\\normalized-manifest.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\ingest\\ingest-receipt.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\ingest\\compatibility-receipt.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\ingest\\INGEST_SHA256SUMS`。

**问题 / 失败**

- 无。

**下一步**

1. 实现 CPU 指标 schema、图像加载与 F/P/T/Q 计算；
2. 添加方向性、维度、mask 边界和 no-replace 测试；
3. 定向测试通过后对 35 个真实定量候选运行评分。

---

## Defense MVP CPU F/P/T/Q 评分实现

- 完成时间：2026-09-02 22:42:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-cpu-metrics-implementation-v01`

**行动与关键配置**

- 在冻结配置中加入 `cpu-fptq-v1`、曝光阈值、亮度闪烁尺度和异常帧阈值；
- 新增 `metrics.py`，实现 512×512 RGB/16 帧严格加载、mask 二值化与覆盖率门禁；
- 实现 F=mask 内编辑强度与 HSV 目标色支持度几何平均，local 任务使用新增目标色证据；
- 实现 P=mask 外保持度、T=相邻编辑残差稳定度、Q=梯度保留/曝光/亮度稳定几何平均；
- 定量记录确定性 `metrics.jsonl`，将 CPU 计时独立写入 runtime/receipt，避免污染核心结果 checksum；
- 15 个对象转换候选仅写 `qualitative_only`，不生成伪 F/P/T/Q；
- CLI 新增 `defense score`；新增目标色、背景破坏、闪烁、曝光/模糊、mask/no-replace 方向性测试。

**结果**

- 评分代码、冻结配置与测试已写入工作树，尚未运行测试；
- 真实 ingest 已就绪但尚未运行 score；
- 所有正式输出仍使用 staging + no-replace。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`；
- `D:\\lab idea\\configs\\defense_mvp\\pilot.yaml`；
- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`。

**问题 / 失败**

- 代码尚未编译或执行方向性测试，真实评分仍被门禁阻止。

**下一步**

1. 运行 metrics/config/CLI 定向测试与 compileall；
2. 修复任何数值、schema 或图像接口失败；
3. 通过后对真实 normalized manifest 执行 score。

---

## Defense MVP CPU metrics 首轮定向测试

- 完成时间：2026-09-02 22:43:40 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-cpu-metrics-targeted-tests-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src/defense_mvp`；
- 执行 `uv run pytest tests/defense_mvp/test_metrics.py tests/defense_mvp/test_config_cli.py -q`。

**结果**

- compileall 通过；
- 8 个定向测试全部通过；
- 方向性断言确认目标色提高 F、背景破坏降低 P、闪烁降低 T、过曝平坦帧降低 Q；
- 捕获 32 条相同 Pillow DeprecationWarning：`Image.fromarray(..., mode="RGB")` 的 mode 参数将在 Pillow 13 移除。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`。

**问题 / 失败**

- 数值测试无失败，但弃用警告影响未来兼容性；真实评分前应移除显式 mode 参数并复跑。

**下一步**

1. 将 `Image.fromarray(uint8, mode="RGB")` 改为由数组形状自动推断 RGB；
2. 复跑 metrics 定向测试并要求无 warning；
3. 通过后执行真实 score。

---

## Defense MVP Pillow 13 兼容性修复

- 完成时间：2026-09-02 22:44:14 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-pillow-mode-deprecation-fix-v01`

**行动与关键配置**

- 移除 `Image.fromarray` 已弃用的显式 `mode="RGB"` 参数；
- 保留 uint8 H×W×3 输入，由 Pillow 按数组形状推断 RGB。

**结果**

- 单行兼容性修复已写入；
- 指标公式和输出 schema 未改变；
- 尚待复跑测试确认警告消失。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`。

**问题 / 失败**

- 无新增问题。

**下一步**

1. 复跑 metrics 定向测试；
2. 确认 8/8 通过且不再出现 Pillow warning；
3. 执行真实 CPU 评分。

---

## Defense MVP CPU metrics 无警告复验

- 完成时间：2026-09-02 22:45:14 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-cpu-metrics-targeted-tests-v02`

**行动与关键配置**

- 执行 `uv run pytest tests/defense_mvp/test_metrics.py tests/defense_mvp/test_config_cli.py -q`；
- 观察 pytest 完整输出与退出码。

**结果**

- 8/8 定向测试通过；
- 退出码 0；
- Pillow DeprecationWarning 已消失，无 warning summary。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`。

**问题 / 失败**

- 无。

**下一步**

1. 对真实 50 候选执行 CPU score；
2. 验证 35 scored、15 qualitative_only、无 NaN/Inf；
3. 记录 metrics/config/runtime/checksum 产物并复跑确定性检查。

---

## Defense MVP 真实 CPU 评分首轮失败：mask 覆盖率门禁

- 完成时间：2026-09-02 22:46:03 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-score-attempt-01`

**行动与关键配置**

- 执行 `uv run defense score --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/metrics`；
- 使用冻结 `cpu-fptq-v1` 与 mask fraction `[0.001, 0.95]` 门禁；
- 输出采用 staging + no-replace。

**结果**

- 评分失败并 fail-closed，未发布正式 `metrics/`；
- 错误：`ValueError: mask fraction falls outside the frozen protocol`；
- 失败发生于真实定量候选处理期间；
- 失败 staging 已保留，包含 `SCORING_FAILED.json`。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\.metrics.score-184d1a77906a4cd1b1f9cf32c3b79e9e.failed`；
- 正式 `metrics/` 不存在。

**问题 / 失败**

- 当前逐帧 mask 门禁可能把真实 DAVIS 中目标暂时离开画面的空帧判为整组失败；尚不能在未审计覆盖率分布前放宽协议。

**下一步**

1. 只读统计 10 个样本、160 张 mask 的逐帧和样本总体覆盖率；
2. 定位所有越界帧及其 sample；
3. 根据真实分布决定保持逐帧门禁或改为“总体门禁 + 空帧显式记录”。

---

## Defense MVP 真实 mask 覆盖率诊断

- 完成时间：2026-09-02 22:46:47 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only 只读分析

**步骤 ID**

- `DEFENSE-MVP-d2-real-mask-fraction-diagnostic-v01`

**行动与关键配置**

- 从 normalized manifest 读取 10×16 个 mask 相对路径；
- 逐个校验已提取 mask 后使用 Pillow `convert("L") / 255 >= 0.5` 计算前景比例；
- 汇总每个 sample 的 min/mean/max、空帧数和越界帧数。

**结果**

- 10 个 sample 的 160 张 mask 在当前转换方式下全部得到 fraction=0；
- 每个 sample 均为 empty=16、out=16；
- 这不是少数目标离场帧，而是 mask 解码语义错误的强信号；
- 原始 mask checksum 与 ingest 均已通过，因此不得请求重传或修改 mask，需检查 PNG mode、原始像素索引和 palette。

**产物路径**

- 只读输入：`D:\\lab idea\\data\\raw\\defense_mvp\\e0-delivery-v01\\media\\sources\\*\\masks\\*.png`；
- 未生成新的正式产物。

**问题 / 失败**

- 对 palette/indexed DAVIS mask 使用灰度亮度和 0.5 阈值可能把类别索引 1 转成接近 0，错误抹去前景。

**下一步**

1. 只读检查各 sample 第一张 mask 的 mode、原始像素 unique values、灰度 unique values 和 palette；
2. 确认 DAVIS mask 应按非零索引还是亮度二值化；
3. 冻结正确解码协议、增加回归测试后再评分。

---

## Defense MVP DAVIS palette mask 语义确认

- 完成时间：2026-09-02 22:47:27 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only 只读分析

**步骤 ID**

- `DEFENSE-MVP-d2-mask-palette-semantics-v01`

**行动与关键配置**

- 读取 10 个 sample 第一张真实 mask 的 Pillow mode、size、原始数组 shape/unique/max、灰度转换 unique/max 与 palette 前 4 色；
- 不修改 mask 或 manifest。

**结果**

- 10/10 mask 均为 512×512 `P` palette/indexed PNG；
- 原始像素为类别索引：背景 0，前景对象为 1，部分多对象样本包含 2/3/4/5；
- palette 索引 1 的 RGB 为 `(128,0,0)`，灰度亮度仅 38/255，低于 0.5；
- 因此 `convert("L")/255 >= 0.5` 与 DAVIS 索引 mask 语义不兼容；正确协议是对 `P`/`L` 单通道原始索引执行 `raw > 0`，覆盖所有前景对象。

**产物路径**

- 只读输入：`D:\\lab idea\\data\\raw\\defense_mvp\\e0-delivery-v01\\media\\sources\\*\\masks\\00000.png`；
- 未生成新的正式产物。

**问题 / 失败**

- 冻结配置中的通用 `mask_threshold=0.5` 不能直接解释 palette 类别索引；需增加显式 `mask_decode=index-nonzero`，保留阈值仅作为 RGB/灰度 fallback 的防御路径。

**下一步**

1. 将 mask 协议冻结为 `index-nonzero-v1`；
2. loader 对 `P`/整数单通道执行原始索引非零，对其他模式 fail-closed；
3. 新增 palette mask 回归测试并复跑后再次执行真实 score。

---

## Defense MVP DAVIS 索引 mask 解码修复

- 完成时间：2026-09-02 22:48:39 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-mask-index-decode-fix-v01`

**行动与关键配置**

- 冻结配置新增 `mask_decode: index-nonzero-v1`；
- mask loader 只接受 512×512 的 `1/L/P/I/I;16` 单通道整数图像，按原始类别索引 `raw != 0` 二值化；
- RGB 或非整数二维 mask fail-closed；
- metrics protocol lock 增加 mask decode 身份；
- 新增真实 DAVIS palette 形态回归 fixture：索引 1 即使 palette 亮度低于 0.5，也必须得到 25% 前景。

**结果**

- 解码实现与测试已写入工作树；
- 原 `mask_threshold` 保留在配置以维持既有 schema/审计信息，但正式 `cpu-fptq-v1` 使用显式 index-nonzero 解码；
- 尚未复跑测试或真实评分。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`；
- `D:\\lab idea\\configs\\defense_mvp\\pilot.yaml`；
- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`。

**问题 / 失败**

- 需复验全部方向性测试及真实 mask 覆盖率。

**下一步**

1. 运行 metrics/config 定向测试；
2. 只读复核新解码后的 160 帧 mask fraction；
3. 通过后重跑真实 score 到同一尚不存在的正式输出目录。

---

## Defense MVP 索引 mask 解码定向复验

- 完成时间：2026-09-02 22:49:22 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-mask-index-decode-tests-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/defense_mvp/test_metrics.py tests/defense_mvp/test_config_cli.py -q`；
- 包含新增 palette/index 1 回归用例和原 8 个配置/方向性用例。

**结果**

- 9/9 测试通过，退出码 0；
- palette 索引 mask 被正确解码；
- 无 warning 输出。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`。

**问题 / 失败**

- 无。

**下一步**

1. 使用新解码对真实 160 张 mask 做覆盖率复核；
2. 确认所有逐帧值处于冻结范围；
3. 重跑真实 CPU score。

---

## Defense MVP 真实 mask 覆盖率复验

- 完成时间：2026-09-02 22:50:02 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only 只读分析

**步骤 ID**

- `DEFENSE-MVP-d2-real-mask-fraction-index-v01`

**行动与关键配置**

- 使用冻结 `index-nonzero-v1` 对 10×16 张真实 palette mask 的原始索引执行 `raw != 0`；
- 汇总逐 sample min/mean/max 和全体 outlier 数；
- 门禁仍为每帧 `[0.001, 0.95]`。

**结果**

- 全部 160 帧通过覆盖率门禁，outliers=0；
- 全局 mask fraction：min=0.01052094、mean=0.23733137、max=0.77602768；
- 各 sample 均有非空、非全屏前景；
- 证实失败根因仅为旧解码方式，不需要重传或改动 mask 文件。

**产物路径**

- 只读输入：`D:\\lab idea\\data\\raw\\defense_mvp\\e0-delivery-v01\\media\\sources\\*\\masks\\*.png`；
- 未生成新的正式产物。

**问题 / 失败**

- 无。

**下一步**

1. 重新执行真实 CPU score；
2. 验证 35 scored、15 qualitative_only 与数值有限性；
3. 记录运行耗时、核心 metrics SHA 和 score range。

---

## Defense MVP 真实 CPU F/P/T/Q 评分

- 完成时间：2026-09-02 22:51:09 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-score-v01`

**行动与关键配置**

- 执行 `uv run defense score --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/metrics`；
- 使用 `cpu-fptq-v1`、`index-nonzero-v1`、冻结 HSV 与质量阈值；
- 对正式输出使用 staging + no-replace。

**结果**

- status=passed、ready_for_design=true；
- records=50、scored=35、qualitative_only=15；
- CPU 总耗时 27.6706619 秒；
- deterministic metrics SHA=`c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac`；
- config SHA=`19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae`；
- ingest manifest SHA=`b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46`。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\metrics.jsonl`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\metrics-summary.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\metrics-config-lock.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\scoring-runtime.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\score-receipt.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics\\METRICS_SHA256SUMS`。

**问题 / 失败**

- 无；第一次失败 staging 按审计策略保留，未混入正式 metrics。

**下一步**

1. 对 metrics.jsonl 做独立数量、状态、NaN/Inf、per-frame 长度与范围审计；
2. 记录各维度真实 range 和异常帧统计；
3. 完成确定性复跑比较后冻结评分结果。

---

## Defense MVP 真实 metrics 独立完整性审计

- 完成时间：2026-09-02 22:52:04 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only 分析

**步骤 ID**

- `DEFENSE-MVP-d2-real-metrics-audit-v01`

**行动与关键配置**

- 独立解析正式 `metrics.jsonl`；
- 检查记录数、candidate_id 唯一性、measurement_status、四维有限性与 `[0,1]` 范围；
- 检查 scored 记录所有 per-frame 数组长度=16且数值有限；
- 检查 qualitative-only 的 scores/components/per_frame 均为 null；
- 重新计算 `METRICS_SHA256SUMS` 的 5 个输出文件 SHA。

**结果**

- 50 条记录、50 个唯一 candidate；35 scored、15 qualitative_only；
- metric issues=0、checksum issues=0；
- F：min=0.24500902、mean=0.37941274、max=0.51488656；
- P：min=0.63243108、mean=0.85778881、max=0.92709654；
- T：min=0.83419970、mean=0.88285783、max=0.92250283；
- Q：min=0.73411954、mean=0.88467864、max=0.97139819；
- 35 个 scored 候选共标记 14 个异常帧，保留为质量代理解释信息，不删除候选。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics`。

**问题 / 失败**

- 无。

**下一步**

1. 输出到唯一 `metrics-replay-v01` 目录执行第二次真实评分；
2. 比较 metrics.jsonl、metrics-summary.json、metrics-config-lock.json SHA；
3. 核心确定性产物一致后进入 design/selection 实现。

---

## Defense MVP 真实 CPU metrics 确定性复跑

- 完成时间：2026-09-02 22:53:16 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-score-replay-v01`

**行动与关键配置**

- 使用相同 normalized ingest 与冻结配置，no-replace 输出到 `metrics-replay-v01`；
- 比较 primary/replay 的 `metrics.jsonl`、`metrics-summary.json`、`metrics-config-lock.json` SHA；
- runtime/receipt 按设计不纳入确定性相等要求。

**结果**

- replay status=passed、35 scored、15 qualitative_only；
- replay CPU 总耗时 28.5469304 秒；
- `metrics.jsonl` SHA 两次均为 `c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac`；
- `metrics-summary.json` SHA 两次均为 `7f5f6f3e008dfdccf29e21e31f17ba933dd9416eb053c5c0458491742cedd9a8`；
- `metrics-config-lock.json` SHA 两次均为 `65b3ec0124e32703ca6e1046c9c460d0e1af383d19690c9693e75754cf1e74f7`；
- 三项 deterministic artifacts 全部 MATCH=True。

**产物路径**

- primary：`D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics`；
- replay：`D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\metrics-replay-v01`。

**问题 / 失败**

- 无；CPU runtime 的小幅差异按协议只作为成本测量保留。

**下一步**

1. 冻结 primary metrics SHA 与 config lock；
2. 实现五次 cyclic N=1/2/4 design、random/linear/constrained Pareto；
3. 生成 42 个正式 blind comparison 计划并验证 determinism。

---

## Defense MVP N=1/2/4 设计与三方法选择实现

- 完成时间：2026-09-02 22:58:20 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-design-selection-implementation-v01`

**行动与关键配置**

- 新增 `design.py`：验证 50 条 metrics 与 ingest identity，为 7 个定量 sample 建立 5 次 cyclic trial 和 N=1/2/4 嵌套前缀；
- design 同时携带 source/instruction/candidate media 相对路径，仅供后续盲评呈现；
- 新增 `selection.py`：子集内稳定 rank-percentile、确定性 random、等权 linear、F/P 门禁的 constrained Pareto + max-min/geomean/fallback；
- 生成 315 条 selection 和固定 42 条 comparison：28 条 Proposed N=4 vs N=1，14 条 Proposed vs Linear N=4；
- comparison 保留 candidate 角色和 checksum，不提前指定 annotator A/B 方向；
- CLI 新增 `defense design` 与 `defense select`；
- 新增 cyclic 覆盖/嵌套、稳定并列 rank、Pareto 支配/max-min、显式 fallback 和错误 cardinality 测试。

**结果**

- 设计、选择、CLI 与测试代码已写入工作树，尚未编译或运行；
- 正式 metrics 保持冻结且未修改；
- 未启动人工标注。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\design.py`；
- `D:\\lab idea\\src\\defense_mvp\\selection.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_design_selection.py`。

**问题 / 失败**

- 代码尚未通过定向测试；42 条真实比较尚未生成。

**下一步**

1. 运行 compileall 与 design/selection/config CLI 定向测试；
2. 修复任何算法或 schema 失败；
3. 通过后对冻结真实 metrics 创建 no-replace design 与 selection。

---

## Defense MVP design/selection 定向验证

- 完成时间：2026-09-02 22:58:58 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-design-selection-targeted-tests-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src/defense_mvp`；
- 执行 `uv run pytest tests/defense_mvp/test_design_selection.py tests/defense_mvp/test_config_cli.py -q`。

**结果**

- compileall 通过；
- 8/8 定向测试通过，退出码 0；
- cyclic balance/nesting、rank tie-break、Pareto/max-min 与 fallback 均满足冻结协议；
- 无 warning。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\design.py`；
- `D:\\lab idea\\src\\defense_mvp\\selection.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_design_selection.py`。

**问题 / 失败**

- 无；真实 design/selection 尚未运行。

**下一步**

1. 使用正式 metrics 与 normalized ingest 创建真实 design；
2. 运行真实 selection 并生成 42 comparison；
3. 审计 315 selection、42 comparison、自动 tie 与 fallback 统计。

---

## Defense MVP 真实 N=1/2/4 cyclic design

- 完成时间：2026-09-02 22:59:41 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-design-v01`

**行动与关键配置**

- 执行 `uv run defense design --metrics artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/metrics.jsonl --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/design`；
- 使用 7 个定量 sample、5 次 cyclic replicate、N=1/2/4 前缀；
- 输出采用 staging + no-replace，并锁定 config/metrics/ingest SHA。

**结果**

- status=passed、ready_for_selection=true；
- samples=7、trials=35、subsets=105；
- design SHA=`891ee8b0d75acf5c825fd01d529d545f12a7fb1b72a4310364a805d8d6cd1ff5`。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\design\\design.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\design\\design-lock.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\design\\design-receipt.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\design\\DESIGN_SHA256SUMS`。

**问题 / 失败**

- 无。

**下一步**

1. 对真实 design 运行三方法 selection；
2. 生成 42 个 blind comparison；
3. 独立验证 family 数量、媒体身份、automatic tie 与 fallback。

---

## Defense MVP 真实三方法 selection 与比较计划

- 完成时间：2026-09-02 23:00:18 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-selection-v01`

**行动与关键配置**

- 执行 `uv run defense select --design artifacts/defense_mvp/DEFENSE-MVP-v01/design/design.json --metrics artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/metrics.jsonl --output artifacts/defense_mvp/DEFENSE-MVP-v01/selection`；
- 每个 trial/N 同时运行 random、equal-linear、constrained-pareto；
- 输出 42 个盲评 comparison，尚未随机化到 annotator A/B 方向；
- 使用 staging + no-replace。

**结果**

- status=passed、ready_for_annotation=true；
- selection records=315；
- comparisons=42，其中 N4 vs N1=28、Pareto vs Linear N4=14；
- automatic ties=10；
- constrained Pareto fallbacks=26（跨全部 N/trial 记录统计，包含容易退化的 N=2 子集）；
- selections SHA=`aae1410de8d9d90c1266c43cadf17f1fce8666bdc163b709d82504689b38afaf`；
- comparisons SHA=`486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb`。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection\\selections.jsonl`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection\\comparisons.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection\\selection-summary.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection\\selection-lock.json`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection\\SELECTION_SHA256SUMS`。

**问题 / 失败**

- 自动 ties 和 fallback 数量较高但属于协议允许结果；不得为制造方法差异而调阈值，需独立审计其分布与主比较影响。

**下一步**

1. 独立审计 315 selection 与 42 comparison 的唯一性、family/replicate 覆盖、checksum join；
2. 分解 fallback 和 automatic tie 的 N/sample 分布；
3. 确认盲评有效人工工作量后执行确定性 replay。

---

## Defense MVP 真实 selection/comparison 独立审计

- 完成时间：2026-09-02 23:01:19 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only 分析

**步骤 ID**

- `DEFENSE-MVP-d2-real-selection-audit-v01`

**行动与关键配置**

- 独立解析 selections.jsonl、comparisons.json 与 normalized ingest；
- 检查 selection key/comparison ID 唯一性、method/N/family/replicate 覆盖；
- 将所有 selection/comparison candidate SHA 与 ingest 重新 join；
- 重新计算 automatic ties、fallback 分布与 SELECTION_SHA256SUMS。

**结果**

- 315/315 唯一 selection keys；每个 method 各 105 条，每个 N 各 105 条；
- 42/42 唯一 comparison IDs；N4-vs-N1 各 replicate 1–4 每个 7 条，Pareto-vs-Linear replicate 1–2 每个 7 条；
- identity issues=0、checksum issues=0；
- 26 次 fallback 全部发生于 N=2：bear 3、bus 4、car-headlights 5、classic-car 3、elephant 4、hiker 3、rider 4；N=1/N=4 无 fallback；
- 10 个 automatic ties 复算一致：N4-vs-N1 6，Pareto-vs-Linear 4；
- 需要人工观看的 comparison 为 32 个，10 个 automatic tie 仍保留在统计分母。

**产物路径**

- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection`；
- `D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\ingest\\normalized-manifest.json`。

**问题 / 失败**

- N=2 的离散 rank 门槛在 F/P 排名相反时高频进入已定义 fallback；主比较只使用 N=1/N=4，因此不影响 42 条主协议，但应在报告中解释。

**下一步**

1. no-replace 生成 `selection-replay-v01`；
2. 比较 selections、comparisons、summary、lock 的 SHA；
3. 确定性通过后运行全 Defense 与全仓库回归。

---

## Defense MVP 真实 selection 确定性复跑

- 完成时间：2026-09-02 23:02:06 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-real-selection-replay-v01`

**行动与关键配置**

- 使用相同 design/metrics no-replace 生成 `selection-replay-v01`；
- 比较 primary/replay 的 selections、comparisons、summary、lock 四个核心文件 SHA。

**结果**

- replay status=passed，315 selection、42 comparison、10 automatic ties、26 fallbacks；
- `selections.jsonl` SHA 均为 `aae1410de8d9d90c1266c43cadf17f1fce8666bdc163b709d82504689b38afaf`；
- `comparisons.json` SHA 均为 `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb`；
- `selection-summary.json` SHA 均为 `2cf97da4f8bf704bbd7d2d9e62f1e8237873db89a805aefc168266133b115f3f`；
- `selection-lock.json` SHA 均为 `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2`；
- 四项 MATCH=True。

**产物路径**

- primary：`D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection`；
- replay：`D:\\lab idea\\artifacts\\defense_mvp\\DEFENSE-MVP-v01\\selection-replay-v01`。

**问题 / 失败**

- 无。

**下一步**

1. 运行全 Defense 测试；
2. 运行全仓库 pytest 回归；
3. 执行 CLI smoke、文档/whitespace/path/hygiene 审计并准备提交。

---

## Defense MVP D2 全套测试

- 完成时间：2026-09-02 23:05:46 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-full-defense-tests-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/defense_mvp -q`；
- 覆盖 config/CLI、严格与兼容 archive、ingest、CPU metrics、cyclic design、三方法 selection。

**结果**

- Defense MVP 全套测试全部通过，退出码 0；
- 无失败或 warning summary；
- 真实 artifacts 未被测试覆盖或修改，测试使用 pytest 临时目录。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp`；
- pytest 临时产物由测试框架管理。

**问题 / 失败**

- 无。

**下一步**

1. 运行全仓库 pytest；
2. 若旧 E0/E1/E2 测试通过，再运行 CLI smoke 与静态审计；
3. 准备精确 staged allowlist。

---

## Defense MVP D2 全仓库回归首轮收集失败

- 完成时间：2026-09-02 23:06:23 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-full-regression-attempt-01`

**行动与关键配置**

- 执行 `uv run pytest -q`。

**结果**

- pytest 在 collection 阶段退出码 1，未进入测试执行；
- 错误为 import file mismatch：新增 `tests/defense_mvp/test_metrics.py` 与既有 `tests/e1/test_metrics.py` 均被作为顶层模块 `test_metrics` 导入；
- 这是测试文件 basename 冲突，不是指标或旧协议测试失败。

**产物路径**

- 冲突文件：`D:\\lab idea\\tests\\defense_mvp\\test_metrics.py`；
- 既有文件：`D:\\lab idea\\tests\\e1\\test_metrics.py`。

**问题 / 失败**

- Defense 测试 basename 不唯一，破坏全仓库 pytest 收集。

**下一步**

1. 将 Defense 测试文件改名为 `test_cpu_metrics.py`，不改测试内容；
2. 先运行两个同类测试文件确认可共同收集；
3. 再重跑全仓库 pytest。

---

## Defense MVP 测试文件首次 rename patch 失败

- 完成时间：2026-09-02 23:06:57 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-test-file-rename-attempt-01`

**行动与关键配置**

- 尝试使用 `apply_patch` 的 Move 语法将 `test_metrics.py` 改名为 `test_cpu_metrics.py`；
- patch 未包含内容 hunk。

**结果**

- apply_patch 拒绝空 hunk：`Update file hunk ... is empty`；
- 文件未移动、内容未改变。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp\\test_metrics.py` 仍在原位。

**问题 / 失败**

- Move patch 必须包含至少一个有效内容 hunk。

**下一步**

1. 在 Move patch 中同时加入模块 docstring，形成有效 hunk；
2. 核对旧路径消失、新路径存在；
3. 运行双文件收集验证。

---

## Defense MVP CPU metrics 测试文件唯一化

- 完成时间：2026-09-02 23:07:30 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-test-file-rename-v01`

**行动与关键配置**

- 使用带有效 hunk 的 apply_patch Move 将 `tests/defense_mvp/test_metrics.py` 改名为 `test_cpu_metrics.py`；
- 增加说明性模块 docstring；
- 核对旧路径与新路径存在性。

**结果**

- 旧路径存在=False，新路径存在=True；
- 测试逻辑未改变；
- basename 已与 `tests/e1/test_metrics.py` 区分。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp\\test_cpu_metrics.py`。

**问题 / 失败**

- 尚未验证 pytest 双文件共同收集。

**下一步**

1. 同时运行 Defense CPU metrics 与 E1 metrics 测试；
2. 收集成功后重跑全仓库 pytest；
3. 记录回归结果。

---

## Defense/E1 metrics 双文件收集复验

- 完成时间：2026-09-02 23:08:27 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-metrics-test-module-collision-retest-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/defense_mvp/test_cpu_metrics.py tests/e1/test_metrics.py -q`。

**结果**

- 11/11 测试通过，退出码 0；
- 两个 metrics 测试模块共同收集成功，import file mismatch 已消除；
- 无 warning。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp\\test_cpu_metrics.py`；
- `D:\\lab idea\\tests\\e1\\test_metrics.py`。

**问题 / 失败**

- 无。

**下一步**

1. 重跑全仓库 pytest；
2. 若通过，执行 CLI help/smoke 与 compileall；
3. 完成 git hygiene/staged allowlist 审计。

---

## Defense MVP D2 全仓库回归复验

- 完成时间：2026-09-02 23:21:27 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-full-regression-v02`

**行动与关键配置**

- 修复测试模块 basename 冲突后重新执行 `uv run pytest -q`；
- 等待完整 suite 自然结束，未中断或缩减旧 E0/E1/E2 测试。

**结果**

- 全仓库 pytest 达到 100%，退出码 0；
- 新 Defense MVP 与既有 W1/E0/E1/E2 测试全部通过；
- 无失败堆栈或 warning summary。

**产物路径**

- `D:\\lab idea\\tests`；
- pytest cache（非研究产物）。

**问题 / 失败**

- 无。

**下一步**

1. 运行 defense CLI help/version/config 与新增命令 help smoke；
2. 运行 compileall、git diff --check、绝对路径/大文件/ignored artifact 审计；
3. 审阅 staged allowlist 并准备审计提交。

---

## Defense MVP D2 CLI 与编译 smoke

- 完成时间：2026-09-02 23:22:13 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-cli-compile-smoke-v01`

**行动与关键配置**

- 执行 `uv run python -m compileall -q src/defense_mvp`；
- 执行 defense version、validate-config、根 help；
- 分别检查 extract-delivery、score、design、select help 的必需参数与 compat option。

**结果**

- compileall 通过；
- defense version=`0.1.0`；
- validate-config 返回 valid=true、10 sample、50 candidate、35 quantitative、15 qualitative、42 comparisons；
- 根 CLI 正确注册 score/design/select/extract-delivery；
- extract 暴露 `--compat-profile`，score/design/select 的 metrics/ingest/design/output 参数正确显示。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\cli.py`；
- `D:\\lab idea\\configs\\defense_mvp\\pilot.yaml`。

**问题 / 失败**

- 无。

**下一步**

1. 运行 git diff whitespace、status、tracked/untracked scope 审计；
2. 确认 tar/sidecar/raw/artifacts 均未进入 staged 范围；
3. 修复任何 hygiene 问题后提交。

---

## Defense MVP D2 工作树与大文件 hygiene 审计

- 完成时间：2026-09-02 23:23:14 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；仅本地 Git 审计

**步骤 ID**

- `DEFENSE-MVP-d2-worktree-hygiene-audit-v01`

**行动与关键配置**

- 执行 `git diff --check`、`git status --short`、`git diff --stat`；
- 列出全部未跟踪文件及字节数；
- 检查 tracked files 中大于 10 MiB 的文件；
- 搜索 Defense src/tests/config 中 Windows、DATA4 与 server absolute path；
- 使用 `git check-ignore -v` 检查 raw/artifacts/tar 状态。

**结果**

- `git diff --check` 通过；
- tracked large files >10 MiB 数量=0；
- raw 与 artifacts 分别由 `.gitignore` 的 `data/raw/` 和 `artifacts/` 规则排除；
- 484 MB tar 与 97-byte sidecar 保持可见未跟踪状态，尚未且不得暂存；
- 其余 6 个未跟踪文件均为预期 Defense 源码/测试；
- absolute path 搜索的 7 条命中全部来自既有 tiny fixture 的虚构 `/server/...` provenance 字段，不是本地/真实 DATA4 泄漏；
- 当前 tracked 修改严格集中于 DEVLOG、Defense config/src/tests。

**产物路径**

- 工作树 `D:\\lab idea`；
- `.gitignore` 既有规则；
- 原始 tar/sidecar 未暂存。

**问题 / 失败**

- tar 根目录文件未被 `.gitignore` 隐藏，必须继续使用显式 staged allowlist，禁止 `git add .`。

**下一步**

1. 审阅代码差异与静态潜在问题；
2. 精确暂存 DEVLOG、Defense config/src/tests，排除 tar/sidecar；
3. staged path/whitespace/binary guard 通过后提交并普通推送。

---

## Defense MVP 定性候选媒体解码门禁加固

- 完成时间：2026-09-02 23:24:52 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-qualitative-media-validation-hardening-v01`

**行动与关键配置**

- 静态审阅评分路径后，将 15 个 qualitative-only 候选从“仅 checksum”加固为“checksum + 16 帧 512×512 RGB 解码”；
- 三个定性 sample 的 source frames 和 indexed masks 也执行完整 mode/尺寸/解码验证；
- score 入口新增候选 sample/seed 固定矩阵顺序检查；
- 新增灰度候选帧必须被 RGB loader 拒绝的回归测试。

**结果**

- 加固代码与测试已写入工作树；
- qualitative-only 仍保持 scores/components/per_frame=null，不改变研究边界；
- 尚未测试或对真实数据复跑。

**产物路径**

- `D:\\lab idea\\src\\defense_mvp\\metrics.py`；
- `D:\\lab idea\\tests\\defense_mvp\\test_cpu_metrics.py`。

**问题 / 失败**

- 需确认真实 15 个对象候选全部可按 RGB 解码，且核心 35 候选 metrics SHA 不变。

**下一步**

1. 运行 CPU metrics 定向测试；
2. 使用新唯一 replay 目录对真实 50 候选复跑；
3. 比较核心 metrics/summary/lock SHA 后再做最终回归。

---

## Defense MVP 定性媒体解码门禁定向测试

- 完成时间：2026-09-02 23:25:44 +08:00
- 执行位置：本地 Windows 工作区 `D:\\lab idea`
- 远程环境：未连接学校服务器；CPU-only

**步骤 ID**

- `DEFENSE-MVP-d2-qualitative-media-validation-tests-v01`

**行动与关键配置**

- 执行 `uv run pytest tests/defense_mvp/test_cpu_metrics.py -q`；
- 覆盖新增非 RGB 帧拒绝、palette mask、F/P/T/Q 方向性和 no-replace。

**结果**

- 7/7 测试通过，退出码 0；
- 无 warning。

**产物路径**

- `D:\\lab idea\\tests\\defense_mvp\\test_cpu_metrics.py`。

**问题 / 失败**

- 无。

**下一步**

1. no-replace 生成 `metrics-replay-v02`；
2. 验证 50 个候选全部通过解码，35/15 边界不变；
3. 比较三项确定性核心 SHA。

---

## Defense MVP 中断恢复：补录最终媒体验证复跑

- 复跑产物时间：2026-09-02 23:27:06 +08:00（score-receipt.json LastWriteTime）
- 核对与补录时间：2026-09-03 09:36:06 +08:00
- 环境：本地 Windows `D:\lab idea`，CPU-only；未连接学校服务器。
- 步骤 ID：`DEFENSE-MVP-d2-qualitative-media-replay-v02-reconciled`
- 行动：恢复昨晚中断现场，读取已存在的 `metrics-replay-v02/score-receipt.json`、runtime 和三项核心文件 SHA；未重新评分或覆盖目录。首次读取误用了 `scoring-receipt.json`，文件枚举确认实际文件名为 `score-receipt.json`，无产物缺失。
- 原运行关键配置：`defense score --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/metrics-replay-v02`；最终代码包含所有定性帧的 RGB 解码门禁；配置 SHA `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae`。
- 结果：回执 passed，50 条记录、35 scored、15 qualitative_only，CPU 时间 52.3457099 秒。三项确定性输出与首次成功评分一致：metrics `c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac`；summary `7f5f6f3e008dfdccf29e21e31f17ba933dd9416eb053c5c0458491742cedd9a8`；lock `65b3ec0124e32703ca6e1046c9c460d0e1af383d19690c9693e75754cf1e74f7`。
- 产物：`artifacts/defense_mvp/DEFENSE-MVP-v01/metrics-replay-v02/`，保留原目录和历史失败诊断。
- 剩余任务：审阅最终代码与施工文档；最终全仓回归、输入/输出身份复核；显式暂存审计、提交并普通推送 main。D3 界面与正式双人盲评尚未开始。

## Defense MVP 恢复后最终实现核对

- 时间：2026-09-03 09:38:00 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-resume-code-review-v01`。
- 行动：逐一读取 archive/compat/ingest/models/metrics/design/selection/CLI、配置与现有测试，对照批准的 D2 计划；读取真实 ingest receipt。
- 结果：固定兼容指纹、原始文件保留、35/15 隔离、三方法和 42 比较均已有实现。真实交接 warnings 和 missing_optional_artifacts 均为空；四类兼容偏差已单列。最终复跑没有改变指标公式或核心 SHA。运行计时用 perf_counter，字段虽名为 cpu_seconds，语义是 CPU-only 流水线经过时间，不是进程 CPU 核时。
- 验收补强：现有方向性测试将曝光和梯度退化合在一个案例；补充独立模糊、local 已有目标色排除、真正 Pareto 支配、全三方法确定性和兼容控制/身份篡改测试。只增加测试，不改变冻结算法或真实结果。
- 产物：`src/defense_mvp/`、`tests/defense_mvp/`、`configs/defense_mvp/pilot.yaml`；原始数据不变。
- 下一步：补足验收测试和 D2 文档；已经启动的最终全仓回归结束后立即记录，新增测试另做完整 Defense 定向回归。

## Defense MVP D2 验收覆盖补强

- 时间：2026-09-03 09:40 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-resume-acceptance-tests-v01`。
- 行动：新增 local 已有颜色排除、独立模糊质量退化、可行集内支配消除、完整 synthetic 三方法流水线确定性/no-replace/checksum，以及七类兼容包篡改和未知 profile 拒绝测试。
- 配置：仍使用冻结 `configs/defense_mvp/pilot.yaml`；未改源码、算法或真实数据；synthetic 分数仅用于临时测试目录。
- 结果：测试代码已写入，尚待执行验证。新增覆盖不追求改变真实选择或减少 fallback。
- 产物：`tests/defense_mvp/test_cpu_metrics.py`、`test_design_selection.py`、`test_archive.py`。
- 下一步：执行 Defense 全套定向测试，完成 D2 运行文档与最终回归记录。

## Defense MVP D2 实现文档与交接接口

- 时间：2026-09-03 09:42 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-implementation-docs-v01`。
- 行动：更新施工方案至 v1.1-d2；新增 D2_IMPLEMENTATION_RECEIPT，记录真实计数、冻结 SHA、算法精确定义、复跑命令与 D3 输入边界。
- 关键说明：DAVIS 非零索引 mask、local 前景而非子部位 mask、无运动补偿、MP4 checksum 与浏览器播放验证的区别、perf_counter 计时语义；明确 10 automatic ties、32 实际观看项、26 个 N=2 fallback。
- 结果：文档与现有实现/真实回执对齐；原始施工题目、7+3、42×2、人评及冻结协议未变。将未实现的 D3–D6 CLI 与现有命令分开标注。
- 产物：`docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`、`docs/defense_mvp/D2_IMPLEMENTATION_RECEIPT.md`。
- 下一步：等待回归结果；复核输入和产物 checksum；执行发布审计。

## Defense MVP 文档完成后的 whitespace 检查

- 时间：2026-09-03 09:43:09 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d2-resume-whitespace-v01`。
- 行动/命令：`git diff --check`。
- 结果：退出码 0，无 whitespace 错误；仅现有 Git autocrlf 的 LF/CRLF 提示，未运行格式重写。
- 产物：当前 Defense 代码/配置/测试/文档工作树；未暂存媒体。
- 下一步：只读验证 raw package、外层 tar/sidecar 与全部 D2 输出清单。

## Defense MVP 外层传输与 D2 产物最终 checksum 审计

- 时间：2026-09-03 09:44:06 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-final-artifact-checksums-v01`。
- 行动：PowerShell Get-FileHash 与固定 tar/sidecar SHA 比对；逐行验证 ingest、metrics、metrics-replay-v01/v02、design、selection、selection-replay-v01 的 SHA256SUMS，同时核对清单覆盖全部目录文件。
- 结果：tar `0aa0bd951f4609ef779013d78e424fa373201823a8e16e29cbdd070f3a66abdb`、sidecar `5155e42e63ffde4fb079c8bef6897e9a0f834db16cd14d35b4c79687d8e034cd` 均不变；7 个目录共 29 个产物文件全部通过，无额外/缺失文件。
- 产物：既有原始传输文件、`artifacts/defense_mvp/DEFENSE-MVP-v01/`；只读检查，没有覆盖产物。
- 下一步：记录 raw package verify-delivery 与测试结果，执行 CLI/compile 与 staged 发布审计。

## Defense MVP 真实 raw 包最终只读复验

- 时间：2026-09-03 09:44 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-final-raw-verification-v01`。
- 命令：`uv run defense verify-delivery --delivery data/raw/defense_mvp/e0-delivery-v01 --compat-profile server-agent-20260902-v01`。
- 结果：退出码 0，status=passed；1264 SHA 行，唯一偏差仍为已固定的 verification 控制文件，全部媒体、原始记录和 manifest 身份通过。10/50/60/160/160/800 数量无漂移；warnings=[]，missing_optional_artifacts=[]。
- 产物：只读核对 `data/raw/defense_mvp/e0-delivery-v01/`；未改 tar、sidecar、raw 或任何已生成输出。
- 下一步：全仓回归已输出 130 passed，等待进程清理退出；Defense 新增验收测试仍在运行，随后记录最终退出状态。

## Defense MVP 最终 Defense 定向回归

- 时间：2026-09-03 09:45:03 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-final-defense-tests-v01`。
- 命令：`uv run pytest tests/defense_mvp -o addopts='' -q`。
- 结果：39 passed in 281.32s，最终退出码 0；包括恢复后新增的 12 项验收覆盖。无失败或 warning；没有运行真实 GPU/model。
- 产物：`tests/defense_mvp/`；临时 synthetic 测试数据未进入真实实验目录。
- 下一步：等待全仓回归清理退出；完成 CLI smoke 与发布审计。

## Defense MVP 最终 compileall

- 时间：2026-09-03 09:45:03 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d2-final-compileall-v01`。
- 命令：`uv run python -m compileall -q src tests`。
- 结果：退出码 0，源码和最终测试全部通过语法编译。
- 产物：src/tests 的本地忽略缓存；无 tracked 编译产物。
- 下一步：CLI smoke、Git remote 状态与 staged allowlist 审计。

## Defense MVP 最终全仓回归

- 完成确认时间：2026-09-03 09:45:57 +08:00；环境：本地 Windows，CPU-only。
- 步骤 ID：`DEFENSE-MVP-d2-final-repository-tests-v01`。
- 命令：`uv run pytest -o addopts='' -q`（session 43247）。
- 结果：130 passed in 437.91s，清理结束后进程退出码 0，无失败。该运行启动时收集的是 130 项；其间仅新增 12 项测试与文档，未改产品源码。最终 Defense 全套 39 项另行全部通过，因此旧全仓覆盖与新增验收均已验证，不将两次数目简单相加为独立用例数。
- 产物：全仓 tests；未修改 E0/E1/E2 实现与协议。
- 下一步：确认最终 collection 数与 Git 发布范围。

## Defense MVP 最终 CLI smoke

- 时间：2026-09-03 09:45:44 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d2-final-cli-smoke-v01`。
- 命令：`uv run defense version`、`validate-config`，以及 verify-delivery/extract-delivery/ingest/score/design/select 六个命令的 `--help`。
- 结果：全部退出码 0；版本 0.1.0，配置 valid=true，10 samples、50 candidates、35/15、42 comparisons。
- 产物：现有 `defense` CLI；未执行新评分或生成覆盖目录。
- 下一步：发布前 staged path/whitespace 检查。

## Defense MVP Git 远端与作用域预检

- 时间：2026-09-03 09:46 +08:00；环境：本地 Windows 与 GitHub origin，仅 Git 操作。
- 步骤 ID：`DEFENSE-MVP-d2-publication-preflight-v01`。
- 行动：检查 remote、branch、最近提交、diff/ignore 规则；执行 `git fetch origin`。
- 结果：origin 为既有 FAVOR-Edit 仓库，当前 main/HEAD 为 c381cc7；fetch 退出码 0。raw/artifacts 仍忽略；tar/sidecar 保持未跟踪，必须显式排除。仓库无 .gitattributes，可选读取使该只读检查组合命令返回 1；不是测试失败，未创建或改动该文件。
- 产物：本地 Git refs；所有开发改动仍未提交，历史 D1 最终推送 DEVLOG 回执已保留。
- 下一步：确认 main 与最新 origin/main 一致，精确暂存 Defense allowlist 并审计后提交。

## Defense MVP 最终 collection 与发布基线

- 时间：2026-09-03 09:46:39 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d2-final-collection-baseline-v01`。
- 命令：`git rev-parse HEAD origin/main`；`uv run pytest --collect-only -o addopts='' -q`。
- 结果：最终 142 tests collected in 1.05s，退出码 0；HEAD 与 fetch 后 origin/main 均为 `c381cc7d1fac268c9df12976b879de1e2451314a`。已通过的全仓 130 项与最终 Defense 39 项联合覆盖这 142 项。
- 产物：最终测试集合与 Git 基线，无新实验输出。
- 下一步：精确暂存 16 个 Defense 代码/配置/测试/文档文件（含 DEVLOG），执行 staged guard。

## Defense MVP D2 staged 发布审计

- 时间：2026-09-03 09:47:20 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d2-staged-audit-v01`。
- 行动：使用显式 16 路径 allowlist 执行 git add；将 staged 路径集合与 allowlist 精确比对；检查禁止数据路径/媒体后缀、10 MiB 上限、二进制 numstat 和 `git diff --cached --check`。
- 结果：16/16 路径匹配、0 binary、0 media、无超大文件，staged whitespace 通过。范围只含 DEVLOG、Defense 配置、8 个 Defense 模块、4 个 Defense 测试文件、2 个 Defense 文档。tar 与 sidecar 仍未跟踪未暂存；E0/E1/E2 无修改。
- 产物：Git index；保留所有真实实验、复跑及失败诊断目录。
- 下一步：将本审计记录重新暂存，创建 D2 审计提交，然后普通 push origin main。

## Defense MVP D2 审计提交

- 时间：2026-09-03 09:47:44 +08:00；环境：本地 Windows，main。
- 步骤 ID：`DEFENSE-MVP-d2-commit-v01`。
- 命令：`git commit -m "Add audited Defense MVP CPU scoring and selection"`。
- 结果：退出码 0，提交 `94a67799a31fa5c9eb0753de0a9869be2b1d1222`，16 文件；功能、配置、测试、协议实现回执及本次施工 DEVLOG 入库。未包含 tar/sidecar 或实验媒体。
- 产物：本地 Git commit 94a6779；原始与已验收输出不变。
- 下一步：普通 push 到 origin/main，成功后另建 DEVLOG-only 发布回执提交。

## Defense MVP D2 功能提交普通推送

- 时间：2026-09-03 09:48:03 +08:00；环境：本地 Windows → GitHub origin/main。
- 步骤 ID：`DEFENSE-MVP-d2-push-v01`。
- 命令：`git push origin main`；`git rev-parse HEAD origin/main`。
- 结果：普通推送成功，`c381cc7..94a6779 main -> main`；HEAD 与 origin/main 均为 `94a67799a31fa5c9eb0753de0a9869be2b1d1222`。未 force-push，没有远程服务器操作。
- 产物：远端 D2 功能审计提交 94a6779；数据包和全部实验媒体只保留本地。
- 下一步：仅提交本地提交/推送回执的 DEVLOG 增量，再普通推送；最终该推送回执允许作为唯一未提交 tracked 修改保留。

## Defense MVP D2 发布回执提交

- 时间：2026-09-03 09:48:20 +08:00；环境：本地 Windows，main。
- 步骤 ID：`DEFENSE-MVP-d2-publication-receipt-commit-v01`。
- 行动：精确暂存 DEVLOG.md，确认 staged 仅 1 路径且 whitespace 通过；执行 `git commit -m "Record Defense MVP D2 publication"`。
- 结果：退出码 0，提交 `d5ae95e5f35320ad3d749b637db63197c77a519e`，只含 D2 功能提交与推送回执，没有新增功能/实验变更。
- 产物：本地 Git commit d5ae95e；本条及随后的 final push 回执按既定避免无限递归规则留在本地 DEVLOG。
- 下一步：普通推送 d5ae95e，核对远端/本地身份和最终工作树。

## Defense MVP D2 最终推送与交付状态（本地回执）

- 时间：2026-09-03 09:48:39 +08:00；环境：本地 Windows → GitHub origin/main。
- 步骤 ID：`DEFENSE-MVP-d2-final-push-v01`。
- 命令：`git push origin main`；`git rev-parse HEAD origin/main`；`git status --short`；`git diff --check`。
- 结果：普通推送成功，HEAD/origin/main 均为 `d5ae95e5f35320ad3d749b637db63197c77a519e`；whitespace 检查通过。工作树唯一 tracked 修改是 DEVLOG 的本地最终发布回执；原始 tar 和 sidecar 两项继续未跟踪，未纳入提交。
- 交付：D2 功能提交 `94a6779` 与发布回执提交 `d5ae95e` 已在 main；35 定量/15 定性、315 选择、42 比较均已真实运行并校验。最终源码全仓 130 项通过、最终 Defense 39 项通过，联合覆盖最终 collection 142 项；原始传输与媒体身份不变。
- 产物：`docs/defense_mvp/D2_IMPLEMENTATION_RECEIPT.md`、更新后的施工方案、既有 raw/ingest/metrics/design/selection 目录；没有正式人评记录或人评结论。
- 下一步：D3 本地双人盲评界面，先做匿名化播放、两人独立会话、断点保存、方向映射与 42 项 coverage 验收，再开始正式人评。无需继续索取服务器媒体。
- 本地回执说明：为避免发布回执无限递归，本条及上条不再立即建立第三个 DEVLOG-only 提交；下个正常施工提交可一并纳入。

## Defense MVP D3 新对话施工提示词

- 时间：2026-09-03 10:29 +08:00；环境：本地 Windows `D:\lab idea`。
- 步骤 ID：`DEFENSE-MVP-d3-agent-handoff-prompt-v01`。
- 行动：按用户“在新对话详细施工 D3”的要求，只读核对 main/工作树、selection-summary、pilot/comparisons/selection-lock SHA；使用 OpenAI Docs 提示词指导，以目标、必要上下文、约束、交付和验收组织完整新对话交接文档。
- 关键配置：基线 HEAD/origin/main 仍为 `d5ae95e5f35320ad3d749b637db63197c77a519e`；comparisons SHA `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb`、selection-lock SHA `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2`、pilot SHA `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` 均与 D2 一致。
- 结果：新增完整施工提示词，补齐聊天中 D3 方案、匿名化泄漏点、11/11+5/5 方向平衡、同机隔离、持久化/恢复、64 真人回答与 10 共享自动平局的覆盖语义、隔离练习、发布和停止点。本轮没有实现 D3、启动服务、写正式答案、修改冻结配置或提交/推送。
- 产物：`docs/defense_mvp/D3_IMPLEMENTATION_AGENT_PROMPT.md`；用户将在新对话显式要求读取执行。本文档是施工输入，不代表 D3 已经实现或正式人评协议已落地冻结。
- 下一步：检查提示词文档、引用路径和工作树范围；提供可直接复制的新对话启动词。

## Defense MVP D3 交接文档检查

- 时间：2026-09-03 10:33:05 +08:00；环境：本地 Windows。
- 步骤 ID：`DEFENSE-MVP-d3-agent-handoff-check-v01`。
- 行动：PowerShell 检查提示词尾部空白、14 个必需本地引用路径、tracked 修改范围，并执行 `git diff --check`。
- 结果：182 行文档，无尾部空白；14 个输入路径均存在；检查退出码 0。tracked 修改仅 DEVLOG，新提示词未跟踪；功能代码、D2 冻结输入未修改。未运行开发测试，因为本轮仅交接文档，不宣称新功能通过验收。
- 产物：`D:\lab idea\docs\defense_mvp\D3_IMPLEMENTATION_AGENT_PROMPT.md`。
- 下一步：用户在同一本地项目的新对话中粘贴启动词，承接 agent 先完整阅读本文再进入 D3 施工。


## Defense MVP D3 现场核对与施工方案

- 时间：2026-09-03T02:38:08.980Z；环境：本地 Windows CPU-only。
- 步骤 ID：D3.0-audit-plan。
- 行动：完整阅读交接指令、AGENTS、总方案、D2 回执、必要 DEVLOG/源码/测试；核对 git status/branch/HEAD/origin/main、四项输入 SHA，写详细施工方案。
- 结果：基线 d5ae95e 与快照一致，无重叠冲突；pilot/ingest/comparisons/selection-lock 身份一致。用户文本路径不存在，rg 找到实际 docs/defense_mvp/D3_IMPLEMENTATION_AGENT_PROMPT.md。保留既有改动；未重跑 D2，未启动正式会话。
- 产物：docs/defense_mvp/D3_CONSTRUCTION_PLAN.md。协议细化固定 confidence 编码、分目的哈希、内核单写锁、不可变逐题记录、草稿 CAS、包与导出身份链；研究边界不变。
- 下一步：D3.1 实现并验证关联输入链、严格模型和匿名包。


## D3.1 输入门禁与匿名包实现

- 时间：2026-09-03T02:42:06.910Z；环境：本地 Windows CPU-only；步骤 ID：D3.1-code。
- 行动：新增独立 annotation-v1 配置、严格 comparison/answer/session/coverage 模型、D2 关联清单和跨锁校验、60 视频 SHA 检查、42 比较角色矩阵、确定性方向/题序、staging/no-replace 包与环境回执。
- 结果：实现已落盘待测试；formal 绑定四项已验收 SHA，practice 独立标记；未重新运行 D2 或创建正式回答。
- 产物：src/defense_mvp/annotation_models.py、annotation_bundle.py、configs/defense_mvp/annotation-v1.yaml。
- 下一步：D3.1 定向验证真实只读输入链与映射，补充验收测试。


## D3.1 真实输入链与方向只读验收

- 时间：2026-09-03T02:42:30.744Z；环境：本地 Windows CPU-only；步骤 ID：D3.1-real-validation。
- 命令：uv run python 调用 validate_inputs(formal) 与 mapping_for(annotator-a/b)，输入为既有 D2 selection/ingest/metrics/design 与 pilot。
- 结果：退出码 0，4.69 秒；42 比较、60 视频、20 个输入文件均通过；两人各 11A/11B + 5A/5B。未重建 D2 或写正式人答。
- 产物：命令输出中的比较/视频/输入计数和各类别方向；真实媒体只读。
- 下一步：按验证结果推进存储层与测试。


## D3.2 单写与恢复存储实现

- 时间：2026-09-03T02:45:00.969Z；环境：本地 Windows CPU-only；步骤 ID：D3.2-code。
- 行动：新增内核文件锁、显式 resume/身份目录、不可变原子逐题记录、草稿 CAS、请求幂等/冲突、时间与 canonical 验证；运行回执记录遗留 pending 文件。补强 load_bundle 重新核对 D2 输入关系，拒绝仅重算包内 checksum 的映射/媒体关系漂移。
- 结果：实现已写入待故障测试；正式目录尚未创建。只允许草稿原子替换，正式记录不覆盖，未知锁/损坏记录不静默处理。
- 产物：src/defense_mvp/annotation_store.py、annotation_bundle.py。
- 下一步：实现 HTTP/播放器接口，再以隔离 fixture 联合验收存储与路由。


## D3.3 匿名本地服务与播放器实现

- 时间：2026-09-03T02:49:06.409Z；环境：本地 Windows CPU-only；步骤 ID：D3.3-code。
- 行动：新增 loopback HTTP、一次性入口/HttpOnly cookie/CSRF/Origin、严格路由与当前题媒体授权；实现完整/单段 Range、匿名固定错误、CSP；新增三路播放/暂停/重播/拖动、五字段主动选择、confidence、草稿保存与确认重试界面。
- 结果：源码完成待浏览器与攻击面验收；方法/比较 ID/原始路径保留服务端。播放状态不是精确劳动成本，正式人答未产生。
- 产物：src/defense_mvp/annotation_server.py、annotation_ui.html。
- 下一步：D3.4 导出、coverage、CLI 与隔离故障测试。


## D3.4 导出与覆盖接口实现

- 时间：2026-09-03T02:50:56.455Z；环境：本地 Windows CPU-only；步骤 ID：D3.4-code。
- 行动：实现持锁验证的 no-replace JSONL/事实清单/coverage/自动平局导出、单人/双人 verifier 和四个 CLI；明确 incomplete/complete、single/dual、practice/formal。
- 结果：不统计偏好；自动平局保持共享系统来源，无 confidence/人工时间。正式包可以只读验证但不会创建会话或答案。待联合验收。
- 产物：src/defense_mvp/annotation_export.py、cli.py。
- 下一步：构建隔离 tiny fixtures 与全矩阵验收测试，修复实测缺陷。


## D3 里程碑验收测试实现

- 时间：2026-09-03T02:55:10.633Z；环境：本地 Windows CPU-only；步骤 ID：D3-tests-code。
- 行动：新增独立 test_blind_annotation.py，覆盖 D2 跨锁/重算清单后的关系篡改、映射、严格字段、草稿/幂等/故障/pending、双进程与退出恢复、匿名 HTTP/Range/CSRF、练习双人导出与伪造 coverage 拒绝。
- 配置：使用已有 handoff_factory 的 tiny fake 字节 + synthetic metrics；全部生成答案为 practice，不作为真实播放证据。
- 结果：测试已写入，下一步执行；真实输入与 D2 均未改动。
- 产物：tests/defense_mvp/test_blind_annotation.py。
- 下一步：运行 D3 定向测试，逐次记录失败及修复。


## D3 首次浏览器练习包准备

- 时间：2026-09-03T02:56:37.161Z；环境：本地 Windows CPU-only；步骤 ID：D3.5-browser-prepare-initial。
- 命令：uv run defense prepare-annotation --selection artifacts/defense_mvp/DEFENSE-MVP-v01/selection --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-initial/practice-bundle --mode practice。
- 结果：退出码 0，2.04 秒，42/10/32；bundle SHA e4fb830588ec3c654f0e46a7ab6dad3bf286a7ccb2570fd67d077fea514a2468。只读复用真实媒体，practice 标签明确；正式答案 0。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-initial/practice-bundle，含源码/依赖回执；浏览器连接已建立。
- 下一步：启动隔离练习服务，核对真实播放与提交 UI；等待定向测试退出。


## D3 练习服务首次启动

- 时间：2026-09-03T02:57:01.881Z；环境：本地 Windows CPU-only；步骤 ID：D3.5-browser-start-initial。
- 命令：uv run defense annotate --bundle artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-initial/practice-bundle --annotator-id annotator-a --output artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-initial/annotator-a --port 8765。
- 结果：练习服务成功监听 127.0.0.1:8765，终端 session 3193；运行中，令牌仅终端显示，不入 Git。已创建 practice 会话，未启动 formal。
- 产物：qa-initial/annotator-a/session.json 与 runs 回执；无正式记录。
- 下一步：浏览器播放验收。


## D3 首轮定向验收及故障定位

- 时间：2026-09-03T02:57:49.293Z；环境：本地 Windows CPU-only；步骤 ID：D3-tests-v01。
- 命令：uv run pytest tests/defense_mvp/test_blind_annotation.py -o addopts='' -q（session 57300）。
- 结果：70 passed、1 failed，57.79 秒，退出码 1。Windows 对已锁字节的 read 提前抛 PermissionError，未转换为明确 Conflict；互斥实际生效，但错误分类不符合接口。其余输入、存储、HTTP、导出测试通过。
- 产物：tests/defense_mvp/test_blind_annotation.py 的失败堆栈；pytest-159 tiny practice 诊断。初始浏览器页面已显示 1/32、未预填、提交禁用。
- 下一步：修复锁获取顺序并强化不确定持久化后的幂等恢复，然后复验。


## D3 锁与提交恢复修复

- 时间：2026-09-03T02:57:49.344Z；环境：本地 Windows CPU-only；步骤 ID：D3-storage-fix-v02。
- 行动：内核锁先获取再读取 sentinel，冲突统一返回 Conflict；已提交 request_id 在重启后也可核对相同屏幕内容幂等返回；对 rename 成功但回执失败的情况重新校验不可变事实，不重复写入。
- 结果：修复落盘并增加对应断电确认丢失测试；未改变判断协议或任何真实输入。
- 产物：annotation_store.py、annotation_export.py、test_blind_annotation.py。
- 下一步：定向复验锁和持久化；继续浏览器真实播放。


## D3 首次真实浏览器播放诊断

- 时间：2026-09-03T02:58:44.373Z；环境：Codex In-app Browser + 本地 practice 服务；步骤 ID：D3-browser-play-v01。
- 行动：打开当前会话入口，检查初始 1/32、无预填/禁用提交，点击同步播放并读取 video DOM 状态与控制台。
- 结果：未通过播放验收。source readyState=4/duration=2，A/B readyState=0；页面显示媒体播放失败且提交仍禁用，控制台无异常。尚未保存任何练习正式确认记录，formal 为 0。
- 产物：qa-initial/annotator-a、浏览器 DOM/媒体诊断输出。
- 下一步：检查真实 MP4 编码及服务路由，定位加载失败原因；禁止把该结果算作播放通过。


## D3 真实 MP4 编码只读诊断

- 时间：2026-09-03T02:59:35.221Z；环境：本地 Windows CPU-only，既有 imageio-ffmpeg 7.1；步骤 ID：D3-media-codec-diagnosis。
- 命令：对首题 source/X/Y 执行 ffmpeg -hide_banner -i <原媒体> -f null -（只读解码）。
- 结果：退出码 0，3.45 秒；三路均可解码为 16 帧/512×512/8fps/2秒/yuv420p。source 编码 H.264；两候选为 MPEG-4 Part 2 (mp4v)，当前浏览器不能播放，非 checksum 漂移。静态 HTTP 测试无法发现此兼容性问题。
- 产物：终端 ffmpeg 诊断，既有原始媒体未变。
- 下一步：增加独立无损浏览器展示副本及像素/时间/原始 SHA 映射证明；不改 D2、原始 MP4 或比较计划。


## D3 定向复验 v02

- 时间：2026-09-03T03:00:17.041Z；环境：本地 Windows CPU-only；步骤 ID：D3-tests-v02。
- 行动/命令：uv run pytest tests/defense_mvp/test_blind_annotation.py -o addopts='' -q（session 92469）。
- 结果：72 passed in 67.42s，退出码 0，锁冲突/进程退出/不确定确认恢复均通过。
- 产物：pytest-160 tiny practice 与新增 72 项测试。
- 下一步：冻结无损展示兼容细节。


## D3 首次练习服务退出

- 时间：2026-09-03T03:00:17.061Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-stop-initial。
- 行动/命令：向 terminal session 3193 发送 Ctrl+C，结束 qa-initial 练习服务。
- 结果：进程已退出（控制中断退出码 1）；0 条确认回答；原会话/失败证据保留。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-initial/。
- 下一步：以新目录准备兼容浏览器的无损展示包。


## D3 无损展示工程决策

- 时间：2026-09-03T03:00:17.093Z；环境：本地 Windows CPU-only；步骤 ID：D3-presentation-decision。
- 行动：在施工方案固定 lossless-vp9-yuv420p-v1；对全部参与比较的 source/candidate 同规则转换，仅新包内 presentation 目录写入；原始 SHA 仍控制自动平局，记录增加展示 SHA 和等价证明。
- 配置：VP9 lossless、yuv420p、无 resize/补帧/裁剪，验证 RGB24 逐帧 hash、尺寸、帧数与时间；fake-native 仅隔离 practice 可用。
- 结果：属于浏览器兼容性工程修复；不改 sealed E0/D2 或比较与判断协议。若无法证明无损/时序一致则 prepare 失败，不用有损副本替代。
- 产物：docs/defense_mvp/D3_CONSTRUCTION_PLAN.md 补充。
- 下一步：实现展示副本身份链并用真实浏览器再验收。


## D3 无损展示实现与身份链

- 时间：2026-09-03T03:02:33.957Z；环境：本地 Windows CPU-only；步骤 ID：D3-presentation-code。
- 行动：新增 annotation_media，生成 VP9 lossless 私有展示媒体；验证原/展示 RGB24 帧 hash 与 8fps 时间完全一致；包、逐题记录与 verifier 同时绑定原媒体/展示媒体。四个 CLI 之一新增 practice-only fixture-native-media。
- 结果：原始 MP4 与自动平局规则不变；正式准备不能跳过展示等价门禁。尚待真实转换和浏览器验证。
- 产物：annotation_media.py、bundle/store/models/server/cli、annotation-v1.yaml 与对应 tiny fixture 调整。
- 下一步：在新 qa-v02 目录执行真实无损展示准备；每个失败保留诊断。


## D3 无损展示真实准备 v02

- 时间：2026-09-03T03:04:11.844Z；环境：本地 Windows CPU-only；步骤 ID：D3-presentation-prepare-v02。
- 命令：uv run defense prepare-annotation --selection artifacts/defense_mvp/DEFENSE-MVP-v01/selection --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-v02/practice-bundle --mode practice。
- 结果：退出码 0，转换/逐帧验证 44.60 秒；39 个引用视频共 624 帧 RGB24 SHA、512×512、16帧/8fps 时间完全相等。42/10/32 不变，bundle SHA f72a111869cb449c88b9b121dd1a7b12f565fcf46fde68a075887d0937fe3958。
- 产物：qa-v02/practice-bundle/presentation/、presentation-proof.json 与完整 SHA 清单；原始视频只读，正式人答 0。
- 下一步：启动新练习会话并验收浏览器播放、拖动和表单。


## D3-browser-start-v02

- 时间：2026-09-03T03:04:52.424Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-start-v02。
- 行动/命令：启动 qa-v02/practice-bundle 的 annotator-a，output qa-v02/annotator-a，port 8765。
- 结果：练习服务就绪，terminal session 71342，127.0.0.1；未启动 formal。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-v02/ 与 tests/defense_mvp/test_blind_annotation.py。
- 下一步：真实浏览器操作。


## D3-tests-v03

- 时间：2026-09-03T03:04:52.445Z；环境：本地 Windows CPU-only；步骤 ID：D3-tests-v03。
- 行动/命令：uv run pytest tests/defense_mvp/test_blind_annotation.py -o addopts='' -q（session 88657）。
- 结果：72 passed in 58.67s，退出码 0；展示原始/副本身份字段纳入存储、导出与 verifier 后现有用例全部通过。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-v02/ 与 tests/defense_mvp/test_blind_annotation.py。
- 下一步：补充展示/媒体失败专项及浏览器验收。


## D3 真实浏览器播放与同步通过

- 时间：2026-09-03T03:06:08.265Z；环境：Codex In-app Browser + qa-v02 practice，CPU-only；步骤 ID：D3-browser-play-v02。
- 行动：UI 同步播放、从头重播、全部暂停、统一滑条 Home/ArrowRight；读取实际 video 元素状态并保存整页截图。
- 结果：三路 readyState=4、duration=2 秒、无媒体错误；播放时 source/A/B 时间 0.253670/0.253515/0.253457 秒；暂停全部 paused=true；统一 seek 后三路均 0.01 秒。界面明确近似同步，初始表单未预填，未完整填答时提交禁用。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/output/playwright/01-playback.png；仅 practice 会话。
- 下一步：草稿刷新恢复、注入文本安全、确认提交与错误媒体门禁浏览器验证。


## D3 浏览器草稿恢复与表单门禁通过

- 时间：2026-09-03T03:07:02.646Z；环境：本地浏览器 practice；步骤 ID：D3-browser-draft-v02。
- 行动：仅在 qa-v02 练习中填入覆盖 A/B/tie/uncertain 的测试值、confidence=.5 和 script 字面量备注；确认草稿保存，刷新并检查 DOM。
- 结果：五字段与备注按草稿恢复、未执行 script、无弹窗；刷新后必须重新播放才解锁提交；尚无确认记录。练习值明确非研究。
- 产物：output/playwright/02-draft-restored.png 与 qa-v02/annotator-a/drafts；正式答案仍 0。
- 下一步：练习确认提交、刷新只读恢复与下一题初始状态验收。


## D3 浏览器原生确认弹窗诊断

- 时间：2026-09-03T03:08:43.375Z；环境：Codex In-app Browser、本地 practice；步骤 ID：D3-browser-confirm-v01。
- 行动：点击练习提交按钮，调用文档支持的 getJsDialog，并读取 browser-troubleshooting。
- 结果：Input.dispatchMouseEvent / Emulation.setFocusEmulationEnabled 超时，无法控制原生 confirm；只读检查 records 为 0。没有盲目重复提交，当前不算提交流程通过。
- 产物：qa-v02 练习草稿保留；正式人答仍 0。
- 下一步：改用页面内二次确认并关闭旧页/服务，显式 resume 再验收。


## D3 页面内二次确认修复

- 时间：2026-09-03T03:08:43.401Z；环境：本地 Windows；步骤 ID：D3-ui-confirm-fix。
- 行动：将原生 confirm 替换成页面内“确认保存本题/返回修改”二次操作；保留保存前冻结表单、成功后只读、失败原请求重试。
- 结果：UI 变更已写入；不改变答案字段/身份/协议或已准备媒体。
- 产物：src/defense_mvp/annotation_ui.html。
- 下一步：重启练习服务，验证草稿恢复与两次确认。


## D3 qa-v02 练习服务中断回执

- 时间：2026-09-03T03:09:26.967Z；环境：本地 Windows / In-app Browser；步骤 ID：D3-browser-stop-v02。
- 行动：尝试按浏览器文档关闭被 confirm 阻塞的标签页；向 terminal session 71342 发送 Ctrl+C。
- 结果：服务已停止，控制中断退出码 1；浏览器 close 仍受 Emulation.setFocusEmulationEnabled 超时阻塞，尚未确认旧页关闭。草稿保留，确认记录仍 0。
- 产物：qa-v02/annotator-a；该会话后续只能显式 resume。
- 下一步：创建新标签页恢复验证；旧令牌随新服务作废。


## D3 显式恢复练习服务

- 时间：2026-09-03T03:09:57.762Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-resume-v03。
- 命令：uv run defense annotate --bundle artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-v02/practice-bundle --annotator-id annotator-a --output artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-v02/annotator-a --resume --port 8765。
- 结果：校验既有草稿后成功启动，terminal session 57295；新令牌，浏览器新标签页创建成功；没有绕过旧页确认或改写记录。
- 产物：qa-v02/annotator-a/runs 新回执。
- 下一步：新页面内确认与恢复验收。


## D3 页面确认、持久化与下一题通过

- 时间：2026-09-03T03:10:51.573Z；环境：真实浏览器 practice；步骤 ID：D3-browser-confirm-v03。
- 行动：重启 --resume 后确认草稿，播放三路；打开页面内确认、返回修改、再确认保存。
- 结果：成功落盘后进度 1/32→2/32；下一题五字段、confidence、notes 均无预填，提交禁用。仅新增 1 条 practice 工程记录，formal 为 0。
- 产物：qa-v02/annotator-a/records/0001.json，原草稿保留；源码为页面内确认版本。
- 下一步：按固定工程测试值走完隔离练习双人覆盖，同时对每题检查真实展示媒体可播放；不解释测试值为偏好。


## D3-browser-practice-a-02-09

- 时间：2026-09-03T03:12:11.170Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-a-02-09。
- 行动/命令：浏览器逐题播放并提交固定非研究测试值，第 2–9 题。
- 结果：8/8 三路 readyState=4、duration=2、无解码错误；a 已保存9条 practice；formal仍0。
- 产物：output/playwright/a-progress.json、qa-v02/annotator-a/records。
- 下一步：继续同一隔离流程。


## D3-browser-practice-a-10-21

- 时间：2026-09-03T03:12:53.287Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-a-10-21。
- 行动/命令：浏览器逐题播放并提交固定非研究测试值，第10–21题。
- 结果：12/12 播放/保存成功，a累计21条practice，formal0。
- 产物：output/playwright/a-progress.json、qa-v02/annotator-a。
- 下一步：完成a练习并封存导出。


## D3-browser-practice-a-complete

- 时间：2026-09-03T03:14:46.709Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-a-complete。
- 行动/命令：第22–32题逐题播放/保存，刷新完成页，关闭新标签页；Ctrl+C退出session57295。
- 结果：a为32条practice，所有三路视频通过；刷新保持完成，无重答入口。服务已中断退出码1；正式答案0。
- 产物：output/playwright/03-a-complete.png、a-progress.json、qa-v02/annotator-a。
- 下一步：补强同浏览器旧页的启动隔离，然后b流程复验。


## D3-session-route-hardening

- 时间：2026-09-03T03:14:46.761Z；环境：本地 Windows CPU-only；步骤 ID：D3-session-route-hardening。
- 行动/命令：为每次启动增加随机URL前缀和cookie Path隔离，旧页即使共享浏览器新cookie也不能访问新会话；修复复用request_id跨题冲突。增加旧页、原媒体漂移、practice-only展示和真实可播放tiny无损转换测试。
- 结果：实现与测试落盘；这是同机隔离补强，协议/真实输入不变。
- 产物：annotation_server.py、annotation_store.py、annotation_ui.html、test_blind_annotation.py。
- 下一步：运行D3定向测试并用b完整流程验收最终路由。


## D3-browser-start-b

- 时间：2026-09-03T03:15:17.002Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-start-b。
- 行动/命令：a 服务退出后启动 qa-v02/annotator-b（同一 practice-bundle，127.0.0.1:8765）。
- 结果：新身份、新会话、新cookie Path及启动前缀；terminal session82202运行。a已32条practice，b0；formal0。
- 产物：qa-v02/annotator-b/session.json、runs。
- 下一步：验收b未看到a答案并走完整套流程。


## D3-browser-b-navigation-diagnostic

- 时间：2026-09-03T03:16:14.419Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-navigation-diagnostic。
- 行动/命令：打开新b会话入口，检查URL/DOM/控制台。
- 结果：浏览器返回net::ERR_BLOCKED_BY_CLIENT，停在about:blank，服务未报错；b未作答。尚不能确定是随机入口还是/s/路径触发客户端过滤。
- 产物：qa-v02/annotator-b，浏览器诊断输出。
- 下一步：改用明确/review/启动路径后重新连接；保持所有身份校验。


## D3-browser-prefix-compatibility

- 时间：2026-09-03T03:16:14.445Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-prefix-compatibility。
- 行动/命令：将启动URL路径从/s/改为/review/，随机前缀与cookie/CSRF/Origin门禁全部保留。
- 结果：仅路由名称变更待浏览器复验；不降低访问控制。
- 产物：annotation_server.py。
- 下一步：重启b练习会话。


## D3-tests-v04

- 时间：2026-09-03T03:16:29.570Z；环境：本地 Windows CPU-only；步骤 ID：D3-tests-v04。
- 行动/命令：uv run pytest tests/defense_mvp/test_blind_annotation.py -o addopts='' -q（session3747）。
- 结果：76 passed in61.31s，退出码0；包括旧页新cookie拒绝、跨题request冲突、tiny MPEG4→VP9逐帧等价。其后仅/review/路由字面量改变，最终回归仍待跑。
- 产物：tests/defense_mvp/test_blind_annotation.py。
- 下一步：浏览器b复验与最终全仓回归。


## D3-browser-b-stop

- 时间：2026-09-03T03:16:29.587Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-stop。
- 行动/命令：Ctrl+C停止session82202，关闭空白tab4。
- 结果：练习b服务已中断退出码1，确认记录0。
- 产物：qa-v02/annotator-b。
- 下一步：显式resume新入口。


## D3-browser-b-resume

- 时间：2026-09-03T03:16:48.326Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-resume。
- 行动/命令：以--resume重启qa-v02/annotator-b，port8765，使用/review/随机路径。
- 结果：session2661运行，b确认记录0，正式会话未创建。
- 产物：qa-v02/annotator-b/runs。
- 下一步：打开新入口并验证表单。


## D3-browser-b-navigation-v02

- 时间：2026-09-03T03:17:22.751Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-navigation-v02。
- 行动/命令：重新打开/review/启动路径的新入口。
- 结果：同样ERR_BLOCKED_BY_CLIENT且页面未载入；此前路径名称假设未获支持。b仍0条，未把导航失败算通过。
- 产物：qa-v02练习诊断；保留两次运行回执。
- 下一步：检查本地HTTP重定向行为，避免继续猜路径。


## D3-browser-redirect-probe

- 时间：2026-09-03T03:18:00.354Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-redirect-probe。
- 行动/命令：用本地http.client只读请求失败入口并只打印状态/Location。
- 结果：403 session_rejected，说明入口已由浏览器消费，阻拦发生在后续重定向/页面载入阶段；未读取浏览器cookie或绕过身份校验。
- 产物：终端诊断。
- 下一步：输出受会话cookie保护的工作页面URL用于定位重定向兼容性。


## D3-browser-redirect-diagnostic-link

- 时间：2026-09-03T03:18:00.379Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-redirect-diagnostic-link。
- 行动/命令：启动日志增加受cookie保护的工作页面URL；入口与页面均只含随机标识。
- 结果：便于定位内置浏览器重定向阻断；未改权限或放宽任何路由。
- 产物：annotation_server.py。
- 下一步：重启练习b并检查入口后页面。


## D3-browser-b-stop-v02

- 时间：2026-09-03T03:18:10.606Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-stop-v02。
- 行动/命令：Ctrl+C退出session2661并关闭空白tab5。
- 结果：服务已停止（中断退出码1），b记录0，旧入口作废。
- 产物：qa-v02/annotator-b。
- 下一步：启动带诊断页面URL的b恢复服务。


## D3-browser-b-resume-v03

- 时间：2026-09-03T03:18:28.367Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-resume-v03。
- 行动/命令：显式resume qa-v02/annotator-b，带随机工作页面诊断URL，port8765。
- 结果：session43066运行；所有历史会话/草稿不变，b正式确认0。
- 产物：qa-v02/annotator-b/runs。
- 下一步：验证入口重定向是否为唯一阻碍。


## D3-cookie-path-collision-diagnosis

- 时间：2026-09-03T03:19:28.303Z；环境：本地 Windows CPU-only；步骤 ID：D3-cookie-path-collision-diagnosis。
- 行动/命令：浏览器对已认证工作URL仍阻拦；在本地用两个同名、不同作用域的假cookie值复现SimpleCookie解析。
- 结果：退出码0，解析保留最后old_root_path；代码存在旧root cookie与新窄Path cookie重名时选错令牌的风险。未读取任何浏览器cookie。
- 产物：终端假cookie解析证据。
- 下一步：每次启动使用独立cookie名称消除歧义，记录匿名HTTP错误码定位剩余问题。


## D3-cookie-name-isolation-fix

- 时间：2026-09-03T03:19:28.331Z；环境：本地 Windows CPU-only；步骤 ID：D3-cookie-name-isolation-fix。
- 行动/命令：每次启动生成独立cookie名称，Path仍限定随机启动前缀；终端仅输出匿名HTTP错误码；测试覆盖与旧root cookie同时存在。
- 结果：实现落盘，全部授权检查保留；无需删除/读取浏览器cookies。
- 产物：annotation_server.py、test_blind_annotation.py。
- 下一步：重启b复验并读取匿名诊断。


## D3-browser-b-stop-v03

- 时间：2026-09-03T03:19:40.339Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-stop-v03。
- 行动/命令：Ctrl+C退出session43066，关闭tab6。
- 结果：练习b仍0条确认记录；服务已中断退出码1。
- 产物：qa-v02/annotator-b。
- 下一步：以独立cookie名称恢复。


## D3-browser-b-resume-v04

- 时间：2026-09-03T03:20:00.124Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-resume-v04。
- 行动/命令：显式resume qa-v02/annotator-b，port8765，独立cookie名称与启动路径。
- 结果：session92546运行；b0条、formal0。
- 产物：qa-v02/annotator-b/runs。
- 下一步：浏览器入口与匿名服务日志核对。


## D3-browser-b-entry-passed

- 时间：2026-09-03T03:20:48.568Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-b-entry-passed。
- 行动/命令：独立cookie名称修复后，用同一浏览器打开新的b入口。
- 结果：成功进入1/32，首题与a不同，所有判断/信心/备注空白；未看到a记录，服务无匿名错误。此前同名cookie冲突已由实测修复。
- 产物：qa-v02/annotator-b与浏览器DOM证据。
- 下一步：完成b练习；冻结源码进行最终定向和全仓回归。


## D3-browser-practice-b-01-12

- 时间：2026-09-03T03:22:01.110Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-b-01-12。
- 行动/命令：浏览器逐题播放/填写固定工程值/二次确认，第1–12题。
- 结果：12/12三路可播放且保存成功，b12条practice，formal0。
- 产物：output/playwright/b-progress.json、qa-v02/annotator-b。
- 下一步：继续b后20题；最终Defense和全仓pytest运行中（3473、44555）。


## D3-browser-practice-b-13-24

- 时间：2026-09-03T03:22:40.987Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-b-13-24。
- 行动/命令：浏览器逐题播放和固定工程值提交，第13–24题。
- 结果：12/12通过，b累计24条practice，formal0。
- 产物：output/playwright/b-progress.json、qa-v02/annotator-b。
- 下一步：完成最后8题。


## D3-browser-practice-b-complete

- 时间：2026-09-03T03:23:22.765Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-practice-b-complete。
- 行动/命令：第25–32题播放/固定工程值确认，刷新完成页，关闭tab并Ctrl+C退出session92546。
- 结果：b32条practice全部可播放与保存；两人合计64条practice。服务退出码1（控制中断），formal仍0。
- 产物：output/playwright/04-b-complete.png、b-progress.json、qa-v02/annotator-b。
- 下一步：no-replace导出双人练习并验证coverage。


## D3-export-practice-a

- 时间：2026-09-03T03:23:36.325Z；环境：本地 Windows CPU-only；步骤 ID：D3-export-practice-a。
- 行动/命令：调用export_annotations，对qa-v02/annotator-a输出新exports/annotator-a-v01。
- 结果：退出码0，3.20秒；practice complete，32条回答+10项共享自动平局。原始逐题记录不变。
- 产物：qa-v02/exports/annotator-a-v01。
- 下一步：导出b。


## D3-export-practice-b

- 时间：2026-09-03T03:23:55.282Z；环境：本地 Windows CPU-only；步骤 ID：D3-export-practice-b。
- 行动/命令：调用export_annotations，对qa-v02/annotator-b输出新exports/annotator-b-v01。
- 结果：退出码0，3.11秒；practice complete，32条回答+10项共享自动平局。
- 产物：qa-v02/exports/annotator-b-v01。
- 下一步：运行双人verifier及formal拒绝检查。


## D3-dual-practice-verification

- 时间：2026-09-03T03:24:12.340Z；环境：本地 Windows CPU-only；步骤 ID：D3-dual-practice-verification。
- 行动/命令：verify_annotations校验两个新导出，并不带allow_practice重试正式门禁。
- 结果：退出码0，3.83秒；dual practice complete，64条练习+10共享自动平局，两个coverage均42；formal模式明确拒绝该包。未计算任何偏好统计。
- 产物：qa-v02/dual-verification.json。
- 下一步：建立不可播放媒体的独立错误fixture并验证禁用提交。


## D3-browser-error-fixture-prepared

- 时间：2026-09-03T03:24:43.189Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-error-fixture-prepared。
- 行动/命令：prepare_annotation以practice+fixture_native_media构建独立qa-media-error包，保留浏览器不支持的原始mp4v作为错误fixture。
- 结果：退出码0，2.29秒；仅错误播放测试，禁止作为formal；原始媒体未修改。
- 产物：qa-media-error/practice-bundle。
- 下一步：填完整练习字段时验证媒体故障仍禁止提交。


## D3-browser-error-fixture-start

- 时间：2026-09-03T03:25:22.398Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-error-fixture-start。
- 行动/命令：启动qa-media-error/annotator-a练习服务，port8765。
- 结果：session10096运行，仅错误fixture；formal包准备进程33931运行但无正式会话。
- 产物：qa-media-error/annotator-a。
- 下一步：真实浏览器填写完整表单并检查解码错误门禁。


## D3-browser-media-error-gate-passed

- 时间：2026-09-03T03:26:04.226Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-media-error-gate-passed。
- 行动/命令：不可播放mp4v练习页中主动填写全部五字段和confidence，点击播放并检查按钮；关闭页面，Ctrl+C退出session10096。
- 结果：页面明确媒体播放失败且submitEnabled=false，不能用uncertain替代失败；未保存确认回答。服务中断退出码1。
- 产物：output/playwright/05-media-error-blocked.png、qa-media-error/annotator-a。
- 下一步：核对正式prepared包与环境证据。


## D3-formal-bundle-prepared

- 时间：2026-09-03T03:26:18.069Z；环境：本地 Windows CPU-only；步骤 ID：D3-formal-bundle-prepared。
- 行动/命令：prepare_annotation(formal)从D2冻结输入生成全新artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-bundle。
- 结果：退出码0；39视频/624帧逐像素与时间等价，转换验证55.07秒；42/10/32，正式答案0。bundle SHA c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6。未运行formal annotate。
- 产物：formal-bundle/prepare-receipt.json、presentation-proof.json、SHA256SUMS。
- 下一步：创建供用户练习的独立新包，最终checksum/CLI/回归。


## D3-documentation-delivery

- 时间：2026-09-03T03:29:40.735Z；环境：本地 Windows CPU-only；步骤 ID：D3-documentation-delivery。
- 行动/命令：新增ANNOTATION_GUIDE、D3_IMPLEMENTATION_RECEIPT；更新总方案已实现CLI/真实32+10覆盖/停止点；施工方案对齐无损展示与最终会话路由。
- 结果：文档落盘，完整操作/退出/恢复/正式a与b/导出命令和局限可审阅。最终回归/发布栏尚待实际结果补齐。
- 产物：docs/defense_mvp/ANNOTATION_GUIDE.md、D3_IMPLEMENTATION_RECEIPT.md、D3_CONSTRUCTION_PLAN.md、docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md。
- 下一步：记录最终回归结果，执行CLI/编译/输入前后校验和发布审计。


## D3-final-defense-regression

- 时间：2026-09-03T03:30:16.828Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-defense-regression。
- 行动/命令：uv run pytest tests/defense_mvp -o addopts='' -q（session3473，最终产品源码）。
- 结果：115 passed in364.72s，退出码0；D2原有39项+D3新76项一次实际运行通过。运行期间未改产品源码，仅完善文档。
- 产物：tests/defense_mvp、pytest输出回执。
- 下一步：等待最终全仓218项并完成静态/CLI审计。


## D3-user-practice-bundle-prepared

- 时间：2026-09-03T03:30:16.848Z；环境：本地 Windows CPU-only；步骤 ID：D3-user-practice-bundle-prepared。
- 行动/命令：prepare_annotation(practice)生成全新DEFENSE-MVP-D3-v01/practice-bundle，默认无损展示。
- 结果：退出码0，42/10/32；SHA80cf70cbefc73815f0cd016db7741a99bf43b858f2fe9ce2b329a8cfd4ec3da9。用户练习会话目录尚不存在，formal0。
- 产物：practice-bundle/prepare-receipt.json、presentation-proof.json、SHA256SUMS。
- 下一步：验证正式/练习最终包与源码、冻结输入前后SHA。


## D3-final-compileall

- 时间：2026-09-03T03:30:37.650Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-compileall。
- 行动/命令：uv run python -m compileall -q src tests。
- 结果：退出码0，1.13秒；最终源码和测试语法编译通过。
- 产物：忽略的Python缓存，未新增tracked二进制。
- 下一步：CLI smoke与最终包/原始身份核对。


## D3-final-cli-smoke

- 时间：2026-09-03T03:31:20.290Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-cli-smoke。
- 行动/命令：CliRunner执行version/validate-config及10个命令--help，并真实调用verify-annotations --bundle formal-bundle。
- 结果：全部退出码0，2.89秒；正式包prepared_bundle/incomplete、exported_answers0、42/10/32，未生成会话。
- 产物：defense CLI及正式bundle。
- 下一步：核对所有原始/展示媒体、最终源码snapshot及正式答案为0。


## D3-final-identity-verification

- 时间：2026-09-03T03:31:47.937Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-identity-verification。
- 行动/命令：load_bundle复验正式/用户练习包及所有输入/展示SHA，比较初始qa-initial原视频inventory、四个D2冻结SHA、当前源码文件hash；扫描D3会话/确认记录。
- 结果：退出码0，3.88秒；60原MP4前后完全一致、39展示引用有效、最终包源码snapshot匹配。formal目录不存在，正式会话0、人答0；64条确认均practice。
- 产物：final-identity-verification.json。
- 下一步：等待全仓结果并审计Git发布范围。


## D3-browser-cleanup-complete

- 时间：2026-09-03T03:32:45.518Z；环境：本地 Windows CPU-only；步骤 ID：D3-browser-cleanup-complete。
- 行动/命令：使用浏览器文档支持的CUA Escape关闭早期原生确认，再关闭tab2。
- 结果：成功清除最后一个遗留练习标签页；所有练习服务已退出，未启动formal。
- 产物：浏览器临时页面清理，无正式数据变更。
- 下一步：最终发布审计。


## D3-final-repository-regression

- 时间：2026-09-03T03:32:45.536Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-repository-regression。
- 行动/命令：uv run pytest -o addopts='' -q（session44555，最终产品源码状态）。
- 结果：218 passed in613.64s，退出码0；本次为一次实际完整218项通过。原E0/E1/E2源码未改。
- 产物：全仓tests输出；此前Defense115项另一次通过。
- 下一步：更新最终回执，审计Git index后发布。


## D3-final-working-tree-whitespace

- 时间：2026-09-03T03:32:45.555Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-working-tree-whitespace。
- 行动/命令：git diff --check、git status --short、git diff --name-only。
- 结果：退出码0，无whitespace错误；已有tracked变更仅DEVLOG/总方案/CLI，新文件均Defense范围；tar/sidecar未跟踪。仅Git autocrlf提示，无格式批量重写。
- 产物：工作树与待发布allowlist。
- 下一步：补齐最终回执并审查暂存内容。


## D3-final-acceptance-receipt

- 时间：2026-09-03T03:32:45.588Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-acceptance-receipt。
- 行动/命令：将115/218实际回归、CLI/编译/身份核对与0正式回答写入D3_IMPLEMENTATION_RECEIPT，施工方案标记D3.1–D3.5通过。
- 结果：D3工程ready，停止于邀请真人前；源代码未变，正式人评与D4未启动。
- 产物：D3_IMPLEMENTATION_RECEIPT.md、D3_CONSTRUCTION_PLAN.md、ANNOTATION_GUIDE.md。
- 下一步：Git fetch核对远端，显式allowlist暂存审计并普通发布。


## D3-publication-preflight

- 时间：2026-09-03T03:33:38.232Z；环境：本地 Windows CPU-only；步骤 ID：D3-publication-preflight。
- 行动/命令：git fetch origin；git rev-parse HEAD origin/main；git branch --show-current。
- 结果：退出码0，3.03秒；main、HEAD与最新origin/main仍为d5ae95e5f35320ad3d749b637db63197c77a519e，无远端前进或合并冲突。仅GitHub Git操作，无学校服务器连接。
- 产物：Git refs与既有publication授权。
- 下一步：按16路径显式allowlist暂存并执行binary/size/path/whitespace guard。


## D3-staged-publication-audit

- 时间：2026-09-03T03:34:19.226Z；环境：本地 Windows CPU-only；步骤 ID：D3-staged-publication-audit。
- 行动/命令：显式暂存16个Defense代码/配置/测试/文档路径；Python严格比对allowlist、git numstat binary、每个blob大小/后缀、git diff --cached --check。
- 结果：退出码0，16/16路径；0 binary、0 media，最大403222 bytes，whitespace通过。tar/sidecar、artifacts、raw、私有映射/令牌/人答均未暂存；未改E0/E1/E2或D2实现。
- 产物：Git index；16路径清单与staged stat。
- 下一步：重新暂存本审计DEVLOG并创建功能审计提交，普通push main。


## D3-code-audited-commit

- 时间：2026-09-03T03:34:30.453Z；环境：本地 Windows CPU-only；步骤 ID：D3-code-audited-commit。
- 行动/命令：git add -- DEVLOG.md；git diff --cached --check；git commit -m 'Add audited Defense MVP D3 blind annotation system'。
- 结果：退出码0，功能审计提交f38517f9238f16a15b606a52fc81251dfe47a14d，16文件。无媒体/私有产物；原先交接文档和DEVLOG回执一并保留。
- 产物：本地main commit f38517f。
- 下一步：普通push origin main，然后记录发布回执。


## D3-code-normal-push

- 时间：2026-09-03T03:35:08.164Z；环境：本地 Windows CPU-only；步骤 ID：D3-code-normal-push。
- 行动/命令：git push origin main；git rev-parse HEAD origin/main。
- 结果：退出码0，5.27秒；d5ae95e→f38517f普通推送成功，HEAD与origin/main均f38517f9238f16a15b606a52fc81251dfe47a14d。无force-push，无学校服务器操作。
- 产物：GitHub origin/main上的D3功能审计提交。
- 下一步：提交发布回执文档与DEVLOG，再普通推送；最终回执允许只留DEVLOG未提交。


## D3-publication-receipt-document

- 时间：2026-09-03T03:35:08.212Z；环境：本地 Windows CPU-only；步骤 ID：D3-publication-receipt-document。
- 行动/命令：在实现回执中写入已发布功能提交f38517f及16路径审计结果。
- 结果：仅文档变更，产品源码与已验证包snapshot不变。
- 产物：D3_IMPLEMENTATION_RECEIPT.md、DEVLOG.md。
- 下一步：显式暂存两文件、检查后提交发布回执。


## D3-publication-receipt-commit

- 时间：2026-09-03T03:35:23.759Z；环境：本地 Windows CPU-only；步骤 ID：D3-publication-receipt-commit。
- 行动/命令：两路径文档allowlist/二进制/whitespace guard通过后，git commit -m 'Record Defense MVP D3 acceptance and publication'。
- 结果：退出码0，回执提交77f0a2549e22264b9dca7034b1e51ee7fab051c5；仅DEVLOG与D3_IMPLEMENTATION_RECEIPT两文件。
- 产物：本地main commit77f0a25。
- 下一步：普通push并最终核对；本条与最后push回执不递归创建新提交。


## D3-final-push-and-handoff

- 时间：2026-09-03T03:36:11.049Z；环境：本地 Windows CPU-only；步骤 ID：D3-final-push-and-handoff。
- 行动/命令：git push origin main；git rev-parse HEAD origin/main；git status --short；git diff --check；浏览器tabs.list。
- 结果：退出码0，4.61秒；普通推送f38517f→77f0a25成功，HEAD/origin/main均77f0a2549e22264b9dca7034b1e51ee7fab051c5。工作树唯一tracked修改为DEVLOG发布回执，tar/sidecar仍未跟踪未暂存；whitespace通过；临时浏览器tab列表为空，服务均已停止。
- 产物：main功能提交f38517f9238f16a15b606a52fc81251dfe47a14d、回执提交77f0a25；正式bundle c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6；指南/方案/回执齐备。
- 下一步：D3工程ready，可以邀请真人。用户首次执行formal annotator-a/b启动；本次正式会话0、正式人答0，不自动继续D4。本条与上一提交回执作为唯一未提交tracked DEVLOG增量保留，避免无限递归。


## D3-LOAD-01

- 时间：2026-09-03T04:15:07.840Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-01。
- 行动/命令：只读核对用户在用的 8765 服务、练习页 DOM/媒体错误和会话目录；检查 annotation_ui/server 与 D3 约束。
- 结果：practice annotator-a 第1/32；三路 readyState=0、buffered空、duration未知，无解码错误；题目/API正常；终端曾出现一次403 session_rejected，尚不能归因于具体请求。会话无草稿/确认文件。原生媒体请求停滞且界面无超时/重试；不宣称已确认唯一底层原因。
- 产物：src/defense_mvp/annotation_ui.html；用户 practice/annotator-a（原样保留）
- 下一步：使用同源认证 fetch 完整读取原有无损媒体到短期 blob，提供进度/超时/重试；不重编码、不改协议，保留服务端SHA与提交门禁。


## D3-LOAD-02

- 时间：2026-09-03T04:15:48.435Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-02。
- 行动/命令：将加载修复方案追加 D3_CONSTRUCTION_PLAN；决定只调整当前题媒体传输与可恢复UI。
- 结果：采用原字节认证fetch+临时blob，20秒请求超时/一次自动重试、64MiB每路上限；取消和回收、串行就绪更新；冻结协议/输入/答案不变。
- 产物：docs/defense_mvp/D3_CONSTRUCTION_PLAN.md
- 下一步：实现并定向验证。


## D3-LOAD-03

- 时间：2026-09-03T04:18:39.214Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-03。
- 行动/命令：实现 annotation_playback.js 与页面接线；服务启动内联加载器并计算完整脚本CSP；source_evidence增加JS文件。
- 结果：当前题同源认证fetch/长度与类型校验/20秒超时/一次重试/blob；独立读取和解码状态、手动重试保留题目表单；资源取消回收、新video隔离旧事件；媒体就绪串行更新且忽略过期结果；服务端SHA和回答记录逻辑不变。
- 产物：src/defense_mvp/annotation_playback.js；annotation_ui.html；annotation_server.py；annotation_bundle.py
- 下一步：补充故障回归，启动独立practice验证实际加载。


## D3-LOAD-04

- 时间：2026-09-03T04:20:11.610Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-04。
- 行动/命令：新增9项 Node 内置test网络/视频替身测试及pytest入口；HTTP测试核对内联实际脚本CSP与blob许可。
- 结果：覆盖原字节相等、认证选项、403、有限重试、长度/大小/类型、请求及body超时、取消后迟到响应、解码失败/超时、URL回收；无正式答案。
- 产物：tests/defense_mvp/annotation_playback.test.cjs；test_annotation_playback_node.py；test_blind_annotation.py
- 下一步：运行定向回归及独立练习服务。


## D3-LOAD-05

- 时间：2026-09-03T04:20:43.022Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-05。
- 行动/命令：启动8766独立practice QA服务：uv run defense annotate --bundle .../practice-bundle --annotator-id annotator-a --output .../qa-loading-v01/annotator-a --port 8766。
- 结果：成功启动新隔离练习会话；原用户8765和其练习目录继续保留；正式会话未启动。
- 产物：artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-loading-v01/annotator-a
- 下一步：真实浏览器首帧与恢复检查。


## D3-LOAD-06

- 时间：2026-09-03T04:21:44.848Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-06。
- 行动/命令：真实8766浏览器初测；完善解码计时器及时清理、未知网络错误匿名化与等待秒数；增加错误不泄漏诊断测试。
- 结果：首题三路WebM均 readyState=4、duration=2、无error；点击同步播放三路实际时间推进，服务端就绪通过。新增10项Node测试覆盖未知错误消息过滤，解码错误不会被后续超时覆写。
- 产物：src/defense_mvp/annotation_playback.js；annotation_ui.html；tests/defense_mvp/annotation_playback.test.cjs
- 下一步：结束首次定向测试后，用最终源码回归和浏览器恢复/提交切题验收。


## D3-LOAD-07

- 时间：2026-09-03T04:22:16.676Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-07。
- 行动/命令：uv run pytest tests/defense_mvp/test_blind_annotation.py tests/defense_mvp/test_annotation_playback_node.py -q；node --test tests/defense_mvp/annotation_playback.test.cjs。
- 结果：定向pytest77项退出0；最终加载器10项Node测试全部通过，281.8ms；首次定向启动期间有后续小修，最终回归将重新读取最终源码。
- 产物：tests/defense_mvp；控制台测试结果
- 下一步：启动最终Defense全套与全仓回归；独立practice浏览器完整恢复/切题验证。


## D3-LOAD-08

- 时间：2026-09-03T04:23:13.144Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-08。
- 行动/命令：隔离practice页填写一项tie与固定测试备注；等待草稿保存后点击重新加载视频。
- 结果：重载后仍第1题；备注和已选字段完全保留，三路重新可播放；未确认任何回答。
- 产物：.../qa-loading-v01/annotator-a/drafts
- 下一步：重启隔离服务加载最终HTML，再检查草稿恢复、seek/replay与提交切题。


## D3-LOAD-09

- 时间：2026-09-03T04:23:14.289Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-09。
- 行动/命令：按已核对PID/命令终止隔离8766服务，以便加载最终页面源码；草稿已持久化。
- 结果：只停止qa-loading-v01服务，未删除锁/目录；用户8765未动。
- 产物：.../qa-loading-v01/annotator-a
- 下一步：原QA目录显式--resume，核对恢复。


## D3-LOAD-10

- 时间：2026-09-03T04:23:35.782Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-10。
- 行动/命令：同practice bundle/身份/目录以--resume重启8766。
- 结果：最终源码服务启动成功；写锁正常释放恢复，原草稿经存储验证；新运行回执含annotation_playback.js。
- 产物：.../qa-loading-v01/annotator-a/runs
- 下一步：浏览器使用新入口检查最终源码。


## D3-LOAD-11

- 时间：2026-09-03T04:24:31.368Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-11。
- 行动/命令：最终源码8766实际浏览器：3次重载-播放-暂停，统一seek到2秒和从头重播，固定practice答案确认一次并切题。
- 结果：三次完整控件操作924/855/858ms（含工具交互，非纯网络基准）；每路readyState4、2秒、无error、实际播放时钟推进，草稿保持；重启恢复草稿；一条practice固定tie记录成功，下一题2/32三路可播放且表单清空/提交禁用。
- 产物：.../qa-loading-v01/browser/reloads.json；next-question.png；annotator-a/records
- 下一步：再验真实解码错误门禁与用户原练习恢复；继续等待最终回归。


## D3-LOAD-12

- 时间：2026-09-03T04:24:59.021Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-12。
- 行动/命令：启动8767独立practice原始mp4v故障包，输出全新qa-loading-v01/decode-error/annotator-a。
- 结果：服务启动成功；仅工程故障演练，原候选/展示包未改写。
- 产物：.../qa-loading-v01/decode-error/annotator-a
- 下一步：确认无法解码时有具体提示且提交仍禁用。


## D3-LOAD-13

- 时间：2026-09-03T04:26:08.072Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-13。
- 行动/命令：真实原始mp4v故障包浏览器检查：A/B解码失败，填满固定practice字段也不能提交；检查用户8765页面输入。
- 结果：原视频可播放、A/B显示无法解码且提交disabled；仅故障练习草稿，没有确认记录。用户原页面1/32、无选项/信心/备注，尚未填写，可无损重启。
- 产物：.../qa-loading-v01/browser/decode-error.png；decode-error/annotator-a/drafts
- 下一步：停止两项QA服务，并重启同目录用户practice服务。


## D3-LOAD-14

- 时间：2026-09-03T04:26:10.181Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-14。
- 行动/命令：核对命令身份后停止8766/8767 QA与用户旧8765 practice服务；原目录保留。
- 结果：用户session.json SHA=见控制台只读结果，原用户草稿0/确认0；未删锁或目录。QA暂停，准备加载最终源码恢复同一用户会话。
- 产物：.../practice/annotator-a；.../qa-loading-v01
- 下一步：显式--resume重启原用户practice。


## D3-LOAD-15

- 时间：2026-09-03T04:26:42.937Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-15。
- 行动/命令：uv run defense annotate --bundle .../practice-bundle --annotator-id annotator-a --output .../practice/annotator-a --resume。
- 结果：原用户同一practice会话恢复成功，写锁安全重获，新增运行回执；旧session.json前SHA为54d03890e4bf1166d7ade041a6a0344d3d9084e0f837922109feb6d99be01093。QA标签页已关闭。
- 产物：.../practice/annotator-a/runs
- 下一步：在用户原标签页打开新版入口，只验证媒体，不填写或提交答案。


## D3-LOAD-16

- 时间：2026-09-03T04:27:23.780Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-16。
- 行动/命令：用户原8765标签页使用新版入口，点击同步播放后全部暂停；只读检查表单与媒体并留证。
- 结果：恢复原practice第1/32；三路readyState4、duration2、无error、播放时间约0.298s；仍未选字段、无备注。实际用户试用卡住的问题已恢复。
- 产物：.../qa-loading-v01/browser/user-session-restored.json；user-session-restored.png
- 下一步：完成最终回归、身份复核、指南与审计发布；保留用户当前可用练习服务。


## D3-LOAD-17

- 时间：2026-09-03T04:27:59.863Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-17。
- 行动/命令：运行本地compileall（Defense源码）、CLI --help及正式包只读verify。
- 结果：命令退出0；正式包SHA c03640...未变；prepared_bundle/incomplete，42比较、10共享自动平局、每人32手工项、导出回答0。未创建正式会话。
- 产物：.../qa-loading-v01/cli-help.txt；formal-verification.txt
- 下一步：补齐最终源码/全部输入与会话身份报告，更新操作文档。


## D3-LOAD-18

- 时间：2026-09-03T04:28:00.639Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-18。
- 行动/命令：更新ANNOTATION_GUIDE的加载、等待、重试、草稿保留与错误恢复操作。
- 结果：明确新流程、原字节临时blob与读取/解码超时边界，Node仅开发测试；正式首次启动仍由用户执行。
- 产物：docs/defense_mvp/ANNOTATION_GUIDE.md
- 下一步：最终身份与回归报告、审计发布。


## D3-LOAD-19

- 时间：2026-09-03T04:28:46.672Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-19。
- 行动/命令：通过load_bundle验证正式/练习全输入清单、媒体、映射和证明，比较发布前后bundle与用户session SHA；保存最终源码环境。
- 结果：通过：正式/练习bundle SHA均与原已验收值相同；60原MP4、39展示引用全部验证；用户session.json SHA与重启前完全相同；正式会话0/人答0；本次新增确认仅1条隔离practice。
- 产物：.../qa-loading-v01/identity-verification.json
- 下一步：最终测试结果与发布审计。


## D3-LOAD-20

- 时间：2026-09-03T04:28:48.344Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-20。
- 行动/命令：uv run python -m compileall -q src tests；git diff --check（逐项检查退出码）。
- 结果：源码与测试编译通过、whitespace检查通过，退出0。
- 产物：src；tests；Git工作树
- 下一步：收齐最终pytest结果，封存修复回执与发布。


## D3-LOAD-21

- 时间：2026-09-03T04:30:00.199Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-21。
- 行动/命令：尝试新增修复回执并链接原D3回执。
- 结果：apply_patch因原回执标题锚点不精确而拒绝；尚未声称文档完成。改用已读取的文件尾准确锚点重试。
- 产物：docs/defense_mvp/D3_IMPLEMENTATION_RECEIPT.md
- 下一步：核对后完成修复文档。


## D3-LOAD-22

- 时间：2026-09-03T04:30:44.377Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-22。
- 行动/命令：新增D3_VIDEO_LOADING_FIX_RECEIPT，并在原D3回执链接追加修复记录。
- 结果：现场证据、解决方式、内存/超时边界、浏览器/草稿/解码错误/用户恢复/原SHA均记录；明确旧准备包源码与新运行源码各自留证。最终回归仍在运行，未预先标通过。
- 产物：docs/defense_mvp/D3_VIDEO_LOADING_FIX_RECEIPT.md；D3_IMPLEMENTATION_RECEIPT.md
- 下一步：读取最终回归结果并完成审计发布。


## D3-LOAD-23

- 时间：2026-09-03T04:31:25.184Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-23。
- 行动/命令：最终源码执行 uv run pytest tests/defense_mvp -o addopts='' -q。
- 结果：116 passed in 397.93s，退出0；包含最终10项Node子测试入口，无跳过。源码测试过程中未继续修改。
- 产物：.../qa-loading-v01/defense-tests.txt
- 下一步：等待全仓回归，核对远端和发布允许路径。


## D3-LOAD-24

- 时间：2026-09-03T04:31:27.911Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-24。
- 行动/命令：git fetch origin main；核对HEAD、origin/main、当前分支与已有暂存区。
- 结果：fetch成功；当前main和origin/main均为77f0a2549e22264b9dca7034b1e51ee7fab051c5，暂存区空，无远端前进冲突；既有Defense授权允许审计commit/普通push。
- 产物：Git main/origin/main
- 下一步：全仓测试通过后完成回执并按显式allowlist发布。


## D3-LOAD-25

- 时间：2026-09-03T04:33:03.544Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-25。
- 行动/命令：git add显式12路径；Python核对暂存集合完全匹配allowlist、无NUL二进制、每文件<1MiB，git diff --cached --check。
- 结果：暂存审计通过；仅Defense源码/测试/文档/DEVLOG，tar/sidecar/媒体/原始记录/artifacts全部排除。尚未commit，等待全仓结果。
- 产物：Git暂存区12文件
- 下一步：填入最终回归结果，重新暂存文档/DEVLOG后提交并普通推送。


## D3-LOAD-26

- 时间：2026-09-03T04:34:27.795Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-26。
- 行动/命令：最终源码 uv run pytest -o addopts='' -q，全仓回归。
- 结果：219 passed in 689.45s，退出0；无失败/跳过；本次最终Defense全套116和Node10亦通过。
- 产物：.../qa-loading-v01/repository-tests.txt
- 下一步：封存最终结果并按既有授权commit/push。


## D3-LOAD-27

- 时间：2026-09-03T04:34:27.839Z；环境：本地 Windows CPU-only；步骤 ID：D3-LOAD-27。
- 行动/命令：将最终116/219回归、10项Node、CLI/身份/审计结果填入修复回执。
- 结果：最终工程验收通过；当前用户练习已恢复、可播放；真实输入和协议不变。记录全仓实际689.45秒，没有借用历史通过数。
- 产物：docs/defense_mvp/D3_VIDEO_LOADING_FIX_RECEIPT.md
- 下一步：最终暂存守卫后创建修复提交，再普通push。
