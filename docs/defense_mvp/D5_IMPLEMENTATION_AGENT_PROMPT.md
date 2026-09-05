# D5 报告与 Slides 初稿：新对话施工提示词

交接快照：2026-09-05。以下是给承接 agent 的完整任务指令；用户让你阅读并执行本文时，
按本地施工任务处理，不只复述方案。本文是启动导航，不替代对真实工作树、正式产物和最新
`DEVLOG.md` 的核对；文中的 commit、SHA 和测试数只是编制本文时的基线，新对话必须以现场为准。

## 1. 任务、授权与停止点

请在 `D:\lab idea` 承接 Defense MVP，完成 D5 可追溯报告、图表、案例页、8–10 页中文 slides
初稿和 5–7 分钟讲稿工程。项目暂定题目为“基于约束式多目标排序的指令视频编辑候选选择与
盲评系统”，目标交付日为 2026-09-08。D1–D3 的真实输入、CPU 评分、三方法选择和双人盲评
均已封存；D4 已完成正式聚合、统计分析和独立验证，状态明确为“可以进入 D5”。

先核对现场，把 D5 的事实来源、叙事边界、图表语义、确定性案例选择、报告/slide 结构、CLI、
产物和测试矩阵写入 `docs/defense_mvp/D5_CONSTRUCTION_PLAN.md`。在打开案例媒体前，先把案例
选择和展示帧规则写入版本化配置并用 synthetic/tiny fixture 测试；随后才对唯一 D4 输出生成
一份 no-replace D5 正式草稿。普通工程与版式选择自行决定，不反复询问；只有输入身份冲突、
必须改变 D4 事实/统计口径、无法保留的工作树冲突、必需素材缺失或必要权限缺失时才停下来
报告证据。

沿用根 `AGENTS.md` 的 Defense MVP 本地 CPU 开发、文档/报告/slides、DEVLOG、审计提交和普通
推送 `main` 授权。默认单 agent 执行，不创建额外对话、计划任务或远程工作。制作 slides 时
必须使用当前环境提供的 `presentations:Presentations` skill：主 agent 先完整阅读其 `SKILL.md`，
再按要求调用 workspace dependency loader、生成并渲染 PPTX、逐页视觉检查。Markdown 报告不
要求额外创建 DOCX；不要为了“更正式”自行引入 Word/PDF 工作流。D5 草稿 PDF 仅在 slides skill
的验证流程需要或现有工具可稳定生成时输出，最终 PDF 冻结属于 D6。

禁止连接学校服务器、读写 DATA4、运行 GPU/模型、生成新视频候选、重新评分/选择/标注/聚合、
修改 sealed E0 或 D1–D4 事实源。禁止为了更好叙事而删样本、改阈值、改 tie/uncertain 口径、
重跑人评、改 bootstrap、调换 family 分母或挑选只有利案例。D5 可以揭示方法标签并读取已验证
的 D4 聚合/统计和必要的只读媒体关联，但不得读取/发布 notes、入口 token、private mapping、
annotator 真实身份或 64 条逐题原始答案。

本次停止点是：**D5 报告工程和验证器通过测试；唯一正式 D4 输入生成一份可重建、验证通过的
no-replace D5 输出；Markdown/CSV/SVG/PNG、可追溯案例页、8–10 页中文 PPTX 初稿、逐页渲染、
5–7 分钟讲稿和录屏路径方案完成；D5 回执和审计发布完成，可以进入 D6 展示冻结与录屏。**
不自动继续 D6，不录屏，不建立最终交付 manifest，不把 slides 初稿称为最终答辩版，也不宣称
整个 Defense MVP 已完成。

## 2. 首轮核对：以现场为准，不重做 D1–D4

按顺序完整阅读和核对：

