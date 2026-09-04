# Defense MVP D4 聚合与统计分析施工方案

版本：`v1.0-pre-unseal`

日期：2026-09-04

环境：本地 Windows、CPU-only

阶段：D4；D1–D3 事实源只读，D5 不在本方案执行范围内

## 1. 目标、验收与停止点

D4 将两份已封存、已验证的 D3 正式双人导出聚合为 42 条唯一 comparison 事实，并在不改变
既定协议的前提下生成可复现统计、第一版机器可读主表、失败案例清单、验证回执和审计记录。

完成必须同时满足：

1. `configs/defense_mvp/analysis-v1.yaml`、实现、synthetic/tiny fixture 和完整协议测试在读取
   正式 `answers.jsonl` 具体答案值前完成，形成独立审计提交并普通推送 `main`。
2. 唯一正式输入通过 D3 `formal/dual/complete` 验证及本方案的全部身份、角色、集合和 SHA 门禁。
3. 真实运行只写入一个新的 no-replace D4 根；首次结果无论正负、平局、分歧或统计不可识别均保留。
4. 正式聚合恰为 32 条 `human_pair` 加 10 条 `automatic_tie/media_identity`；两个 family
   分母恰为 28/14；sample cluster 恰为 7。
5. agreement/kappa、五字段 rates、Bradley–Terry、2,000 次 sample-cluster bootstrap、confidence、
   elapsed 和成本/provenance 均有机器可读输出，所有退化或缺失值带显式状态和原因。
6. D4 定向测试、Defense 全测试、全仓 pytest、compileall、CLI smoke、真实 verifier、checksum、
   Git whitespace/路径/大小/NUL/敏感内容守卫全部通过。
7. D4 实现回执和总施工方案状态完成审计提交与普通推送；最终只允许留下该次 push 的 DEVLOG 回执。

停止点是 D4 正式统计验收通过并明确“可以进入 D5”。不生成 D5 报告、slides、讲稿或录屏，
不宣称整个 Defense MVP 完成。

## 2. 现场基线与边界

### 2.1 2026-09-04 接手核对

- 分支 `main`；接手时 HEAD 与 `origin/main` 均为
  `9d6baa1306fe0e60bcc7876333ed0aa5af8c4885`。
- 允许保留的 tracked 改动只有 `DEVLOG.md` 中 D4 提示词最终 push 回执。
- 根 `DEFENSE-MVP-E0-HANDOFF-v01.tar` 与 `.sha256` 未跟踪，始终禁止暂存。
- D3 正式状态仍为 `formal/dual/complete`：A/B 各 32 条真人确认，10 条共享自动平局，
  各 42/42 coverage，缺题 0。
- D4 尚无代码、配置、测试或输出；总方案中的 D4 CLI 仅为占位。

### 2.2 明确禁止

- 不连接或操作学校服务器，不读写 DATA4，不运行 GPU/模型，不创建远程实验目录。
- 不重新解包、评分、选择、转换媒体、启动标注服务或重做人评。
- 不修改 sealed E0、D1/D2/D3 事实源、正式导出、private mapping、答案、notes 或 D3 回执事实。
- 不把 raw/export/artifacts/media/token/notes/逐题原始答案提交 Git。
- 不因真实结果改变字段、聚合表、分母、seed、bootstrap 次数/quantile、BT 判断、失败案例规则。
- 不进入 E1/E2/E3/DPO，也不改变这些协议或 gate。

## 3. 正式输入身份与解封门禁

### 3.1 唯一正式输入

正式 D3 根为 `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/`：

| 输入 | 固定 SHA-256 |
|---|---|
| `formal-bundle/bundle.json` | `c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6` |
| `formal-exports/annotator-a-v01/SHA256SUMS` | `ad796e6aca1991b72f9820d2eee807c4fec89a9c80e9574ee1aae8ed3ffcae85` |
| `formal-exports/annotator-b-v01/SHA256SUMS` | `91e6a169b81ef825e29e808a8777c264be55b5f88d5eed8ab9f82d5afc936a3a` |
| `formal-exports/dual-verification-v01.json` | `280b099845be84936021e3bffa9e4f69ab24749a7833f03ea3909f18737bd357` |

关联 D2 输入：

