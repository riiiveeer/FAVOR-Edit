# D4 聚合与统计分析：新对话施工提示词

交接快照：2026-09-04。以下是给承接 agent 的完整任务指令；用户让你阅读并执行本文时，
按本地施工任务处理，不只复述方案。本文是启动导航，不替代对真实工作树和封存输入的核对。

## 1. 任务、授权与停止点

请在 `D:\lab idea` 承接 Defense MVP，完成 D4 正式双人标注聚合与统计分析工程。
项目题目为“基于约束式多目标排序的指令视频编辑候选选择与盲评系统”，目标交付日为
2026-09-08。D1/D2 已完成真实输入接收、CPU 评分、N=1/2/4 设计和三方法选择；D3 已完成
本地盲评工程与两位真人的正式标注，最终验证为 `formal/dual/complete`。

先核对现场，把 D4 的统计模型、输入身份、公式、异常状态、CLI、输出和测试矩阵写入
`docs/defense_mvp/D4_CONSTRUCTION_PLAN.md`。然后先用 synthetic/tiny fixture 实现和冻结协议，
通过测试并建立**真实分析前的审计提交**；只有此前置冻结完成，才读取两份正式
`answers.jsonl` 并运行一次 no-replace 真实分析。普通工程选择自行决定，不反复询问；只有
输入身份冲突、必须改变下述统计协议、无法保留的工作树冲突或必要权限缺失时才停下来说明证据。

沿用根 `AGENTS.md` 的 Defense MVP 本地 CPU 开发、DEVLOG、审计提交和普通推送 main 授权。
默认单 agent 执行，不创建额外对话、计划任务或远程工作。本阶段禁止连接学校服务器、读写
DATA4、运行 GPU/模型、修改 sealed E0、D1/D2/D3 事实源、重做人评或改写正式答案。

D4 可以读取已经验证的正式答案并报告诚实统计；不得先看结果再调聚合规则、分母、字段、
bootstrap seed/次数、选择阈值或案例筛选规则。正结果不是验收条件，负面、平局、不确定、
标注分歧、不可识别的 BT 排名和宽置信区间都必须保留。

本次停止点是：**D4 聚合/分析代码和冻结配置通过测试；真实 A/B 封存输入生成一份可复现、
验证通过的 no-replace D4 输出；第一版机器可读主表与失败案例清单完成；D4 回执和审计发布完成，
可以进入 D5 报告/slides 制作。** 不自动继续 D5，不制作正式 slides/录屏，不修改 D3 原记录。

## 2. 首轮核对：以现场为准，不重做 D1–D3

按顺序阅读和核对：

