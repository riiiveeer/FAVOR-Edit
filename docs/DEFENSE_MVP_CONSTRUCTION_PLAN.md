# Defense MVP 详细施工方案

> 暂定题目：**基于约束式多目标排序的指令视频编辑候选选择与盲评系统**
> 文档版本：v1.4-d4-complete（2026-09-04 正式统计收口）
> 制定日期：2026-09-01
> 目标完成日期：2026-09-08
> 施工环境：本地 Windows、CPU-only
> 当前状态：**D4 正式聚合与统计分析已完成并验证；可以进入 D5，D5 尚未启动**

D1 兼容接收、D2 真实 CPU 评分/选择、D3 本地双人盲评与 D4 正式统计已完成；
最终为 `formal/dual/complete`，64 条真人确认记录 + 10 条共享自动平局，A/B 各42/42。
最终报告与答辩材料尚未完成。D3 详细证据见 [正式标注完成回执](defense_mvp/D3_FORMAL_ANNOTATION_RECEIPT.md)、
[D3 实现回执](defense_mvp/D3_IMPLEMENTATION_RECEIPT.md) 与 [标注指南](defense_mvp/ANNOTATION_GUIDE.md)。
实际运行、冻结身份、重建命令及 D3 接口见 [D2 实现回执](defense_mvp/D2_IMPLEMENTATION_RECEIPT.md)。
D4 正式统计、输出身份和诚实结论见 [D4 实现回执](defense_mvp/D4_IMPLEMENTATION_RECEIPT.md)；
解封前协议见 [D4 施工方案](defense_mvp/D4_CONSTRUCTION_PLAN.md)。D5 尚未启动。

---

## 1. 项目定位

### 1.1 一句话目标

在不训练视频模型、不依赖新增 GPU 机会的条件下，复用已生成的 10 个 DAVIS
输入与 50 个真实 AnyV2V 候选，完成一个可复现的候选导入、CPU 多维评分、
约束式多目标选择、双人盲评、统计分析和自动报告系统。

### 1.2 答辩主线

```text
同一输入的不同随机种子产生质量差异
              ↓
简单平均分允许“高保持、低编辑”相互补偿
              ↓
CPU 指标描述编辑、保持、时序和质量代理
              ↓
先设编辑/保持门槛，再做 Pareto + max-min 选择
              ↓
双人盲评比较 N=4 vs N=1、约束式 vs 线性加权
              ↓
报告有效性、失败案例、能力边界和复现证据
```

### 1.3 技术贡献

1. mask-aware 的四维 CPU 评分；
2. 防止分数补偿的约束式 Pareto/max-min 选择；
3. 可复现的 N=1/2/4 平衡子集设计；
4. 位置随机化的双人盲评与分歧保留；
5. Bradley–Terry、tie-aware 统计和 sample-cluster bootstrap；
6. checksum、配置、输入身份和报告依赖的审计闭环。

---

## 2. 完成定义

### 2.1 必须交付

截止 2026-09-08，以下条件全部满足才视为 Defense MVP 完成：

- 独立的 `defense_mvp` Python 包和 `defense` CLI；
- 从只读 E0 回传包建立本地、相对路径化、带 checksum 的 50 候选清单；
- 7 个颜色/局部任务的 35 个候选完成 CPU 四维评分；
- 3 个对象转换任务的 15 个候选进入定性能力边界案例；
- 随机、等权线性、约束式 Pareto 三种选择方法均可复现运行；
- N=1/2/4 设计、选择、比较计划和成本统计完整；
- 两名独立标注者各完成 32 个实际观看题，加上 10 项共享自动平局，各形成 42 项 coverage；
- 生成一致率、Cohen's kappa、Bradley–Terry 排名、tie-aware win rate 和
  2,000 次 sample-cluster bootstrap 结果；
- 生成 Markdown、CSV、SVG/PNG 和案例页；
- 全仓库测试、Defense MVP 定向测试、CLI smoke、compileall、checksum verifier 和
  `git diff --check` 全部通过；
