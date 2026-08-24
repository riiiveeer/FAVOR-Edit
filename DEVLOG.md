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