1. `D:\lab idea\AGENTS.md` 及适用目录级规则。
2. 本文件及 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md`，重点读取 6.5、7、8、9 月 5 日 D4。
3. `docs/defense_mvp/D3_FORMAL_ANNOTATION_RECEIPT.md`、`D3_IMPLEMENTATION_RECEIPT.md`、
   `D2_IMPLEMENTATION_RECEIPT.md`；D3 工程期“正式答案为0”是历史快照，不是当前状态。
4. `DEVLOG.md` 末尾及 D3-B-CLOSE / D3-A-TO-B 记录；不要一开始输出整个长文件。
5. `src/defense_mvp/` 的 annotation_models、annotation_bundle、annotation_store、
   annotation_export、selection、design、metrics、models、io、cli 及相关测试、pyproject/uv.lock。
6. 只读检查下述正式封存、D2 selection/metrics/design 及各自锁和 SHA 清单。

先运行 `git status --short`、branch、HEAD、origin/main，检查是否有后续提交或用户改动。
不得 reset、clean、stash 或覆盖既有改动。下列是编制本提示词前的 D3 状态基线；发布本提示词
产生的新文档提交属于预期前移，新对话仍须以当时的真实工作树和远端为准：

- 分支 `main`；D3 状态同步基线为 `28be57b2098263549c28901af27bd9aa37b6f03a`。
- D3 正式收口提交 `6aeeeecf76cc49addd54cb12771bc4fb052a5169`，状态同步提交 `28be57b...`。
- `DEVLOG.md` 有允许保留的未提交最终 push 回执；继续追加，不丢弃。
- 根 `DEFENSE-MVP-E0-HANDOFF-v01.tar` 及 `.sha256` 未跟踪，禁止暂存；data/raw、artifacts、
  正式答案、private mapping、媒体和分析运行目录均不得进 Git。
- 最后一次代码状态回归为 Defense 116 passed、全仓 219 passed；后续两个提交仅改文档。
  D4 完成时仍必须用最终源码重跑要求的回归，不能借用历史结果。

首次向用户只需简短报告：D3 是否仍完整、D4 已有/缺少什么、发现的工作树或协议冲突、
准备从哪个里程碑开始。不要重新解包、评分、选择、转换视频或启动标注服务。

## 3. D4 唯一正式输入与身份锁

正式根：`artifacts/defense_mvp/DEFENSE-MVP-D3-v01/`。只接受：

| 输入 | 路径 | SHA-256 |
|---|---|---|
| D3 formal bundle | `formal-bundle/bundle.json` | `c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6` |
| A 封存清单 | `formal-exports/annotator-a-v01/SHA256SUMS` | `ad796e6aca1991b72f9820d2eee807c4fec89a9c80e9574ee1aae8ed3ffcae85` |
| B 封存清单 | `formal-exports/annotator-b-v01/SHA256SUMS` | `91e6a169b81ef825e29e808a8777c264be55b5f88d5eed8ab9f82d5afc936a3a` |
| D3 dual verifier | `formal-exports/dual-verification-v01.json` | `280b099845be84936021e3bffa9e4f69ab24749a7833f03ea3909f18737bd357` |

开始开发前可核对文件结构、schema 和 manifest，但在聚合协议/fixture/测试冻结前，不读取或
汇总两个 `answers.jsonl` 的具体答案值。真实运行前必须调用现有 `verify-annotations` 或等价
库入口，得到 `formal/dual/complete`、64 条真人确认、10 条共享自动平局、A/B 各42/42、
缺题0，并核对上表四个摘要。任何不符都硬失败，不通过修改锁、复制缺题或丢弃记录来接受。

D4 还需只读关联：

- `artifacts/defense_mvp/DEFENSE-MVP-v01/selection/`（315 selections、42 comparisons及锁）；
- `.../design/`（35 trial、7 个正式定量 sample、N=1/2/4 平衡设计）；
- `.../metrics/` 与 `.../ingest/normalized-manifest.json`（只用于关联、CPU 分数/成本/案例元数据）；
- `configs/defense_mvp/pilot.yaml`，SHA
  `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae`；
- `selection/comparisons.json` SHA
  `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb`；
- `selection/selection-lock.json` SHA
  `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2`。

使用现有 verifier 继续验证全部内部清单和关联关系，不把三个显式 SHA 当作完整验证替代。
D2 的 26 次 Pareto fallback 全在 N=2，应按既有成本/能力事实保留，不能在 D4 修选择算法。

## 4. 先冻结的 D4 统计协议

新增版本化 `configs/defense_mvp/analysis-v1.yaml`（具体 schema 可调整，但语义必须覆盖本节），
协议名建议 `defense-analysis-v1`。在真实答案读取前，配置、公式和测试必须进入一个前置审计提交。

### 4.1 规范方向、连接和逐题事实

- 以 D3 记录中的 canonical `X/Y/tie/uncertain` 为分析值，不能直接把屏幕 A/B 跨评审合并。
- 服务端记录、private mapping 和 comparisons 必须互相验证；客户端字段、文件顺序和 position
  不能替代 `comparison_id` 身份连接。
- A/B 两份人答应具有相同的 32 个 manual comparison ID；自动平局的10个 ID与manual不相交。
- 根据冻结 comparisons/selection 解析 X/Y 对应的方法、N、family、sample、trial；禁止用
  candidate 文件名或看到结果后手写方向。
- 每项聚合都保存来源（`human_pair` 或 `automatic_tie/media_identity`）及输入摘要，
  但自动平局不得伪造 annotator、confidence、notes、timestamp 或人类劳动时间。

### 4.2 双人分歧规则（五字段逐字段应用）

字段固定为 `overall`、`faithfulness`、`preservation`、`temporal_consistency`、`visual_quality`。
对每个 manual comparison 和每个字段执行确定性规则：

| A值 | B值 | 聚合值 |
|---|---|---|
| 相同的 decisive（X或Y） | 同值 | 该 decisive 值 |
| decisive | tie（任一顺序） | tie |
| tie | tie | tie |
| X | Y（任一顺序） | uncertain |
| 任一 uncertain | 任意值 | uncertain |

实现时用穷举的 4×4 对称表或等价严格逻辑测试所有16组合，不以第三人裁决，不在揭盲后改判。
10项 automatic comparison 对五个字段均生成 `tie` 聚合事实，系统来源只保存一次。

最终聚合为42个 comparison：32个人工双人聚合 + 10个系统自动平局。不要把10项自动平局
按两位评审复制，不能声称84条真人答案。原始双人分歧仍在审计输出中可计数，但不要把
notes 或逐题真人原始载荷写进 Git 文档。

### 4.3 一致性统计

- 一致性只使用32个双方实际作答的 manual comparison；自动平局不进入双人一致性/kappa。
- 每字段报告 4 类 canonical 混淆矩阵、observed agreement、nominal Cohen's kappa、各类边际。
- `exact agreement` 定义为同一题五字段的 canonical 向量全部相同；confidence/notes/time不参与。
- 另可报告逐字段 agreement；不得将 X/Y 统一折成“decisive”来抬高主 agreement/kappa。
- kappa 分母退化（expected agreement=1）、无样本或非有限值时输出明确 `undefined` 和原因，
  不填0或1。不要把只有两位评审的小样本 kappa 包装成稳定人口参数。

### 4.4 胜率、分母和原始计数

两个固定 family：28项 `proposed-n4-vs-n1`（Proposed N=4 vs N=1，含6自动平局）；14项
`proposed-vs-linear-n4`（Proposed N=4 vs Linear N=4，含4自动平局）。先从冻结角色解析
Proposed 在 X/Y 哪一侧。

对主字段 `overall` 及其余四字段分别保存 wins、losses、ties、uncertain、total，并保证求和
等于 family 固定分母。主指标至少报告：

- tie-aware win rate = `(wins + 0.5 * ties + 0.5 * uncertain) / total`；
- decisive win rate = `wins / (wins + losses)`，无 decisive 时为 undefined；
- tie rate、uncertain rate 及全部原始数量；
- 42项全量（含自动平局）为正式主表口径；manual-only 可作为明确标注的诊断，不能替代主表。

tie 和 uncertain 虽同记0.5，只在 tie-aware 数值中等权；原始类别必须始终分开报告。
不得静默排除 uncertain、只挑 decisive、改用评审级伪重复分母或把五字段当独立样本扩大 n。

### 4.5 Bradley–Terry

- 方法节点固定来自冻结角色：Proposed N=4（`constrained-pareto-n4`）、N=1 baseline
  （`constrained-pareto-n1`）、Linear N=4（`equal-linear-n4`）；先验证实际角色集合。
- 只把 `overall` 的聚合 decisive X/Y 转成方法胜负边；tie、uncertain、自动平局不进 BT 边。
- 输出中心化 ability（和为0）及确定性拟合诊断。实现可用本地 CPU 的稳定 MM/Newton 方法，
  不为了得到排名添加未声明伪计数、结果依赖正则或手工破平。
- 无 decisive、某个固定比较 family 无 decisive、无向方法图不连通、方向胜图导致完全分离、
  未收敛或非有限时，输出 `insufficient_connectivity` / `separation` / `not_converged` 等状态和
  边计数，不伪造有限排名。若使用数值容差、迭代上限或参考约束，写进analysis配置并测试。
- BT 用于描述三方法聚合偏好，不训练选择器，不回写 CPU 分数或 D2 选择。

### 4.6 sample-cluster bootstrap

- cluster固定为 `sample_id`，正式主表cluster数必须为7；不是annotator、comparison或frame。
- seed `20260901`，迭代恰为2,000；固定并记录 RNG 实现/版本。
- 每次有放回抽7个 sample cluster，被抽中的sample携带其全部family/replicate题；重复抽中按倍数计。
- 至少对两个family的 `overall` tie-aware win rate 计算 percentile 95% CI；量化规则仍为
  win=1、loss=0、tie/uncertain=0.5。percentile使用2.5%/97.5%，quantile method固定为linear。
- 可为预先声明的其他字段输出诊断CI，但不能看到结果后挑字段；不做伪精确的评审级bootstrap。
- 保存2,000次原始bootstrap统计或可验证的紧凑等价产物及draw/config摘要，以便精确复跑。
- 若某次统计 undefined，保留有效/无效次数和原因；7个cluster的CI只描述小样本不确定性，
  不声称论文级显著性，不由CI是否跨0.5决定项目成败。

### 4.7 confidence、时间和成本

- confidence按评审分别和总体作描述性分布，不作答案加权，不用低confidence删题。
- annotation `elapsed_seconds` 是current-view服务器经过时间，含停顿/后台/恢复影响；仅按评审
  报告总和、median/IQR等描述并明确不是精确主动观看或人工工时。
- 从已有receipts/runstats只读提取：E0历史生成runtime/VRAM（若有可信来源）、CPU指标总时长/
  每候选时长、选择算法时长、N=1/2/4候选量和分析本身运行时间。每个成本值绑定来源文件/SHA。
- 缺失或无法同口径解释的成本输出 `unavailable` 和原因，不能估算、从文件mtime冒充或把
  D3重启前后经过时间相加包装为精确劳动成本。

## 5. 实施顺序、CLI 与产物

建议里程碑；完成每一项后立即记录 DEVLOG：

1. **D4.0 输入预检**：验证双人封存、SHA、角色/ID/42覆盖；只检查schema，不汇总真实答案。
2. **D4.1 协议冻结**：完成 `analysis-v1.yaml`、D4_CONSTRUCTION_PLAN、严格模型、公式和fixture；
   建立真实分析前的审计commit/push，保证后续不能按结果调规则。
3. **D4.2 聚合**：实现方向还原、16组合分歧表、自动平局一次性合并、no-replace审计输出。
4. **D4.3 分析**：agreement/kappa、rates、BT状态机、2,000 cluster bootstrap、成本/provenance。
5. **D4.4 真实运行**：对唯一冻结输入运行一次新的 `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/`；
   失败目录保留诊断，不覆盖、不换规则重跑。机械bug修复先记录、补测试，使用v02新目录。
6. **D4.5 验证发布**：生成机器可读主表/案例清单、验证器、回执、最终回归和审计push。

计划中的旧CLI是占位，不必照抄参数。建议使用更强的D3封存验证入口：

```text
defense aggregate --bundle <formal-bundle> --left <a-export-dir> --right <b-export-dir> --output <new-dir>
defense analyze --aggregate <aggregate-dir> --selection <selection-dir> --metrics <metrics-dir> --design <design-dir> --config <analysis-v1.yaml> --output <new-dir>
defense verify-analysis --bundle <formal-bundle> --aggregate <aggregate-dir> --analysis <analysis-dir>
```

如保留总方案里的 `--plan/answers.jsonl` 接口，也必须在库内先验证两个完整export目录及bundle，
不能只接受裸JSONL。所有输出走 staging + no-replace，保存输入清单、配置/源码/依赖、命令、
运行时间、SHA256SUMS和receipt。失败保留独立FAILED诊断或新实验ID，不覆盖旧输出。

建议真实输出：

```text
artifacts/defense_mvp/DEFENSE-MVP-D4-v01/
  aggregate/{aggregate.jsonl,agreement-input.json,aggregation-receipt.json,SHA256SUMS}
  analysis/{summary.json,main-table.csv,agreement.csv,confusion-matrices.json,
            bootstrap.jsonl,bt.json,costs.json,failure-cases.json,analysis-receipt.json,SHA256SUMS}
  verification.json