- 完成 8–10 页中文 slides、60–90 秒演示录屏和 5–7 分钟讲稿。

### 2.2 不以正结果作为完成条件

以下三种结果均可作为有效答辩结论：

1. 约束式方法优于随机和线性加权；
2. 约束式方法只在部分任务有效；
3. CPU 代理指标与人类偏好不一致，暴露语义理解边界。

不得为了得到正结果而在查看正式人评后修改阈值、删样本或改比较计划。任何正式协议
变化必须使用新实验 ID，并在 DEVLOG 中说明。

### 2.3 明确不做

- 不训练 LoRA、DPO、SFT 或其他深度模型；
- 不生成新候选，不使用学校 GPU；
- 不把 mock、synthetic、replay 输出写成真实研究测量；
- 不宣称 CPU 指标理解任意语义编辑；
- 不把 3 个对象转换任务纳入 CPU 指标胜率主表；
- 不修改 E1 的 `PASS_PROVISIONAL` / `reward-v0.yaml` 门禁；
- 不修改 E2 的 8 候选、80 trial、280 pair、560 request 正式协议；
- 不以临时安装 PyTorch、OpenCLIP 或大型权重作为关键路径；
- 不覆盖 E0、E1、E2 的任何既有目录或产物。

---

## 3. 数据范围与回传协议

### 3.1 定量主实验：7 个任务

| sample_id | 类型 | 指令 | CPU faithfulness 代理 |
|---|---|---|---|
| bear-white | attribute | Make the bear white | 白色支持度 + mask 内变化 |
| bus-red | attribute | Make the bus red | 红色支持度 + mask 内变化 |
| elephant-pink | attribute | Make the elephant pink | 粉色支持度 + mask 内变化 |
| classic-car-blue | attribute | Make the classic car blue | 蓝色支持度 + mask 内变化 |
| hiker-backpack | local | Add a red backpack to the hiker | 红色新增支持度 + 局部变化 |
| rider-helmet | local | Add a yellow helmet to the rider | 黄色新增支持度 + 局部变化 |
| car-headlights | local | Make the car headlights glow blue | 蓝色高亮支持度 + 局部变化 |

每个任务保留 5 个 E0 seed：`101/202/303/404/505`，共 35 个定量候选。

### 3.2 定性能力边界：3 个任务

- `dog-tiger`；
- `horse-zebra`；
- `mallard-swan`。

纯 NumPy/Pillow 指标不能可靠判断动物类别是否真的转换。这 15 个候选只用于展示
CPU 低层指标与语义成功可能不一致，不进入定量胜率主表。

### 3.3 E0 回传包最小要求

用户或服务器端 agent 应从既有 E0 只读源建立一个新的、唯一的回传包。不得移动、删除、
修改或覆盖 E0 原目录。包中至少包含：

1. `plan.json`；
2. `candidates.json`；
3. 10 个 source MP4；
4. 50 个 candidate MP4；
5. 每个 source/candidate 对应的 16 帧；
6. 10 组 DAVIS masks；
7. `audit-manifest.json`；
8. 已填写的 `audit.csv` 或人工粗审记录；
9. `W1_REPORT.md`；
10. E0 关键运行日志、代码 snapshot 和模型/AnyV2V revision 记录；
11. 覆盖回传包全部常规文件的 `PACKAGE_SHA256SUMS`；
12. `PACKAGE_MANIFEST.json`，记录原始只读路径、打包时间、命令、文件数和总字节数。

不需要回传模型权重、conda 环境、cache、inversion latent 或其他大体积中间状态，除非
`candidates.json` 的正式校验明确依赖它们。

### 3.4 本地路径