| 输入 | 固定 SHA-256 |
|---|---|
| `configs/defense_mvp/pilot.yaml` | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |
| `selection/comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| `selection/selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |

同时使用 D2 `SELECTION_SHA256SUMS`、`DESIGN_SHA256SUMS`、`METRICS_SHA256SUMS`、
`INGEST_SHA256SUMS` 验证整个内部清单和跨文件关系，不能只验上表三个 D2 摘要。

### 3.2 两阶段门禁

**预解封阶段**只允许核对路径、inventory、schema、摘要、coverage ID 集合、comparison 角色、
family/sample/trial/automatic 集合和上述 SHA；不读取或汇总 `answers.jsonl` 的具体答案值。

**解封条件**必须全部具备：

1. 本文、`analysis-v1.yaml`、D4 实现和 synthetic/tiny tests 已完成；
2. 16 个双人选择组合、方向还原、agreement/kappa、rates、BT 状态、bootstrap、no-replace、
   tamper/漂移和隐私边界测试已通过；
3. 已创建并普通推送“真实分析前冻结提交”；
4. DEVLOG 在运行前记录 commit、四个 D3 SHA、配置 SHA、命令、输出根和预期不变量；
5. 现有 `verify-annotations` 在当时源码下返回 `formal/dual/complete`、64 人答、10 自动平局、
   A/B 各 42/42、缺题 0；输入验证前后 checksum 相同。

条件满足后才由 `defense aggregate` 首次读取具体答案。若身份不符，硬失败并停止，不通过改锁、
补题、丢题或复制记录接受。

## 4. 冻结统计协议 `defense-analysis-v1`

### 4.1 配置固定项

`analysis-v1.yaml` 必须严格模型化并覆盖：

- schema/protocol/experiment 身份；五个固定字段及 `X/Y/tie/uncertain` 类别顺序；
- 两个 family 的固定分母 28/14、自动平局 6/4、Proposed 角色和对照角色；
- 聚合 4×4 规则表的版本；agreement 只用 32 个 manual pair；
- 主统计口径为 all-42，manual-only 只作预声明诊断；
- BT 三个固定节点、`overall` decisive-only、容差和最大迭代；
- bootstrap RNG `numpy.PCG64`、NumPy `Generator`、seed `20260901`、2,000 次、7 clusters、
  95% percentile、`linear` quantile；
- 失败案例规则 `overall in [loss, uncertain]`，按 family/sample/comparison_id 稳定排序；
- 成本单位和 elapsed 语义；输入 SHA pins。

配置采用 strict Pydantic 模型，未知字段、NaN/Infinity、错误顺序、错误数字或角色均拒绝。

### 4.2 canonical 方向与身份连接

- 分析值只取经过 D3 verifier 校验的 canonical `X/Y/tie/uncertain`；screen A/B 只用于验证
  `x_as` 翻转，不跨评审直接合并。
- 两位人答按 `comparison_id` 连接，文件顺序、position、candidate 文件名均不得作为身份。
- 两边必须具有相同 32 个 manual ID；与 10 个 automatic ID 不相交。
- 每题从冻结 bundle/comparisons/selection 解析 `candidate_x/y.role`、family、sample、trial、replicate，
  并验证服务端记录 media、方向和 D2 角色事实。
- 聚合记录保存来源、输入摘要及两位 canonical 值；不复制 notes、screen payload、timestamp；
  annotation elapsed/confidence 进入单独受限描述性事实，不进入答案权重。
- 自动平局每题只生成一个系统事实，五字段全为 tie，不伪造评审或人工时间。

### 4.3 五字段双人聚合

对五个字段逐字段使用同一个穷举、对称 4×4 表：

| A/B 组合 | 聚合 |
|---|---|
| 同一 decisive `X/X` 或 `Y/Y` | 同一 decisive |
| decisive 与 tie（任意顺序） | `tie` |
| `tie/tie` | `tie` |
| `X/Y` 或 `Y/X` | `uncertain` |
| 任一 `uncertain` | `uncertain` |

不得第三人裁决。最终恰为 42 个唯一 comparison；每字段保留 A/B 原始类别计数与聚合类别。

### 4.4 agreement 与 nominal Cohen's kappa

agreement 只用双方实际作答的 32 个 manual comparison，自动平局不进入：