```

文件名可按模型调整，但语义必须齐全。`failure-cases.json` 使用**预先冻结的确定性规则**，例如
overall聚合为loss/uncertain、再按family/sample/comparison_id稳定排序；它是D5选材清单，
不在D4复制媒体、写解读或只挑有利案例。机器可读主表必须由事实产物生成，不手工抄数。

实现放在 `src/defense_mvp/`，测试在 `tests/defense_mvp/`；可复用已有纯hash/IO/严格模型工具，
不得修改 E1/E2 协议或D1–D3 cardinality。交付：

- `docs/defense_mvp/D4_CONSTRUCTION_PLAN.md`；
- `docs/defense_mvp/D4_IMPLEMENTATION_RECEIPT.md`；
- 更新 `docs/DEFENSE_MVP_CONSTRUCTION_PLAN.md` 的已实现CLI和D4状态；
- 必要的统计口径/机器字段说明。D5报告/slides/讲稿不在本轮。

## 6. 测试与验收矩阵

真实运行前至少使用 synthetic/tiny fixture 覆盖：

- **输入门禁**：practice、单人/同身份、bundle混用、SHA漂移、缺/重/多题、顺序变化、
  manual/automatic交叉、伪造自动平局、方向/角色/sample/trial不一致全部拒绝。
- **聚合**：五字段全部16种双人组合和对称性；按ID连接而非position；screen A/B翻转还原；
  自动平局只生成10条系统事实；最终32+10=42，原始输入不变。
- **一致性**：手算混淆矩阵/agreement/kappa；精确五字段agreement；类别边际；expected=1、
  空输入、全同/全不同等退化状态；证明自动平局不进入kappa。
- **rates**：两个family固定28/14，wins+losses+ties+uncertain=分母；tie/uncertain各0.5；
  decisive分母为0；manual-only和正式全量标签不混淆；X/Y角色交换不改变方法结论。
- **BT**：已知三节点小图、标签交换、无边、family缺边、无向不连通、完全分离、
  non-convergence/非有限；能力中心化和重复运行稳定。
- **bootstrap**：7 cluster、整cluster重采样、重复cluster倍增、固定seed/2000完全可复现、
  percentile linear手算fixture、undefined replicate保留；不得误按42题独立抽样。
- **成本**：来源/单位/摘要绑定，缺失明确 unavailable；annotation elapsed不标为active labor。
- **输出**：staging失败、no-replace、receipt/checksum、输入/配置/源码漂移、未知文件、
  tamper后verifier硬失败；不同路径复跑内容确定（仅允许显式时间/环境字段变化并单独处理）。
- **隐私/发布**：Git diff/staged文件不得含private mapping、入口token、原始逐题答案、notes、
  正式export、媒体或artifacts；公开统计只来自已验证聚合输出。

真实数据运行后逐项核对：42唯一聚合（32 human_pair+10 automatic）、两个family28/14、7 sample、
每字段计数守恒、manual agreement n=32、bootstrap恰2,000、全部非有限值有状态、BT诊断与边数一致、
所有输入摘要与本提示词/锁一致。不要用“程序跑完”替代这些不变量。

最终源码状态运行 Defense 定向测试、全仓 pytest、CLI smoke、compileall、真实输入/输出 verifier、
冻结输入前后checksum、`git diff --check` 与 staged path/binary/size/sensitive-data guard。
记录实际数量、耗时、退出码；历史D3的116/219不能代替本轮结果。

## 7. 防止结果驱动修改与异常处理

- 真实答案解封点必须在DEVLOG明确记录：前置配置/代码/fixture测试commit、输入SHA、命令、预期输出。
- 第一次真实运行的负面或失败统计目录必须保留。协议或口径在解封后原则上不改；机械bug需给出
  与结果无关的复现、fixture回归和影响范围，输出使用v02，v01保留。
- 不因win rate低、CI宽、kappa低、BT不可识别或案例难看而删题、换字段、改seed、改变
  uncertain/tie处理、调整D2阈值或重新标注。
- 禁止读取notes后挑规则；notes只可作为D5人工案例解释的受限输入，D4主统计不依赖notes。
- 不运行显著性钓鱼、多重未声明切片或事后子组；若输出exploratory诊断，必须预先列入配置并
  与主结果分开。
- 实际数据与fixture/mock严格分目录和provenance；mock结果不得进入正式主表。
- 不覆盖导出、不删除writer.lock/正式记录、不把草稿当答案、不根据mtime猜运行时间。

## 8. DEVLOG、提交与最终交付

严格遵守根 `AGENTS.md`：每完成一个可独立验证的编辑、测试、决策、失败运行、真实运行、
验证或发布步骤，立即追加DEVLOG，包含本地环境、步骤ID、命令/配置、结果、产物和下一步。
不能最后批量补写，也不能在记录前宣称完成。

至少两个审计发布点：

1. **真实分析前冻结提交**：analysis config、D4计划、模型/实现和完整fixture测试；普通push main。
2. **真实分析后完成提交**：只提交源码、测试、配置、文档和非敏感统计回执；普通push main。

每次先fetch并核对远端；显式路径allowlist暂存，不用 `git add .`；检查NUL/大小/whitespace和
敏感载荷。禁止force-push、重写历史或提交tar、sidecar、data/raw、artifacts、媒体、formal
exports、private mapping、session/entry token、原始答案/notes。最终push回执可作为唯一未提交
tracked DEVLOG增量保留，避免递归回执提交。

最终向用户用中文简洁报告：

- D4实现、真实输入和输出身份；
- 聚合计数守恒、agreement/kappa、两family主指标/CI、BT状态与成本的诚实结果；
- 实际测试与verifier证据、提交/push身份；
- 局限（两位评审、7 clusters、开发者参与、elapsed口径、BT不可识别时的限制）；
- D4是否完成、D5还需什么。

不得在聊天中粘贴64条原始答案或notes。结果无论支持、否定或无法区分 Proposed 都如实交付。
结束时明确没有自动开始D5、没有修改D3事实源，也不要声称整个 Defense MVP 已完成。