- 原始回传包：`data/raw/defense_mvp/e0-delivery-v01/`；
- ingest：`artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/`；
- CPU 指标：`artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/`；
- 设计与选择：`artifacts/defense_mvp/DEFENSE-MVP-v01/design/`；
- 选择记录与比较计划：`artifacts/defense_mvp/DEFENSE-MVP-v01/selection/`；
- 人工标注：`artifacts/defense_mvp/DEFENSE-MVP-v01/human/`；
- 分析：`artifacts/defense_mvp/DEFENSE-MVP-v01/analysis/`；
- 最终本地报告：`artifacts/defense_mvp/DEFENSE-MVP-v01/report/`。

`data/raw/` 和 `artifacts/` 已由 `.gitignore` 排除。Git 只跟踪代码、配置、测试、
协议、匿名化小型摘要、slides 和必要的 checksum/身份记录。

---

## 4. CPU 指标协议

### 4.1 统一预处理

每个 source/candidate 使用 E0 已提取、按帧对齐的 16 帧 512×512 RGB uint8 图像；
8 fps 为原始视频生成配置。视频、逐帧和 mask checksum 必须全部通过。评分端不重新
抽帧、不 resize、不修改原始媒体；不符尺寸或模式直接失败。RGB 转换为 `float32 [0,1]`。

正式 mask 解码冻结为 `index-nonzero-v1`：读取 DAVIS 原始整数类别索引，0 为背景，
非零索引并集为前景；不得将 palette 的显示颜色转灰度再阈值化。配置中的历史
`mask_threshold: 0.5` 仅保留兼容，当前协议不使用它。逐帧前景覆盖率限制为 [0.001, 0.95]。

local 任务使用的是 DAVIS 前景对象 mask，不是背包、头盔或车灯的专门分割。因此 F 只能
衡量前景内新增目标色，P 只能衡量前景外保持；不能证明新增颜色在正确子部位，也不能
检测前景内所有非目标区域破坏。不得把这些代理写成细粒度定位或通用语义准确率。

### 4.2 指令忠实度代理 F

对 7 个颜色/局部任务计算三个分量：

1. 目标区域变化量：`E = mean(abs(candidate - source) inside mask)`；
2. 目标颜色支持度：根据配置中的 HSV 色域计算 mask 内目标颜色像素比例；
3. local 任务新增颜色证据：只计算相对 source 新出现的目标色，避免原视频已有颜色虚高。

组合分采用 `F = sqrt(clipped_edit_strength * clipped_color_support)`。white 使用低
saturation + 高 value；red/pink/blue/yellow 使用冻结的 hue、saturation、value 区间。
原始分量、阈值命中数和组合分全部落盘。F 是 task-specific proxy，不是通用语义准确率。

### 4.3 非目标区域保持度 P

使用 mask 外 source/candidate 绝对误差：

`P = 1 - mean(abs(candidate - source) outside mask)`

保存每帧 P 和总体均值；报告阶段由已保存逐帧值派生最差帧与低分位数。mask 覆盖异常小
或异常大时评分失败，不删帧或删候选。

### 4.4 时序一致性 T

定义编辑残差 `R_t = candidate_t - source_t`，使用相邻残差变化衡量闪烁：

`T = 1 - mean(abs(R_t - R_(t-1)))`

分别报告相邻 mask 并集内、并集外和全帧值；总 T 使用全帧平均。逐帧数组的首项 1.0
是无前驱帧的占位值，总体只平均其余 15 个相邻对。残差差值可能超过 1，最终分数裁剪
到 [0,1]。T 衡量编辑残差是否突变，不等价于光流一致性，也未做运动补偿。

### 4.5 视觉质量代理 Q

只用 NumPy/Pillow 计算：

- 灰度水平/垂直梯度能量；
- candidate/source 梯度能量比；
- 过曝/欠曝像素比例；
- 帧间亮度闪烁；
- 异常帧计数。

亮度使用 BT.601 系数 (0.299, 0.587, 0.114)。梯度保留取 candidate/source 比值及其
倒数的较小者（双方近零时记 1）；曝光正常为亮度在 [0.02,0.98] 内的像素比例；亮度
稳定性为 `clip(1 - abs(diff(mean(candidate_luma-source_luma))) / 0.10)`，首项为 1。
Q 取三项各自逐帧均值的几何平均；各逐帧子项、异常计数单独保存。