- 每字段输出按固定类别顺序的 4×4 confusion matrix、样本数 32、对角和、observed agreement、
  A/B 各类别边际。
- `expected = sum_c p_A(c) * p_B(c)`；`kappa = (observed - expected)/(1-expected)`。
- 空输入、`expected == 1`、非有限值返回 `undefined` 与 reason，不伪造 0 或 1。
- exact agreement 是同题五字段 canonical 向量完全相同；confidence/notes/time 不参与。
- 另存 exact numerator/denominator/rate；不把 X/Y 折成 decisive 作为主 agreement。

### 4.5 family rates 与计数守恒

对 all-42 主表和 manual-only 诊断，分别对五字段计算：

- `wins/losses/ties/uncertain/total`，其中 Proposed 所在 X/Y 侧由冻结角色解析；
- `tie_aware = (wins + 0.5*ties + 0.5*uncertain)/total`；
- `decisive = wins/(wins+losses)`，分母为 0 时 `undefined/no_decisive`；
- `tie_rate = ties/total`；`uncertain_rate = uncertain/total`。

all-42 中 `wins+losses+ties+uncertain == total` 且 family total 必须为 28/14。tie 与 uncertain
即使在 tie-aware 都记 0.5，也始终分列。五字段不当作独立样本扩大 n。

### 4.6 Bradley–Terry 状态机

固定节点：

- `constrained-pareto-n4`（Proposed N=4）；
- `constrained-pareto-n1`（N=1 baseline）；
- `equal-linear-n4`（Linear N=4）。

只把聚合 `overall` 的 decisive X/Y 转为 winner/loser 边；tie、uncertain、自动平局不进边。
拟合前依序检查：

1. `no_decisive`：总边数 0；
2. `family_no_decisive`：任一固定 family 没有 decisive 边；
3. `insufficient_connectivity`：三节点无向图不连通；
4. `separation`：有向胜图不是强连通，有限无约束 MLE 不存在；
5. `not_converged` / `non_finite`：数值迭代失败。

可识别时使用无惩罚 Bradley–Terry 对数似然的中心化 Newton 法：构造 gradient/Hessian，
以最后一节点为参考解约束系统，每步回到 ability 和为 0；固定 tolerance/max_iterations，
必要时用确定性 step-halving 只保证似然不降，不加伪计数、ridge 或结果依赖正则。输出 status、
节点顺序、ability、迭代数、收敛误差、log-likelihood、边/方向/family 计数和图诊断。

### 4.7 sample-cluster bootstrap

- cluster 固定 `sample_id`，正式恰为 7 个；每次用 `numpy.random.Generator(PCG64(seed))`
  有放回抽 7 个 sample；同一 sample 重复抽中时，其全部 family/replicate 事实按倍数带入。
- 使用 all-42 聚合事实及固定计分 win=1、loss=0、tie/uncertain=0.5。
- 至少为两个 family 的 `overall` 输出 2,000 个 replicate；配置预先声明五字段全部输出同口径
  诊断 CI，避免揭盲后挑字段。
- CI 使用 `numpy.quantile(values, [0.025,0.975], method="linear")`；记录 lower/upper、有效/
  无效次数、原因计数、cluster 顺序、每次 draw index 和统计值。
- 某次分母为 0 时保留 undefined；正式固定设计正常应有全部有效值，但验证器不能假装成功。
- CI 只描述 7 个任务 cluster 的小样本不确定性，不作为项目成败或论文级显著性判断。

### 4.8 confidence、elapsed 与成本

- confidence 按 annotator-a、annotator-b 和 pooled 输出 count、codes、频数、mean、median、
  Q1/Q3（linear）；不加权、不删低 confidence。
- `current_view_elapsed_seconds` 按评审输出 count、sum、mean、median、Q1/Q3/min/max，并写明
  `current-view-server-elapsed-not-active-labor`，不得称为精确观看时间或人工工时。
- 成本只从已验证来源读取，并给每一项 `status/value/unit/source_path/source_sha256/semantics`：
  E0 candidate runtime/VRAM（若同口径可信）、D2 scoring 总 elapsed 与每候选值、选择 elapsed
  （若没有可信计时则 unavailable）、N=1/2/4 候选暴露量、D4 自身运行 elapsed。
- mtime、D3 重启间隔或估算值不得充当成本；缺失写 `unavailable` 与 reason。