1. `D:\lab idea\AGENTS.md` 及适用目录级规则。
2. 本文件和 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`，重点读取 1、2、7、8、9 月 6 日、10–12。
3. `docs/defense_mvp/D4_IMPLEMENTATION_RECEIPT.md`、`D4_CONSTRUCTION_PLAN.md`、
   `D3_FORMAL_ANNOTATION_RECEIPT.md`、`D3_IMPLEMENTATION_RECEIPT.md`、
   `D2_IMPLEMENTATION_RECEIPT.md`；较早回执中的“D4/D5 未完成”是历史快照，不是当前状态。
4. `DEVLOG.md` 末尾及 D4-REAL / D4-ACCEPT / D4-ACCEPT-PUBLISH 记录；不要一开始输出整个长文件。
5. `src/defense_mvp/` 的 analysis、analysis_models、analysis_verification、aggregation、selection、
   design、metrics、models、io、cli 及相关测试、`pyproject.toml`、`uv.lock`、`.gitignore`。
6. 只读检查第 3 节列出的 D4/D2 正式产物、各自 `SHA256SUMS`、receipt 和 verifier。
7. 查找现有 `reporting`、slides、模板、字体和可复用资产；不存在时才新增，不要假定旧占位 CLI
   已实现。调用 workspace dependency loader 确认实际 Node/Python/LibreOffice/渲染工具后再定实现。

先运行 `git status --short --branch`、branch、HEAD、`origin/main` 和最近提交，检查是否有后续提交
或用户改动。不得 reset、clean、stash、checkout 覆盖或删除既有文件。下列是编制本文时的现场
基线，新对话仍须重新核对：

- 分支 `main`；HEAD 与 `origin/main` 均为 D4 收口提交
  `e9322821f5986f6939065b911a396b84f2981af1`。
- D4 统计协议冻结提交为 `79976982a3a438ffe13b596ea4389d3645d8847a`；不得改写。
- `DEVLOG.md` 有允许保留的未提交 D4 最终 commit/push 回执；继续追加，不丢弃。
- 根 `DEFENSE-MVP-E0-HANDOFF-v01.tar` 及 `.sha256` 未跟踪，禁止暂存；`data/raw`、`artifacts`、
  正式答案、private mapping、媒体和会话目录均不得进 Git。
- D5 文件、reporting/slides 模块与 D5 正式输出在该快照下不存在。
- 最后一次全仓回归为 250 passed、Defense 147 passed、D4 31 passed；D5 完成时必须用最终源码
  重跑要求的测试，不能借用历史数量。

首次向用户只需简短报告：D4 是否仍完整、D5 已有/缺少什么、工作树或事实身份是否冲突、准备
从哪个里程碑开始。不要重新解包、评分、选择、启动标注服务、读取原始 notes 或创建录屏。

## 3. D5 唯一正式事实源与身份锁

D5 的首要事实源是唯一 D4 根 `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/`。至少核对：

| 输入 | SHA-256 |
|---|---|
| `aggregate/SHA256SUMS` | `17cd49237c975669c45e3cad6591db013333d6ba279f33660b6d2b3839e663d7` |
| `analysis/SHA256SUMS` | `5954d64759e1b1310b7e752d96b223140a1b7a8a873cf70e375b42ce6d25d37b` |
| `analysis/summary.json` | `a329396cddbbe0eaca66430c7df0743c6e16c885f181f4fd90c49ab7e7326e17` |
| `analysis/main-table.csv` | `8948b6807301e72df61bac749b628409f5b48e33df347895ebd699616819d968` |
| `analysis/agreement.csv` | `fc4ddb4a03e92d34781c01d7141233375ec43c86d3874ecaff4b394dec18c492` |
| `analysis/bootstrap.jsonl` | `18ad2f59cc3d97317406d0114a70ebf5eb0e3e58fa39aeb03c9e21b548f9526a` |
| `analysis/bt.json` | `21e8967a5c20d00d9b267d58ce52213f1e817b7b13ba753799d75a20781af791` |
| `analysis/costs.json` | `12bb28c826e9bf6db5c810d7bb07791b5dcc6d3d2c76a1a42cf18c5607f7ecf1` |
| `analysis/failure-cases.json` | `b391905c91cc9b0f6b19a517d8489e88dd461e1f30e558ac16c21e46a220ae03` |
| `verification.json` | `bcb34778eb9370e062da72472756de9fec9b99663c6f55d2e0a7677da405183f` |

开始 D5 实现前，先检查 D4 `verification.json` 为 `passed`，42 = 32 `human_pair` + 10
`automatic_tie`、family 28/14、7 clusters、agreement n=32、bootstrap 2,000、BT `ok`。在正式
D5 运行前调用现有 `verify-analysis` 到一个新的系统 Temp no-replace 文件，或使用等价库入口
完整复算，并核对临时回执与正式回执的内容身份。不要覆盖 D4 的 `verification.json`。

D5 只读关联 D2 正式根 `artifacts/defense_mvp/DEFENSE-MVP-v01/`，用于方法/指标说明、成本、
确定性案例解析和媒体路径，不重新计算事实。至少核对：

| 输入 | SHA-256 |
|---|---|
| `ingest/normalized-manifest.json` | `b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46` |
| `ingest/SHA256SUMS` | `c8eca842c9734ad8be85589bc928517000371051f86eb33909094ccdf676d1f2` |
| `metrics/metrics.jsonl` | `c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac` |
| `metrics/SHA256SUMS` | `fd947a0d31be63b73e38c9e75e7404c20d4412c62018de97141bb53b3b085c0d` |
| `design/design.json` | `891ee8b0d75acf5c825fd01d529d545f12a7fb1b72a4310364a805d8d6cd1ff5` |
| `design/SHA256SUMS` | `a1d41b96454a41a3693bfe210cbc58339c9e85490a815db45a7e482a45198910` |
| `selection/comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| `selection/selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |
| `selection/SHA256SUMS` | `a94929c3bf7c3b716ba0e59f468156ea0855b8a8b23a7657df2039705c5b400d` |
| `configs/defense_mvp/pilot.yaml` | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |
| `configs/defense_mvp/analysis-v1.yaml` | `9b29f1fad47b35ff7ae75b928e1811b98347aec8c7e2fe175cf09a7f1a283fa0` |

使用内部 manifest/verifier 继续验证文件集合、相对路径、candidate/media checksum 和关联关系，
不能把上表摘要当作完整验证替代。任何 SHA、计数、角色或唯一根不符都硬失败；不得用复制、
改锁、手工抄数或跳过 verifier 的方式接受。D5 产物绑定实际输入 SHA 和 source commit。

## 4. 冻结的事实与可说结论

D5 的文字、表格、图和 slides 必须由 D4 machine-readable 事实生成。可以格式化、四舍五入和
解释，但不可手工维护第二套数字。报告事实注册表至少保留原始精度、显示精度、单位、来源文件、
JSON/CSV 路径和 SHA；公开 Markdown、CSV、SVG/PNG、slide 数据和讲稿中的数值都能反查。

### 4.1 样本、分母与主结果

- 真实候选共 50：7 个定量 sample × 5 candidate = 35 个完成 F/P/T/Q 评分；3 个对象转换
  sample × 5 candidate = 15 个仅作 `qualitative_only` 能力边界，不进入主胜率。
- 三种选择方法必须同时出现：N=1 baseline、equal-linear N=4、constrained Pareto/max-min N=4；
  N=2 的 26 次 Pareto fallback 是工程事实，不是 D4 两个正式盲评 family 的第三个比较组。
- 正式聚合为 42 个唯一 comparison，不是 84 条独立人答；32 个人工双人聚合 + 10 个共享
  automatic tie。自动平局按 family 为 6/4，不进入 agreement/kappa。
- Proposed N=4 vs N=1 overall：W/L/T/U = 5/2/17/4，n=28，tie-aware 0.554，decisive
  0.714，7-cluster 2,000 次 bootstrap 95% CI [0.482, 0.643]。
- Proposed N=4 vs Linear N=4 overall：2/2/9/1，n=14，tie-aware 0.500，decisive 0.500，
  95% CI [0.357, 0.643]。
- 五字段明细直接来自 `main-table.csv`；tie 与 uncertain 在原始计数/图例中始终分开。不要把
  decisive rate 作为主胜率，不排除 automatic tie 或 uncertain 来制造更强结果。

### 4.2 一致性、BT、成本与局限

- overall agreement 14/32 = 0.438，nominal Cohen's kappa = 0.164；五字段 exact agreement
  7/32 = 0.219。其余字段从 `agreement.csv` 派生；四类 canonical 值不得折叠。
- BT 只使用 overall 的 11 条 decisive 边；状态 `ok`。ability 为 Proposed N4 0.305430、
  Linear N4 0.305430、N1 -0.610860。必须同时写明边少、估计脆弱、Proposed 与 Linear 相同；
  不得把它包装为稳定总体排名。
- E0 历史 50 候选 runtime 12413.711 s、报告过的 peak VRAM 最大 22476 MB；D2 metrics
  27.671 s / 50 = 0.553 s/candidate；D2 selection timer 为 `unavailable`；D4 compute 0.430 s。
  A/B current-view server elapsed 2018.096/3138.452 s 不是主动观看时间或精确工时。
- 只有两位评审且一位是开发者参与者；同机配合式盲评不是双盲。只有 7 个 cluster，CI 宽；
  agreement/kappa 较低；CPU F/P/T/Q 是代理；15 个对象转换候选没有定量分数。

### 4.3 叙事红线

报告主结论应保持以下含义：**约束式 N=4 相对 N=1 有描述性正向点估计，但区间跨 0.5；相对
线性 N=4 没有观察到差异。当前证据不足以宣称显著或稳定优势，工程贡献主要是可复现的
多目标选择、盲评、统计和审计闭环，并诚实暴露代理指标与小样本边界。**

不得使用“显著提升”“证明优于”“达到 SOTA”“普遍有效”“双盲”“42 条独立真人样本”或
“CPU 指标理解语义”等无证据表述。不得做未预注册显著性检验、p-value 钓鱼、事后子组或只报
decisive 子集。可以写“描述性”“点估计”“未观察到差异”“证据不充分”“在本 7 个任务上”。
如果机器产物与上述数字冲突，以身份验证失败处理，不按本文数字覆盖机器事实。

## 5. 先冻结的 D5 报告协议

新增版本化 `configs/defense_mvp/report-v1.yaml`，协议名建议 `defense-report-v1`。具体 schema 可
调整，但必须在打开正式案例媒体前固定并测试：输入身份、输出文件、标签/显示精度、颜色/字体、
图尺寸、事实注册、案例选择键、帧抽取、slide 页数/顺序、讲稿语速和隐私规则。

### 5.1 表格与图

至少生成：

1. `main-results.csv`：两个 family × 五字段的 W/L/T/U、total、tie-aware、decisive、CI、
   valid/invalid bootstrap；与 D4 主表精确一致。
2. `agreement.csv`：五字段 agreement/kappa 和 exact 五字段 agreement；manual n=32。
3. `costs.csv`：value、unit、status、语义、来源和 SHA；`unavailable` 不填估算值。
4. overall CI 图：两个 family 的 tie-aware 点估计与 95% CI，固定 0.5 参考线，标 n=28/14、
   7 clusters、2,000 bootstrap，并在标题/注释中写“描述性”。
5. W/L/T/U 组成图：两个 family 的四类数量或比例，tie 和 uncertain 使用不同颜色/纹理并直接标数。
6. agreement/kappa 图：五字段 observed agreement 与 kappa，注明只有 32 个 manual comparison；
   不把不同量纲堆成误导性排名。
7. 系统流程图：只表达 ingest→F/P/T/Q→N=1/2/4→三方法选择→双人盲评→D4统计→D5报告，
   不伪造性能数据。

图表必须同时生成可审计 SVG 和 slides 使用的 PNG；使用色盲友好配色、清晰图例、足够对比度，
中文字体采用明确 fallback。数值轴、分母和参考线固定在配置中。禁止 3D、截断轴制造差异、
把 CI 当显著性检验或省略不确定/平局。PNG 尺寸、透明/白底策略和导出 DPI 固定并测试。

### 5.2 确定性案例选择与媒体

在查看正式案例视频/帧之前固定以下语义，并在 fixture 中验证：

- 成功案例：`proposed-n4-vs-n1` 中 `source=human_pair`、aggregated overall 为 Proposed `win`，
  按 `(family, sample_id, trial_id, replicate, comparison_id)` 升序取第一项。
- 失败案例：同一 family 中 overall 为 Proposed `loss`，按同一稳定键取第一项；必须能反查
  D4 `failure-cases.json`。
- 不确定案例：同一 family 中 overall 为 `uncertain`，按同一稳定键取第一项；必须能反查
  D4 `failure-cases.json`。
- 能力边界：从 3 个 `qualitative_only` sample 按 `sample_id` 升序取第一项，只说明未量化的
  对象转换边界，不赋予 win/loss、不进入 D4 主结果。

如果某类别不存在，输出显式 `unavailable` 和原因，不换成更“好看”的案例；当前 D4 已验证计数
应使前三类存在。为全部 D4 预冻结失败案例保留机器可读索引和总数 9，但公开报告重点展示上述
固定样例，不浏览 notes 后换例。案例公共标签使用“成功/失败/不确定/定性边界案例 1”等，不在
Git 文档暴露 comparison_id、private mapping、entry token、annotator 信息或原始五字段载荷。

每个定量案例页以一致布局展示输入、Proposed 和 comparator；方法标签在 D5 可以揭示。固定从
已验证帧序列抽取 first、1/3、2/3、last 四个归一化位置，明确舍入规则；所有方法使用相同索引。
可展示 mask 轮廓，但不得改变像素、挑单帧替代整段结论或只展示 Proposed。保存内部 trace
manifest：公共 case label→D4 comparison→D2 role/candidate→媒体 SHA→帧索引；trace 留在忽略的
artifact，公开页只保留非敏感来源摘要。不要把 MP4、原始 frames 或案例 contact sheet 提交 Git。

## 6. 报告、Slides 与讲稿结构

### 6.1 Markdown 报告

`DEFENSE_REPORT.md` 至少包含：摘要/一句话结论、问题与范围、50 候选及 35+15 分工、系统流程、
F/P/T/Q 与约束式选择、N=1/2/4 和三方法、双人盲评/聚合协议、正式主结果、agreement/BT、
确定性案例、成本/复现、威胁与局限、结论与后续。正文引用生成表/图和来源 SHA；主结果先写
W/L/T/U 与 all-42 tie-aware，再写 decisive 诊断。15 个对象转换任务只能出现在能力边界。

Markdown、CSV、SVG/PNG 和案例页由 reporting 代码从 verified D4/D2 输入生成，不手工抄数。
如需可编辑的人工叙事模板，使用受控模板 + machine fact registry；verifier 必须证明展开后的所有
数字和链接一致。报告中的案例结论限于可见现象与正式聚合，不根据评审 notes 补故事。

### 6.2 8–10 页中文 Slides 初稿

建议固定 10 页；若版式需要 8–9 页可合并，但不得删主结果、失败案例或局限：

1. 题目与一句话结论；
2. 问题、10 个 sample / 50 个真实候选及 35+15 范围；
3. 系统流程与 checksum/身份审计；
4. F/P/T/Q 代理指标及适用边界；
5. 线性补偿问题与约束式 Pareto/max-min、N=1/2/4；
6. 两人盲评、32+10=42、位置去偏与保守聚合；
7. 两个 family 主结果、W/L/T/U、CI 和不夸大结论；
8. 固定成功/失败/不确定案例（空间不足时将定性边界放报告附录）；
9. agreement、BT、成本、复现与局限；
10. 结论：描述性信号、未观察到线性优势、工程贡献和下一步。

每页只保留一个核心信息，标题应写结论而不是泛化栏目；所有数字由 `slide-data.json` 或等价
生成事实输入绑定，图表复用 D5 生成资产。脚注给出 n、口径和必要来源，不塞满 SHA。禁止把
wide CI 用绿色“胜利”视觉包装。PPTX 初稿需渲染为逐页 PNG，检查中文字体、裁切、重叠、比例、
图片拉伸、对比度和投影可读性；至少做一次全页 contact sheet 检查，并对有问题页面迭代。

### 6.3 5–7 分钟讲稿和录屏方案

`DEFENSE_SCRIPT.md` 与 slides 一页一节，建议配时：45 秒问题、60 秒数据/系统、90 秒指标/算法、
60 秒盲评、90 秒结果/案例、45 秒工程亮点/局限/结论。配置固定中文有效字符估算语速及允许区间，
静态检查估算总时长 5–7 分钟；讲稿不新增 slides/报告之外的数字或强结论。

D5 只输出 `RECORDING_PLAN.md`：60–90 秒依次展示冻结配置/checksum verifier、盲评界面或安全截图、
三方法选择、自动报告和主表，并注明现场 demo 失败时的降级。不得实际启动录制、生成正式视频、
做两次计时演练或建立最终交付 manifest；这些属于 D6。

## 7. 实施顺序、CLI 与产物

建议里程碑；每个完成后立即记录 DEVLOG：

1. **D5.0 现场/输入预检**：核对 Git、D4 verifier/SHAs、D2 manifests、工具/字体/模板；不改旧事实。
2. **D5.1 施工方案与展示协议**：完成 `D5_CONSTRUCTION_PLAN.md`、`report-v1.yaml`、事实/叙事、
   图表、案例选择、帧规则、slide 结构和发布边界；在打开正式案例媒体前记录 gate。
3. **D5.2 报告工程**：实现严格输入模型、事实注册、表格/图、案例 trace/page、no-replace 输出和
   verifier；用 synthetic/tiny fixture 覆盖，不运行真实 D5。
4. **D5.3 Slides/讲稿工程**：按 presentations skill 生成 PPTX、渲染/视觉 QA、讲稿时长检查和
   录屏方案；先在 fixture/synthetic 资产验证布局。
5. **D5.4 正式草稿运行**：记录计划后，只对唯一 verified D4/D2 输入运行一次新的
   `artifacts/defense_mvp/DEFENSE-MVP-D5-v01/`；失败目录保留诊断，机械 bug 修复补测试后使用
   v02，不覆盖 v01，不改 D4 事实或案例规则。
6. **D5.5 验证发布**：复核全部数字/链接/图片/slide 页面、独立 verifier、最终回归、回执、
   总计划状态、审计 commit 和普通 push。

总方案中的旧 `defense report` 只是占位。建议实现以下语义；参数可按现有模型收敛，但正式入口
必须接收完整目录/manifest 和配置，不能只吃手写摘要：

```text
defense report --aggregate <d4-aggregate-dir> --analysis <d4-analysis-dir> --d4-verification <file> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --config <report-v1.yaml> --output <new-dir>
defense verify-report --report <d5-dir> --aggregate <d4-aggregate-dir> --analysis <d4-analysis-dir> --d4-verification <file> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --config <report-v1.yaml> --output <new-file>
```

Slides 生成可以是 `defense slides` 子命令或由受测脚本消费 `slide-data.json`；无论接口为何，
必须保留输入/config/source identity、命令、依赖、页数、文件 SHA 和 render/QA receipt。所有稳定
数据输出使用 UTF-8、排序键、有限数值和固定列顺序；写入采用 staging + no-replace，失败诊断
保留，不自动删除。PPTX/PDF 的内部时间戳可能不稳定时，不伪称字节级可复现；固定语义输入，
保存实际 SHA，并由 verifier 检查页数、文本/数字资产与渲染，不用二进制哈希代替语义验证。

建议正式输出：

```text
artifacts/defense_mvp/DEFENSE-MVP-D5-v01/
  report/
    DEFENSE_REPORT.md
    report-data.json
    tables/{main-results.csv,agreement.csv,costs.csv}
    figures/{system-flow,overall-ci,outcomes,agreement}.{svg,png}
    cases/{index.html,case-index.json,case-*.html,media/...}
    slide-data.json
    input-manifest.json
    report-receipt.json
    SHA256SUMS
  slides/
    DEFENSE_MVP_D5_DRAFT.pptx
    rendered/slide-*.png
    contact-sheet.png
    slides-receipt.json
  script/DEFENSE_SCRIPT.md
  script/RECORDING_PLAN.md
  verification.json