### 4.6 标准化与冻结

- 原始 F/P/T/Q 永久保留；
- 排序使用当前候选子集内部的稳定 rank-percentile；
- 并列按原始值和 candidate_id 固定顺序处理；
- 指标定义、HSV、mask 索引解码与随机种子在人评开始前冻结；
- 正式人评开始后不得修改指标、回填候选或删掉低分样本。

---

## 5. 选择算法

### 5.1 Baseline A：确定性随机选择

使用 `randomization_seed=20260901`、trial_id、N 与方法名的规范化 SHA-256 对子集大小
取模，选择稳定索引。相同配置重复执行必须选出同一 candidate。三方法都覆盖 N=1/2/4；
N=1 时它们必然选中同一候选。

### 5.2 Baseline B：等权线性加权

`Score_linear = (F + P + T + Q) / 4`

输入为子集内 rank-percentile。该方法允许高分维度补偿低分维度，是主要对照。

### 5.3 Proposed：约束式 Pareto + max-min

对每个候选子集：

1. F 不低于子集 F 中位数；
2. P 不低于子集 P 的 25% 分位数；
3. 在可行候选中求四维 Pareto 非支配前沿；
4. 优先最大化四维最小值；
5. 再最大化四维几何平均；
6. 最后按 candidate_id 稳定决胜。

若 F/P 联合门槛导致空集，使用明确的 `fallback=true` 路径：先最大化 `min(F,P)`，
再按 T、Q 和 candidate_id 决胜。报告必须统计 fallback 次数。

### 5.4 Bradley–Terry 的用途

Bradley–Terry 只用于聚合正式人评，不使用同一批人评先训练再评估，从而避免循环论证。
自动选择仅依赖在人评前冻结的 CPU 指标。

---

## 6. N=1/2/4 与盲评设计

### 6.1 平衡子集

每个 sample 的 5 个 seed 使用确定性 cyclic permutation。每个 trial 的 N=1、N=2、N=4
均为同一候选顺序的前缀，保证候选池嵌套。至少建立 5 个平衡 trial，使每个 seed 在不同
位置均获得覆盖。成本曲线复用同一个 5 候选池，不把历史候选写成本项目新生成的 GPU 成本。

### 6.2 42 个正式比较

每位标注者收到相同的 42 个 comparison：

- 28 个：7 个 sample × 4 个平衡 trial，比较 Proposed N=4 与 N=1；
- 14 个：7 个 sample × 2 个平衡 trial，比较 Proposed N=4 与 Linear N=4。

若两种方法选中同一 checksum 视频，该 comparison 标记为 automatic tie，保留在计划和
统计分母中，但无需人工重复观看。

### 6.3 盲法与位置去偏

- 页面不显示 seed、方法、N、分数或 candidate_id；
- 页面只显示 source、指令、A、B 和必要的 contact sheet；
- annotator-a/b 使用 comparison_id、annotator_id 和固定随机种子派生独立 A/B 方向；
- 每位标注者写入独立、no-replace 的 JSONL；
- 标注过程中不展示累计统计；
- 两位标注者不得讨论具体样本答案。

### 6.4 标注字段

每个 comparison 记录 overall、faithfulness、preservation、temporal_consistency、
visual_quality；每项均允许 A/B/tie/uncertain。另记录 confidence、可选 notes、
comparison_id、annotator_id、display_direction、timestamp 和媒体 checksum。

### 6.5 双人分歧处理

本项目不依赖第三位标注者：

- 完全一致：采用共同结果；
- 一人 decisive、一人 tie：聚合为 tie；
- A/B 相反或任一 uncertain：聚合为 uncertain；
- 不在看到方法身份后做主观裁决。

同时报告 exact agreement、各字段 agreement、Cohen's kappa、tie rate 和 uncertain rate。