## 5. 实现结构与 CLI

### 5.1 模块

- `analysis_models.py`：冻结配置、聚合/统计严格 schema 与状态类型。
- `aggregation.py`：D3/D2 完整门禁、ID/方向/角色连接、16 组合聚合、自动平局、no-replace 输出。
- `analysis.py`：agreement/kappa、rates、BT、bootstrap、confidence/elapsed、成本和机器表。
- `analysis_verification.py`：重新计算核心事实、验证清单/receipt/漂移/未知文件和跨产物一致性。
- 复用现有 `annotation_bundle.read_json/verify_sums/stage/write_sums`、`annotation_export.verify_annotations`
  和 `io.rename_noreplace`；不改 D1–D3 行为。

### 5.2 CLI

```powershell
uv run defense aggregate \
  --bundle <formal-bundle> --left <annotator-a-export> --right <annotator-b-export> \
  --dual-verification <dual-verification-v01.json> \
  --selection <selection-dir> --metrics <metrics-dir> --design <design-dir> \
  --ingest <normalized-manifest> --config configs/defense_mvp/analysis-v1.yaml \
  --output <new-aggregate-dir>

uv run defense analyze \
  --aggregate <aggregate-dir> --selection <selection-dir> --metrics <metrics-dir> \
  --design <design-dir> --ingest <normalized-manifest> \
  --config configs/defense_mvp/analysis-v1.yaml --output <new-analysis-dir>

uv run defense verify-analysis \
  --bundle <formal-bundle> --left <annotator-a-export> --right <annotator-b-export> \
  --dual-verification <dual-verification-v01.json> \
  --aggregate <aggregate-dir> --analysis <analysis-dir> --selection <selection-dir> \
  --metrics <metrics-dir> --design <design-dir> --ingest <normalized-manifest> \
  --config configs/defense_mvp/analysis-v1.yaml --output <new-verification-file>
```

三个入口都验证完整 export 目录和 bundle；不接受裸 answers 文件。正式输出目录采用 staging +
原子 no-replace；失败保留带唯一后缀的 `.failed` 诊断，绝不覆盖既有成功或失败目录。

## 6. 输出契约

正式根：`artifacts/defense_mvp/DEFENSE-MVP-D4-v01/`，Git 忽略。

```text
aggregate/
  aggregate.jsonl
  agreement-input.json
  aggregation-receipt.json
  input-manifest.json
  SHA256SUMS
analysis/
  summary.json
  main-table.csv
  agreement.csv
  confusion-matrices.json
  bootstrap.jsonl
  bt.json
  costs.json
  failure-cases.json
  analysis-receipt.json
  input-manifest.json
  SHA256SUMS
verification.json
```

稳定事实文件不写运行时间、绝对输出路径或随机 UUID；时间/环境只进入 receipt。所有 JSON 使用
UTF-8、排序键、拒绝 NaN/Infinity；JSONL 按固定 ID/field 顺序；CSV 列顺序固定。

`failure-cases.json` 只列 `overall` 对 Proposed 为 `loss` 或 `uncertain` 的 comparison，并按
family/sample/comparison_id 稳定排序；含角色、聚合类别和必要 provenance，不复制媒体、notes、
原始 screen/canonical 五字段载荷，不做 D5 解释。

## 7. 测试与验收矩阵

### 7.1 真实解封前 synthetic/tiny 测试

1. 输入门禁：practice、单人、同身份、bundle/export 混用、SHA 漂移、缺/重/多题、顺序变化、
   manual/automatic 交叉、伪自动平局、方向/角色/sample/trial/replicate 不一致全部拒绝。
2. 聚合：五字段 16 组合与对称性；按 ID 而非 position；screen A/B 翻转验证；32+10=42；
   自动平局仅一个系统事实；源文件 checksum 前后不变。
3. 一致性：手算 confusion/agreement/kappa、exact vector、边际；expected=1、空、全同/全不同；
   自动平局排除。
4. rates：28/14 守恒、tie/uncertain 各 0.5、无 decisive、all/manual 标签隔离、X/Y 角色交换。
5. BT：可识别三节点小图、标签交换、无边、family 无边、无向不连通、完全分离、强连通、
   non-convergence/非有限、ability 中心化与确定性。
