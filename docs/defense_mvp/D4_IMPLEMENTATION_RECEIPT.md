# Defense MVP D4 聚合与统计分析实现回执

日期：2026-09-04；环境：本地 Windows CPU-only。

状态：**D4 工程、正式聚合、统计分析与独立验证全部通过，可以进入 D5 报告制作。**

D4 只分析既有 D3 正式封存，不修改 D1–D3 事实源，不重做人评，不运行 GPU/模型或远程任务。
本回执不包含 64 条逐题原始答案、notes、private mapping、会话令牌或媒体。

## 1. 协议冻结与解封审计

真实答案读取前已完成并普通推送审计提交：

- commit：`79976982a3a438ffe13b596ea4389d3645d8847a`
- message：`feat(defense): freeze D4 analysis protocol`
- 配置：`configs/defense_mvp/analysis-v1.yaml`
- 配置 SHA-256：`9b29f1fad47b35ff7ae75b928e1811b98347aec8c7e2fe175cf09a7f1a283fa0`
- 预解封测试：D4 31 passed；Defense 147 passed；compileall 和三个 D4 CLI smoke 通过

配置在解封前固定了五字段、4×4 双人分歧表、28/14 分母、tie/uncertain 计分、agreement/kappa、
Bradley–Terry 状态机、sample-cluster bootstrap 的 seed/2,000 次/quantile、失败案例规则和成本口径。
正式结果产生后没有改变代码、配置、公式、seed、次数、案例规则或 D2 选择。

解封前现有 D3 verifier 再次得到 `formal/dual/complete`：64 条真人确认、10 条共享自动平局，
A/B 各 42/42、缺题 0；验证前后 formal bundle 与两个 export 共 59 个文件的 SHA 完全相同。

## 2. 唯一正式输入

| 输入 | SHA-256 |
|---|---|
| D3 `formal-bundle/bundle.json` | `c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6` |
| A export `SHA256SUMS` | `ad796e6aca1991b72f9820d2eee807c4fec89a9c80e9574ee1aae8ed3ffcae85` |
| B export `SHA256SUMS` | `91e6a169b81ef825e29e808a8777c264be55b5f88d5eed8ab9f82d5afc936a3a` |
| D3 `dual-verification-v01.json` | `280b099845be84936021e3bffa9e4f69ab24749a7833f03ea3909f18737bd357` |
| `pilot.yaml` | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |
| D2 `comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| D2 `selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |

实现还验证 D2 selection/metrics/design/ingest 的完整 checksum inventory 和跨文件关系，
并从冻结 role 恢复 Proposed 所在 X/Y 侧；没有按文件名、position 或结果手工猜方向。

## 3. 正式输出身份

唯一正式输出根为 `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/`，采用 no-replace，未产生 v02
或额外成功/失败 D4 根。

| 产物 | SHA-256 |
|---|---|
| `aggregate/aggregate.jsonl` | `c4dd6b2b1ade57da68d15c06f00e122f4e41a4aa99e34f01e3795f6a7dda3502` |
| `aggregate/SHA256SUMS` | `17cd49237c975669c45e3cad6591db013333d6ba279f33660b6d2b3839e663d7` |
| `analysis/summary.json` | `a329396cddbbe0eaca66430c7df0743c6e16c885f181f4fd90c49ab7e7326e17` |
| `analysis/main-table.csv` | `8948b6807301e72df61bac749b628409f5b48e33df347895ebd699616819d968` |
| `analysis/agreement.csv` | `fc4ddb4a03e92d34781c01d7141233375ec43c86d3874ecaff4b394dec18c492` |
| `analysis/bootstrap.jsonl` | `18ad2f59cc3d97317406d0114a70ebf5eb0e3e58fa39aeb03c9e21b548f9526a` |
| `analysis/bt.json` | `21e8967a5c20d00d9b267d58ce52213f1e817b7b13ba753799d75a20781af791` |
| `analysis/costs.json` | `12bb28c826e9bf6db5c810d7bb07791b5dcc6d3d2c76a1a42cf18c5607f7ecf1` |
| `analysis/failure-cases.json` | `b391905c91cc9b0f6b19a517d8489e88dd461e1f30e558ac16c21e46a220ae03` |
| `analysis/SHA256SUMS` | `5954d64759e1b1310b7e752d96b223140a1b7a8a873cf70e375b42ce6d25d37b` |
| `verification.json` | `bcb34778eb9370e062da72472756de9fec9b99663c6f55d2e0a7677da405183f` |

聚合计数守恒：42 个唯一 comparison = 32 个 `human_pair` + 10 个
`automatic_tie/media_identity`；自动平局没有复制成两位评审答案。两个 family 为 28/14，
自动平局为 6/4，sample cluster 为 7。

## 4. 正式主结果

以下均为 all-42 正式口径。`W/L/T/U` 分别为 Proposed 的 win/loss/tie/uncertain；CI 是固定
7 个 `sample_id` cluster、PCG64 seed 20260901、2,000 次、linear percentile 95% CI。