---

## 7. 统计分析

### 7.1 主指标

- Proposed N=4 vs N=1 tie-aware win rate；
- Proposed N=4 vs Linear N=4 tie-aware win rate；
- decisive win rate、tie rate、uncertain rate；
- 两位标注者 exact agreement 与 Cohen's kappa。

tie 和 uncertain 在 tie-aware win rate 中均记为 0.5，但必须分别报告原始数量。

### 7.2 Bradley–Terry

将聚合后的 decisive pair 转换为 Bradley–Terry 胜负边，得到方法的中心化 ability。
若图不连通或 decisive 边不足，输出 `insufficient_connectivity`，不得伪造排名。

### 7.3 Bootstrap

- cluster 单位：sample_id；
- 主表 cluster 数：7；
- 固定 seed：`20260901`；
- 迭代：2,000；
- 报告 percentile 95% CI；
- 明确 7 个 cluster 只能描述小样本不确定性，不声称论文级显著性。

### 7.4 成本

分别报告 E0 历史生成 runtime/VRAM、CPU 指标总时长与每候选时长、选择算法时长、
每位标注者耗时、N=1/2/4 候选数量以及报告生成时间。

---

## 8. 代码结构与 CLI

计划新增：

```text
configs/defense_mvp/pilot.yaml
src/defense_mvp/{cli,models,io,ingest,metrics,design,selection,annotations,analysis,reporting,verification}.py
tests/defense_mvp/
docs/defense_mvp/{DATA_HANDOFF,ANNOTATION_GUIDE,DEFENSE_REPORT,DEFENSE_SCRIPT}.md
docs/defense_mvp/slides/
```

允许复用 `w1_pipeline.hashing` 和 E1/E2 已测试的纯函数/算法思路。复用必须通过新模块
窄接口完成，不得修改 E1/E2 的固定 cardinality 与 gate。

目标 CLI：

```powershell
uv run defense validate-config
uv run defense verify-delivery --delivery <path> [--compat-profile server-agent-20260902-v01]
uv run defense extract-delivery --archive <tar> --checksum <sidecar> --output <new-dir> [--compat-profile server-agent-20260902-v01]
uv run defense ingest --delivery <path> --output <new-dir>
uv run defense score --ingest <manifest> --output <new-dir>
uv run defense design --metrics <metrics.jsonl> --ingest <manifest> --output <new-dir>
uv run defense select --design <design.json> --metrics <metrics.jsonl> --output <new-dir>
```

上述命令已实现；本次交接的 ingest 也必须显式传同一 `--compat-profile`。省略参数仍为
严格模式，兼容档案只绑定唯一原始包。D3 已实现（参数详见标注指南）：

```powershell
uv run defense prepare-annotation --selection <dir> --ingest <manifest> --output <new-dir> --mode formal
uv run defense annotate --bundle <dir> --annotator-id annotator-a --output <annotator-a-dir> [--resume]
uv run defense export-annotations --bundle <dir> --session <dir> --output <new-dir>
uv run defense verify-annotations --bundle <dir> --export <a-export> --export <b-export>
```

以下 D4 命令已经实现；都要求完整封存目录和关联输入，不接受裸 answers 文件：

```powershell
uv run defense aggregate --bundle <bundle-dir> --left <a-export-dir> --right <b-export-dir> --dual-verification <file> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --output <new-dir>
uv run defense analyze --aggregate <dir> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --output <new-dir>
uv run defense verify-analysis --bundle <bundle-dir> --left <a-export-dir> --right <b-export-dir> --dual-verification <file> --aggregate <dir> --analysis <dir> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --output <new-file>
```

以下为 D5–D6 待实现命令，不可当作现成接口：

```powershell
uv run defense report --analysis <dir> --output <new-dir>
uv run defense verify --experiment-root <dir> --output <new-file>
```