6. bootstrap：7 clusters、整 cluster 搬运、重复 cluster 倍增、seed/2000 字节级复现、linear
   percentile 手算、undefined replicate；明确不是 42 comparison 独立抽样。
7. 成本：来源/SHA/单位/语义绑定，缺失 unavailable，elapsed 不标 active labor。
8. 输出：staging 失败、no-replace、receipt/checksum、未知文件、配置/输入/源码漂移、tamper 后硬失败；
   跨路径重跑稳定事实一致。
9. 隐私：输出和待提交 diff 不含 private mapping、token、notes、screen、原始逐题答案或媒体。

### 7.2 正式运行后不变量

- 42 唯一聚合 = 32 `human_pair` + 10 `automatic_tie`；manual ID 两边相同且与 auto 不交叉。
- family 28/14；automatic family 6/4；7 sample；五字段逐 family 计数全部守恒。
- agreement 每字段 `n=32`；exact denominator 32；自动平局没有进入矩阵。
- bootstrap 每个预声明 family/field 恰 2,000 次，cluster 数 7，seed/engine/quantile 固定。
- BT 边数等于 overall 聚合 decisive 数，状态与 connectivity/separation/数值诊断一致。
- 输入、配置、源码、依赖、输出 SHA 可追溯；正式输入前后字节摘要相同。
- verifier 从事实产物重新计算并通过，不能只接受 receipt 自报数字。

### 7.3 最终回归

```powershell
uv run pytest tests/defense_mvp/test_d4_analysis.py -o addopts='' -q
uv run pytest tests/defense_mvp -o addopts='' -q
uv run pytest -o addopts='' -q
uv run python -m compileall -q src tests
uv run defense version
uv run defense aggregate --help
uv run defense analyze --help
uv run defense verify-analysis --help
git diff --check
```

另运行真实 `verify-annotations`、`verify-analysis`、输入/输出 checksum、staged path/binary/size/NUL/
敏感载荷守卫，并记录实际数量、耗时和退出码。

## 8. 里程碑、DEVLOG 与发布

### D4.0 输入预检

只读确认现场、schema/inventory/摘要/SHA/角色/ID/42 coverage；不读取答案具体值。完成后写 DEVLOG。

### D4.1 协议冻结

完成本文、配置、模型、聚合/分析/验证器、CLI 和 synthetic/tiny 测试；逐个可验证步骤即时写
DEVLOG。定向与必要回归通过后，fetch 远端、显式 allowlist 暂存、安全守卫、创建并普通推送
“真实分析前冻结提交”。

### D4.2–D4.3 聚合与分析实现

这两部分在 D4.1 冻结提交前通过 fixture 完成。正式解封后不再调整协议；仅发现与真实数值无关的
机械 bug 时，先记录失败、给出 synthetic 复现和回归测试，再修复并用 `v02` 新输出，保留 v01。

### D4.4 正式一次性运行

DEVLOG 先记运行计划与冻结身份，再运行 `verify-annotations`、`aggregate`、`analyze` 和
`verify-analysis`。输出写 `DEFENSE-MVP-D4-v01` 下全新路径，no-replace。首次负面或失败输出保留。

### D4.5 正式验收与发布

核对全部不变量，生成 `docs/defense_mvp/D4_IMPLEMENTATION_RECEIPT.md`，将总施工方案 D4 状态
更新为已完成；运行最终回归和 Git 守卫。仅显式暂存源码、测试、配置、文档和非敏感统计回执，
创建完成提交并普通推送 `main`，不 force-push。push 回执作为唯一未提交 DEVLOG 增量保留。

## 9. 异常与停止条件

以下情况立即停止并向用户给出证据，不自行放宽：

- 四个 D3 SHA、三个 D2 pin、内部 checksum 或 `formal/dual/complete` 任一不符；
- A/B ID、manual/automatic 集合、角色、sample/trial/family cardinality 冲突；
- 必须改变本方案统计协议才能继续；
- 发现无法保留或无法安全绕开的用户工作树冲突；
- 需要远程/GPU/服务器/额外权限或必须修改 D1–D3 事实源。

低 win rate、宽 CI、低/负 kappa、BT separation/不可识别、成本 unavailable 或失败案例较多
不是停止条件，必须诚实保留并完成验收。