```

文件名可按实现调整，但语义必须齐全。tracked 文档建议包括：

- `docs/defense_mvp/D5_CONSTRUCTION_PLAN.md`；
- `docs/defense_mvp/DEFENSE_REPORT.md`（与正式 artifact 报告有可验证的生成/身份关系）；
- `docs/defense_mvp/DEFENSE_SCRIPT.md`、`RECORDING_PLAN.md`；
- `docs/defense_mvp/D5_IMPLEMENTATION_RECEIPT.md`；
- 必要的非敏感 slides outline/图表和更新后的总施工方案。

代码放 `src/defense_mvp/`，测试放 `tests/defense_mvp/`。正式 artifacts、PPTX、PDF、案例媒体、
contact sheet、MP4/frames 不进 Git；可提交生成代码、配置、报告 Markdown、讲稿、录屏方案和小型
非媒体 SVG/PNG/CSV，但先检查无绝对路径、原始答案或隐私载荷。不要实现 D6 顶层最终 `verify`、
录屏或最终交付 manifest。

## 8. 测试与验收矩阵

正式 D5 运行前至少用 synthetic/tiny fixture 覆盖：

- **输入门禁**：D4 verification 非 passed、aggregate/analysis 混用、inventory/SHA 漂移、未知文件、
  42/32+10/28+14/7/2000/BT 状态漂移、D2 role/media/candidate 断链全部拒绝。
- **事实注册**：D4 JSON/CSV 路径→原始精度→显示精度→Markdown/CSV/slide data 一致；计数守恒、
  CI 顺序、undefined/unavailable、单位和来源 SHA；禁止手工常量覆盖机器值。
- **叙事守卫**：报告和讲稿包含“描述性/CI 跨 0.5/未观察到线性差异/低 agreement/两人/7 clusters/
  代理边界”，拒绝或人工审查无证据的显著、证明、SOTA、双盲、84 独立答案等表述。
- **图表**：SVG 可解析、PNG 可解码且尺寸固定、两个 family/四 outcome/五 agreement 字段完整，
  reference line、n/CI/legend 存在；tie 与 uncertain 不合并；缺字体/渲染失败硬失败。
- **案例**：四类固定选择、稳定排序、输入顺序扰动不变、缺类别显式 unavailable、D4 failure 索引
  反查、角色方向、四个固定帧位置、同帧对齐、媒体 SHA；不读取 notes，不复制原始 answer payload。
- **Slides/讲稿**：8–10 页、页序/标题/事实引用固定，PPTX 可打开，全部页面渲染且尺寸一致，
  无溢出/重叠告警；中文有效字符估时 5–7 分钟，讲稿数值为事实注册表子集。
- **输出**：staging 失败、no-replace、receipt/checksum、输入/config/source drift、tamper、未知文件
  后 verifier 硬失败；跨路径重建稳定数据文件一致，时间/环境字段隔离。
- **隐私/发布**：Git diff/staged 文件无 tar/sidecar、artifacts、PPTX/PDF、MP4/frames/contact sheet、
  formal exports、private mapping、token、notes、annotator 姓名、逐题原始答案或机器绝对路径。

正式数据运行后逐项核对：D4/D2 输入 SHA 未变；report 的所有主数字与 D4 精确一致；四个案例均
按冻结规则选择；所有 figure 两种格式存在；每个图表和公开案例链接可解析；PPTX 8–10 页且每页
成功渲染；讲稿估时 5–7 分钟；D5 output inventory 无未知文件；verifier 为 passed。对报告、slides
和讲稿逐条做 truthfulness review，不用“生成成功”代替内容与视觉验收。

最终源码状态运行 D5 定向测试、Defense 全测试、全仓 pytest、compileall、CLI/config smoke、
D3/D4 verifier、D5 verifier、冻结输入前后 checksum、Markdown/CSV/SVG/PNG/PPTX/render 检查、
`git diff --check` 和 staged path/binary/size/sensitive-data guard。记录实际数量、耗时和退出码；
历史 31/147/250 不能代替本轮结果。

## 9. 异常处理、DEVLOG 与审计发布

- 正式案例媒体开启 gate 必须在 DEVLOG 记录：计划/config、固定选择/帧规则、fixture 测试、D4/D2
  输入 SHA 和下一条命令。此后不因页面难看或结果不强而换例；只允许统一版式修复。
- 第一次正式 D5 运行的输出或失败目录必须保留。机械 bug 给出与结果无关的复现、fixture 回归和
  影响范围，使用 v02；不能覆盖 v01 或改 D4 结果。
- 视觉 QA 可反复调整排版、字体、字号、间距和对比度，但不能改数据、分母、案例、图轴或结论
  方向。任何内容变更与纯版式修复在 DEVLOG 分开说明。
- 严格遵守根 `AGENTS.md`：每完成一个可独立验证的编辑、测试、决策、失败、正式运行、视觉 QA、
  验证或发布步骤，立即追加 DEVLOG，包含时间、环境、步骤 ID、命令/配置、结果、产物和下一步。
  不能最后批量补写，也不能在记录前宣称完成。
- 至少建立一个 D5 实现/草稿完成审计提交并普通 push `main`；如把施工协议/案例 gate 与正式运行
  分成两个提交，先后都普通推送。每次先 fetch 并核对远端；显式 allowlist 暂存，不用
  `git add .`；检查 NUL、大小、whitespace、二进制和敏感载荷。
- 禁止 force-push、重写历史或提交 tar、sidecar、data/raw、artifacts、PPTX/PDF、媒体、frames、
  contact sheet、formal exports、private mapping、session/entry token、notes 或逐题答案。最终 push
  回执可作为唯一未提交 tracked DEVLOG 增量保留，避免递归回执提交。

最终更新 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md` 为 D5 报告/slides 初稿完成、可以进入 D6、
D6 尚未启动；新增 `D5_IMPLEMENTATION_RECEIPT.md`，记录输入/输出 SHA、事实/图/案例/slide/讲稿
验收、真实测试数、视觉 QA、commit/push 和诚实局限。回执不复制逐题答案、notes 或私有映射。

最终向用户用中文简洁报告：

- D5 实现、正式输入和 no-replace 输出身份；
- 报告/图表/案例/slides/讲稿与录屏方案的位置；
- 两个 family 的主结果及低一致性/小样本/代理边界，不夸大；
- 实际测试、verifier、渲染/视觉 QA、commit/push 证据；
- D5 是否完成、D6 只剩哪些冻结/录屏/演练任务。

结束时明确没有自动开始 D6、没有录屏或建立最终交付 manifest、没有修改 D1–D4 事实源，也不要
声称整个 Defense MVP 已完成。