所有正式输出采用 no-replace。失败后保留诊断，不自动删除或覆盖。真实数据命令只有在
回传包 checksum 验收通过后运行。

---

## 9. 逐日施工表

### 9 月 1 日：D0 协议与数据回传

**Codex**

- 固定授权、施工方案、scope 和完成定义；
- 编写服务器只读回传清单；
- 不启动功能代码。

**用户/服务器端 agent**

- 只读核对 E0 路径；
- 建立新的唯一 package；
- 生成 package manifest 与 SHA256SUMS；
- 将包回传本地。

**退出条件**：本文档经用户审阅；E0 原目录未修改；回传动作有独立日志和 checksum。

### 9 月 2 日：D1 scaffold + ingest

- 新建 package、配置、CLI 和 tiny fixture；
- 实现 50 candidate / 10 source / masks / frames 身份校验；
- 将服务器绝对路径重映射为本地相对路径；
- 实现不可覆盖的 ingest receipt；
- 定向测试、CLI smoke、DEVLOG、审计提交与普通推送。

**退出条件**：tiny fixture happy/failure tests 通过；真实回传包得到 passed 或准确 failed
report；不对 failed package 计算指标。

### 9 月 3 日：D2 CPU metrics + selection

- 实现 F/P/T/Q 原始分量与 task-specific HSV 配置；
- 实现 random、linear、constrained Pareto；
- 实现 N=1/2/4 cyclic design；
- tiny fixture 验证目标颜色增加提高 F、背景破坏降低 P、闪烁降低 T；
- 对真实 35 candidate 运行 CPU score并冻结 config checksum。

**退出条件**：方向性测试通过；35/35 定量候选无静默缺失；15 个对象任务标记
qualitative-only；正式人评前配置已冻结。

### 9 月 4 日：D3 blind annotation

- 复用已冻结的 D2 42 comparison 计划，生成独立 no-replace 盲评包；
- 实现本地 range-video 标注页面与两个 annotator 身份；
- 验证 A/B 方向平衡；
- 工程验收后两位评审已先后独立完成正式标注；A/B各32条确认记录。

**退出条件**：页面不泄漏方法、N、seed 和分数；annotator-a/b 输出路径分离；媒体
checksum 与冻结选择一致；最终双人验证 `formal/dual/complete`、各42/42、缺题0。**已满足。**

### 9 月 5 日：D4 aggregate + analysis

- 冻结并接收已验证的A/B正式导出，不改写D3事实源；
- 聚合一致、tie、uncertain；
- 计算 kappa、Bradley–Terry、win rate、bootstrap 和成本；
- 生成第一版主表与失败案例。

**退出条件**：64 条真人原始回答 + 10 项共享 automatic tie，各人42 coverage；分析可由冻结输入完全重建。**已满足。**

正式输出为42个唯一聚合（32 human pair + 10 automatic）、family 28/14、7 sample clusters；
独立 verifier 复算通过。主结果与局限见 D4_IMPLEMENTATION_RECEIPT；D5 尚未启动。

### 9 月 6 日：D5 report + slides draft

- 生成 Markdown/CSV/SVG/案例页；
- 完成 8–10 页中文 slides 初稿和 5–7 分钟讲稿；
- 选择录屏路径；
- 完整本地回归。

**退出条件**：每个图表可追溯；slides 不超出证据；负结果也有完整叙事。

### 9 月 7 日：D6 freeze + recording

- 只修复展示问题，不改变冻结实验协议；
- 运行全仓库 pytest、compileall、CLI、verifier、diff/checksum 审计；
- 建立最终交付 manifest；
- 创建审计提交并普通推送；
- 录制 60–90 秒演示并至少进行两次计时演练。

**退出条件**：代码、配置、匿名化结果、报告、slides、讲稿、录屏冻结；现场 demo 失败时
录屏仍能独立展示成果。

### 9 月 8 日：缓冲与答辩

只允许修复错字、链接、播放兼容性和致命展示问题；不重新调指标、不换样本、不重做人评。
保留 PDF slides 和两份录屏副本。