| family | 字段 | W/L/T/U | tie-aware | decisive | 95% CI |
|---|---|---:|---:|---:|---:|
| Proposed N=4 vs N=1 | overall | 5/2/17/4 | 0.554 | 0.714 | [0.482, 0.643] |
| Proposed N=4 vs N=1 | faithfulness | 3/4/19/2 | 0.482 | 0.429 | [0.393, 0.554] |
| Proposed N=4 vs N=1 | preservation | 3/5/16/4 | 0.464 | 0.375 | [0.375, 0.554] |
| Proposed N=4 vs N=1 | temporal consistency | 2/1/24/1 | 0.518 | 0.667 | [0.464, 0.571] |
| Proposed N=4 vs N=1 | visual quality | 4/4/16/4 | 0.500 | 0.500 | [0.411, 0.607] |
| Proposed N=4 vs Linear N=4 | overall | 2/2/9/1 | 0.500 | 0.500 | [0.357, 0.643] |
| Proposed N=4 vs Linear N=4 | faithfulness | 2/1/10/1 | 0.536 | 0.667 | [0.429, 0.643] |
| Proposed N=4 vs Linear N=4 | preservation | 2/2/8/2 | 0.500 | 0.500 | [0.357, 0.643] |
| Proposed N=4 vs Linear N=4 | temporal consistency | 2/1/10/1 | 0.536 | 0.667 | [0.429, 0.643] |
| Proposed N=4 vs Linear N=4 | visual quality | 2/2/8/2 | 0.500 | 0.500 | [0.357, 0.643] |

所有十个 bootstrap 单元均为 2,000 有效、0 无效。overall 的诚实结论是：N=4 对 N=1 有
描述性正向点估计，但 CI 跨 0.5；对 Linear N=4 的点估计为 0.5 且 CI 较宽。D4 不把这些结果
解释成显著优势，也不因结果不强而修改协议。

## 5. 双人一致性

一致性只使用 32 个双方实际作答的 manual comparison；10 个自动平局不进入矩阵或 kappa。

| 字段 | agreement | nominal Cohen's kappa |
|---|---:|---:|
| overall | 14/32 = 0.438 | 0.164 |
| faithfulness | 13/32 = 0.406 | 0.125 |
| preservation | 16/32 = 0.500 | 0.281 |
| temporal consistency | 12/32 = 0.375 | 0.042 |
| visual quality | 13/32 = 0.406 | 0.140 |

五字段向量 exact agreement 为 7/32 = 0.219。所有 kappa 均有限且按四类 canonical 值计算，
没有把 X/Y 合并成 decisive。数值显示双人一致性较低，应作为主要局限而非隐藏。

## 6. Bradley–Terry、失败案例与成本

Bradley–Terry 仅使用聚合 `overall` 的 11 条 decisive 边；tie、uncertain、自动平局均不进入。
无向/有向图门禁通过，状态 `ok`，4 次 Newton 迭代，中心化 ability 和约为 0：

- Proposed N=4：`0.305430`
- Linear N=4：`0.305430`
- N=1 baseline：`-0.610860`

该排序只描述 11 条 decisive 边；Proposed 与 Linear 的能力相同，不能包装成稳定总体排名。

按解封前固定的 `overall outcome in [loss, uncertain]` 规则生成 9 个失败案例索引，稳定按
family/sample/comparison_id 排序。清单不复制媒体、notes 或逐题完整人答，也不在 D4 做案例解读。

成本回执：

- 审计 E0 历史 50 候选 runtime 合计 `12413.711 s`，历史 peak VRAM 最大 `22476 MB`；
- 冻结 D2 metrics run elapsed `27.671 s`，按 50 个 validated candidate 为 `0.553 s/candidate`；
- D2 N=1/2/4 candidate-exposures 为 `35/70/140`，selection records 为 315；
- D2 selection 未留可信 timer，明确为 `unavailable`，没有用 mtime 或估算；
- D4 analysis compute elapsed `0.430 s`；
- A/B current-view server elapsed 合计 `2018.096/3138.452 s`，不是主动观看时间或精确工时；
- A/B confidence median 均为 `0.75`，未用于加权或删题。

## 7. 验证与回归

正式 `verify-analysis` 从 D3 完整正式源重新构建聚合，并复算 summary、主表、五个 confusion
matrix、kappa、BT、2,000 条 bootstrap、成本、失败案例、清单和 receipt，结果 `passed`：

- 42 = 32 + 10；family 28/14；7 clusters；agreement n=32；bootstrap 2,000；BT `ok`；
- aggregate 与 analysis inventory 分别为 5/11 个预期文件，无未知文件；
- 10 个 family×field 计数全部守恒，bootstrap valid+invalid 全部为 2,000；
- BT ability 和 `-5.55e-17`，edge count 11 与 overall decisive 数相同；
- 真实运行后四个 D3 固定 SHA 仍匹配，没有额外 D4 根。

最终源码测试：

| 检查 | 结果 |
|---|---|
| D4 定向 pytest | 31 passed |
| Defense pytest | 147 passed |
| 全仓 pytest | 250 passed，601.76 秒 |
| compileall | 退出码 0 |
| D4 CLI/config smoke | 5 项退出码 0 |
| 正式 D3 verifier / D4 verifier | 均通过 |

最终静态、CLI、checksum 与 Git staged 守卫的最新结果及完成提交/push身份记录在 DEVLOG。

## 8. 局限与下一步

- 只有两位评审，其中一位为开发者参与者；这是同机配合式盲评，不是双盲或人口级评估。
- 只有 7 个 sample cluster，CI 较宽，只描述小样本任务级不确定性。
- agreement/kappa 较低；conservative 聚合产生较多 tie/uncertain，正式分母和原始数量均保留。
- BT 只使用 11 条 decisive 边；虽通过可识别门禁，能力估计仍脆弱。
- current-view elapsed 含停顿、后台和恢复，不能作为精确劳动成本。
- CPU F/P/T/Q 是代理指标，不能替代人类语义与感知质量判断。

D4 已完成，可以进入 D5：由上述机器事实生成可追溯报告、图表、案例页和 slides 草稿。此回执
没有自动开始 D5，没有制作正式 slides/录屏，也没有修改 D3 原记录或宣称整个 Defense MVP 完成。