---

## 10. 风险与降级

| 风险 | 截止信号 | 降级 |
|---|---|---|
| E0 回传包不完整 | 9 月 2 日中午仍缺 checksum/媒体 | 先施工完整 sample；少于 4 个完整定量 sample 时只交工程演示，不做正式结论 |
| masks 缺失或错位 | ingest verifier 失败 | 请求重新打包既有 mask，不临时伪造 |
| HSV 忠实度代理失真 | 方向性 sanity 明显失败 | 使用人工 faithfulness anchor + CPU P/T/Q |
| CPU 评分过慢 | 35 candidate 超过 2 小时 | 优化向量化和缓存，不静默减少正式帧数 |
| 两人未完成 42 组 | 9 月 5 日中午 coverage 不足 | 优先完成 28 个 N=4 vs N=1，线性对照降为次要 |
| 算法常选同一视频 | automatic tie 比例高 | 如实报告 selector 收敛，不改阈值追求差异 |
| Proposed 未胜出 | 正式结果不高于 baseline | 报告代理边界或假设未获支持 |
| slides 超时 | 9 月 6 日晚未成稿 | 保留 1 主表、2 图、3 案例、8 页最小答辩包 |
| 现场不稳定 | 9 月 7 日演练失败 | 使用冻结录屏和 PDF slides |

---

## 11. 验收、DEVLOG 与发布

### 11.1 每个里程碑记录

每个独立开发、测试或运行步骤完成后立即追加 DEVLOG，记录时间、环境、步骤 ID、code
snapshot、输入/配置/checksum、命令、结果、计数、runtime、artifact 绝对路径、失败和下一步。

### 11.2 本地验收命令

```powershell
uv run pytest tests/defense_mvp -q
uv run pytest
uv run python -m compileall -q src tests
uv run defense validate-config
uv run defense verify --experiment-root <root> --output <new-report>
git diff --check
git status --short --branch
```

### 11.3 发布边界

- 仅普通 push 到 `main`，禁止 force-push；
- commit 前核对 staging path count 和 staged diff；
- 不提交 MP4、frames、模型、cache、数据库或机器绝对路径；
- 不提交 annotator 真实姓名，只用 `annotator-a/b`；
- final push 后核对本地 HEAD 与 `origin/main`；
- 为避免 push receipt 无限递归，最终 push 后允许只保留该 push 的本地 DEVLOG 回执，
  并明确标记为唯一未提交修改。

---

## 12. 答辩材料

### 12.1 Slides：8–10 页

1. 问题与动机；
2. 数据与 50 个真实候选；
3. 系统流程图；
4. 四维 CPU 指标；
5. 线性补偿问题与约束式 Pareto；
6. 双人盲评协议；
7. 主结果表和置信区间；
8. 成功与失败案例；
9. 工程复现与审计；
10. 结论、局限和后续扩展。

### 12.2 录屏：60–90 秒

依次展示冻结配置、checksum verifier、盲评页面、三方法选择、自动报告和最终主表。

### 12.3 5–7 分钟讲稿配时

- 45 秒：问题；
- 60 秒：数据与系统；
- 90 秒：指标与算法；
- 60 秒：盲评；
- 90 秒：结果和案例；
- 45 秒：工程亮点、局限和结论。

---

## 13. 功能代码开工 gate

只有以下条件满足后才进入功能代码：

1. 用户确认本文档；
2. `AGENTS.md` 已记录授权；
3. 工作树现有修改已识别且不覆盖用户内容；
4. 新模块、实验 ID、路径和禁止边界已固定；
5. 服务器回传由用户/服务器 agent 执行，本地 agent 不越权；
6. D1 可先用 tiny fixture 开发，但正式 CPU 测量必须等待 E0 package verifier PASS。

若改变题目、截止日期、7+3 数据边界、42×2 人评规模或提交/推送权限，必须先更新本文档
并立即记录 DEVLOG。
