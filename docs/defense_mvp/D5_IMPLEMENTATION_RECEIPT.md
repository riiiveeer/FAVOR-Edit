# D5 报告与 Slides 初稿工程验收回执

日期：2026-09-06；环境：本地 Windows CPU-only；协议：`defense-report-v1`。

**D5 报告、Slides 初稿工程与正式草稿验收完成，可以进入 D6；D6 尚未启动。**
本回执不代表整个 Defense MVP 已完成，不是最终答辩版或最终交付 manifest。

## 1. 真实工作树、源码与正式运行

接手时 main/HEAD/origin 为 `9f1f3c565ff133c7559635b0c48d52ca5b2ab511`；保留既有 DEVLOG
发布增量及根 tar/sidecar。没有 reset、clean、stash、改写历史或覆盖用户文件。

D5 全部代码、配置和测试冻结于 `bd55d4f60963f05d92fc05615a35aa5ac616dfd7`，已普通推送 main。
正式媒体 gate 在 2026-09-06 08:41:23 +08:00 写入 DEVLOG，早于任何正式案例媒体查看。
配置 SHA-256 为 `000f4acee9b4b141382cbe1492863c7bc004b48edc5aad91a7a15c1321815005`。
固定案例选择、全部定性候选、统一帧位置已在 49 项 fixture 测试中验证；没有因正式结果换例。

首次正式运行成功，唯一根为 `artifacts/defense_mvp/DEFENSE-MVP-D5-v01/`；退出码 0，
wall 30.0435825 秒。没有正式 v02、正式失败根或覆盖重跑。生成后仅 no-replace 追加
`visual-qa.json`、`verification.json`；固定生成清单不变。此前 synthetic 失败目录保留在
`artifacts/defense_mvp/d5-engineering/`，始终标为非研究数据。

D4 锁定顶层 Defense 源码与依赖，因此 D5 实现在独立 `src/defense_mvp/reporting/`，采用
`python -m defense_mvp.reporting` 入口；13 个 D5 code/config/test 文件 SHA 已与冻结 commit blob
逐个相等，D4 回执锁定的 25 个旧实现/依赖文件也保持相等。没有修改 E0 或 D1–D4 事实源，
没有重新评分、选择、标注或聚合。原 D3/D4 verifier 作为黑盒只读复验；报告不消费原始答案、
notes、入口凭证或私有映射。没有连接服务器、DATA4、加载模型或 GPU 工作。

## 2. 输入身份

以下 21 个 pin 在现场、正式 gate、生成、独立验证及生成后检查中相同。内部 inventories、
媒体 checksum、candidate/role/帧关系另由原 verifier 完整验证，未以此表代替集合验证。
D4 独立复算输出位于新的系统 Temp 文件，与既有正式 verification 内容和 SHA 完全相同。

| 正式输入（仓库相对路径） | SHA-256 |
|---|---|
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/aggregate/SHA256SUMS` | `17cd49237c975669c45e3cad6591db013333d6ba279f33660b6d2b3839e663d7` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/SHA256SUMS` | `5954d64759e1b1310b7e752d96b223140a1b7a8a873cf70e375b42ce6d25d37b` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/agreement.csv` | `fc4ddb4a03e92d34781c01d7141233375ec43c86d3874ecaff4b394dec18c492` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/bootstrap.jsonl` | `18ad2f59cc3d97317406d0114a70ebf5eb0e3e58fa39aeb03c9e21b548f9526a` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/bt.json` | `21e8967a5c20d00d9b267d58ce52213f1e817b7b13ba753799d75a20781af791` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/costs.json` | `12bb28c826e9bf6db5c810d7bb07791b5dcc6d3d2c76a1a42cf18c5607f7ecf1` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/failure-cases.json` | `b391905c91cc9b0f6b19a517d8489e88dd461e1f30e558ac16c21e46a220ae03` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/main-table.csv` | `8948b6807301e72df61bac749b628409f5b48e33df347895ebd699616819d968` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis/summary.json` | `a329396cddbbe0eaca66430c7df0743c6e16c885f181f4fd90c49ab7e7326e17` |
| `artifacts/defense_mvp/DEFENSE-MVP-D4-v01/verification.json` | `bcb34778eb9370e062da72472756de9fec9b99663c6f55d2e0a7677da405183f` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/design/DESIGN_SHA256SUMS` | `a1d41b96454a41a3693bfe210cbc58339c9e85490a815db45a7e482a45198910` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/design/design.json` | `891ee8b0d75acf5c825fd01d529d545f12a7fb1b72a4310364a805d8d6cd1ff5` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/INGEST_SHA256SUMS` | `c8eca842c9734ad8be85589bc928517000371051f86eb33909094ccdf676d1f2` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json` | `b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/METRICS_SHA256SUMS` | `fd947a0d31be63b73e38c9e75e7404c20d4412c62018de97141bb53b3b085c0d` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/metrics.jsonl` | `c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/selection/SELECTION_SHA256SUMS` | `a94929c3bf7c3b716ba0e59f468156ea0855b8a8b23a7657df2039705c5b400d` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/selection/comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| `artifacts/defense_mvp/DEFENSE-MVP-v01/selection/selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |
| `configs/defense_mvp/analysis-v1.yaml` | `9b29f1fad47b35ff7ae75b928e1811b98347aec8c7e2fe175cf09a7f1a283fa0` |
| `configs/defense_mvp/pilot.yaml` | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |

实际 D2 清单名是 INGEST/METRICS/DESIGN/SELECTION_SHA256SUMS；交接提示词中的 SHA256SUMS
是简称，真实文件名已按现场记录。D3 验证为 formal/dual/complete，双方各 42/42 coverage；
D4 为 passed，42 = 32 human_pair + 10 automatic，family 28/14、7 clusters、agreement n=32、
bootstrap 2000、BT ok。原始逐题答案未复制到本回执或报告。

## 3. 交付物与可追溯性

- [公开报告初稿](DEFENSE_REPORT.md)、[讲稿初稿](DEFENSE_SCRIPT.md)、[录屏路径方案](RECORDING_PLAN.md)。
- [主表](d5_generated/tables/main-results.csv)、[一致性表](d5_generated/tables/agreement.csv)、[成本表](d5_generated/tables/costs.csv)。
- `d5_generated/figures/`：system-flow、overall-ci、outcomes、agreement 各 SVG/PNG，共 8 图。
- [4 个固定案例页](../../artifacts/defense_mvp/DEFENSE-MVP-D5-v01/report/cases/index.html)。内部 trace 与全部 9 条 D4 failure index 留在忽略 artifact。
- [10 页中文 PPTX 初稿](../../artifacts/defense_mvp/DEFENSE-MVP-D5-v01/slides/DEFENSE_MVP_D5_DRAFT.pptx)、[全页缩略图](../../artifacts/defense_mvp/DEFENSE-MVP-D5-v01/slides/contact-sheet.png)，逐页 PNG 位于同根 `slides/rendered/`。
- [D5 独立验证回执](../../artifacts/defense_mvp/DEFENSE-MVP-D5-v01/verification.json)，生成/source/runtime/visual 回执均在同根。

事实注册表有 228 项，每项含原始值、显示精度、单位、来源、JSON/CSV/JSONL 指针及 SHA；
各指针独立解析并验证。报告、表、图、slide-data 和讲稿共享受控模板，不手抄第二套数字。
88 个稳定文件跨路径重新生成后逐字节一致，82 个 artifact 内引用/链接通过。PPTX 的正文、
数字、顺序、讲者注释和嵌入图像逐一与生成数据核对；不把二进制 SHA 当语义验证替代。

公开导出共 15 文件：[public-export.json](d5_generated/public-export.json) 保存生成映射，
SHA 为 `ad67ab735e58e494e09bbbdabd7844fd25e679d36872c3b9c625a27d65eac2dc`。
报告只改相对链接；讲稿、录屏方案、CSV/PNG 是正式 artifact 的字节副本。4 个 SVG 副本仅
去除 Matplotlib 路径数据中的行尾空白；逐 XML 节点、属性与文本检查语义相等，正式原件保持不变。
独立发布适配器 `scripts/defense_mvp/publish_d5_docs.py --verify` 为 passed（15 文件、4 SVG）；
版本 2 导出映射包含转换前后 SHA、转换规则和适配器 SHA。原冻结 `verify_public` 检查原始
字节复制阶段；最终 Git 副本由新适配器验证。公开 Markdown 中 14 个引用均可解析。案例媒体和 trace 不进 Git；
仅有 Git checkout 时本地 artifact 链接需要这份独立保存的 D5 草稿目录。

## 4. 内容与视觉验收

报告主结论保持：相对 N=1 有描述性正向点估计且区间跨 0.5；相对 Linear N=4 未观察到差异。
两 family 的完整 W/L/T/U 与主分母先报告，decisive 仅作为诊断；不新增检验、子组或测量。
精确主表及所有五字段见生成 CSV，主要结果为：

| family | W/L/T/U | n | tie-aware | 95% CI |
|---|---|---:|---:|---|
| proposed-n4-vs-n1 | 5/2/17/4 | 28 | 0.554 | [0.482, 0.643] |
| proposed-vs-linear-n4 | 2/2/9/1 | 14 | 0.500 | [0.357, 0.643] |

overall agreement 14/32 = 0.438，kappa 0.164，exact 五字段 7/32 = 0.219；自动平局不进入
agreement。BT 只有 11 条 decisive 边，Proposed 与 Linear ability 相同，估计脆弱。
两位评审含一位开发者、7 个 clusters、宽区间、低一致性、CPU 代理及 15 个未量化候选均明确保留。
成本表保留 E0 历史生成/D2 指标/D4 计算阶段语义；selection unavailable 不补估算，A/B 页面
elapsed 不解释为主动观看工时，不以历史 GPU 与本地 CPU 时间构造加速比。

四个固定案例均 available。成功、失败、不确定按预冻结键各取首项；定性边界取首个任务并
展示输入及其全部 5 候选。定量页固定输入/Proposed/comparator，统一 16 帧中的 0/5/10/15，
原帧像素复制，显示等比缩放。不能从四张静态帧推导整段时序效果；案例标签来自正式聚合。
全部 9 条 D4 失败索引可反查，未浏览评审 notes 补故事或调换案例。

4 图使用冻结的 1600×900、白底、160 DPI 和中文字体；SVG 可解析、PNG 可解码，CI 使用完整
0–1 轴与 0.5 参考线，agreement/kappa 为 −1–1，tie/uncertain 颜色和纹理分开。

PPTX 通过当前 presentations skill 的 Artifact Tool 2.8.59 生成、finalizer、最终文件重新导入
与 10 页 1280×720 渲染。package integrity、font selection、first-party import 均通过；
layout 0 findings、0 warnings。已检查一次完整 contact sheet 和 10 张单页 PNG，另看全部正式图
和 4 张案例 sheet：中文清楚、图片比例正常、无裁切/重叠、投影阅读尺度合理。第 9 页秒单位
自然换行但未截断。所有视觉结论绑定实际 PPTX/PNG SHA，见 visual-qa.json。

这不是桌面 PowerPoint GUI、实际投影或浏览器 HTML 截图验收；HTML 做内容、链接和原帧检查。
无可用 bundled LibreOffice，D5 不额外输出 PDF。PPTX 受内部时间戳影响，不承诺字节级重建；
稳定数据字节相等，PPTX 语义和实际文件身份分别验证。

bundled Windows canvas 曾在 synthetic 输出完成后析构崩溃，诊断保留。最终采用完成握手：
所有写入 await 完成后 helper 等待，父进程核对 PPTX/10 PNG 的 SHA 才结束该空闲进程。
正式 slides receipt 记录 controller-termination-after-verified-completion 与原始退出码 1；
不是把未知崩溃忽略为成功，缺文件/坏 SHA/超时都会硬失败。生成时 status 仍为
rendered-awaiting-visual-review，是不可改写的阶段快照；后续 visual-qa 和 verification 均 passed。

讲稿与 10 页一一对应，1777 个有效字符，配置 260 字符/分钟，估计 410.076923 秒（约 6 分 50 秒），
在 300–420 秒范围。只是静态估时，没有计时演练。录屏方案覆盖 60–90 秒顺序和失败降级，
没有录制视频、启动正式作答会话或创建最终交付 manifest。

## 5. 最终源码测试与检查

全部测试使用冻结 commit 对应的最终源码；冻结报告源码后仅增加独立 Git 文档发布适配器及 4 项测试；最终全仓再次运行，见下表与 DEVLOG。

| 检查 | 实际结果 | 时间 / 退出码 | 证据 |
|---|---|---|---|
| D5 定向 pytest | 49 passed | 58.39 s / 0 | DEVLOG D5.3-TEST-06、D5.3-VISUAL-QA-02；synthetic pytest-8940e990099348e0ae927c4f2b37997b |
| Defense pytest | 196 passed | pytest 588.07 s，wall 590.996 s / 0 | d5-engineering/defense-final-01.log |
| 冻结报告工程全仓 pytest | 299 passed | pytest 585.06 s，wall 588.440 s / 0 | d5-engineering/repository-final-01.log |
| SVG 发布适配器定向 pytest | 4 passed | pytest 0.47 s / 0 | D5.5-SVG-PUBLISH-TEST-01 |
| 加入发布适配器后的最终全仓 pytest | 303 passed | pytest 661.89 s，wall 685.363 s / 0 | d5-engineering/repository-final-02.log |
| 最终 compileall src/tests/scripts | passed | 0.460 s / 0 | D5.5-PUBLISH-SMOKE-01 |
| report / verify-report help | passed | 0.979 / 0.959 s；均 0 | D5.5-FINAL-SMOKE-02/03 |
| pilot / report-v1 config smoke | passed | 1.102 / 0.983 s；均 0 | D5.5-FINAL-SMOKE-04/05 |
| 原 D3 verifier | formal/dual/complete | 2.288 s / 0 | D5.5-D3-VERIFY-01 |
| 原 D4 verifier | passed；Temp 回执与正式 SHA 相同 | 0 | D5.3-D4-VERIFY-02；正式 D5 verifier 亦完整调用 |
| 正式 D5 verifier | passed；88 重建 / 82 链接 / 10 页 | 11.189 s / 0 | D5.5-FORMAL-VERIFY-01 |
| 输入/source/public 身份 | 21 pins / 13 D5 文件 / 25 旧文件 / 15 公开文件通过 | 1.071 s / 0 | D5.5-FINAL-IDENTITY-01 |
| 发布入口 help / 最终副本 verify | passed；15 文件、4 SVG | 1.053 / 1.108 s；均 0 | D5.5-PUBLISH-SMOKE-02/03 |
| 发布适配后完整 D5 复验 | passed；回执 SHA 完全相同 | 12.399 s / 0 | D5.5-SVG-FORMAL-REVERIFY-01 |
| 最终 staged / 工作树 whitespace 与发布守卫 | passed；21 路径、36 个 Markdown 链接 | 均 0 | D5.5-COMPLETION-STAGE-02 |

D5 测试包含身份/计数/角色断链、事实精度与来源指针、叙事守卫、图表格式、确定性案例与帧、
缺类 unavailable、真实 bundled synthetic PPTX 与渲染、讲稿、no-replace、失败保留、未知文件、
重算 checksum 后篡改、PPTX 改数字、缺 visual QA 和公开副本验证。不调用真实模型。

## 6. 输出身份

以下路径相对唯一 D5 根。根 SHA256SUMS 固定记录生成文件；visual-qa/verification 是后续
唯一允许的新文件，独立 verifier 另验证其绑定，其他未知文件会拒绝。

| 输出 | SHA-256 |
|---|---|
| `SHA256SUMS` | `3a6fe6222b1ab132b11f9b97b9c195f8c3f8f1747e5646413f668c6d182d5576` |
| `report/SHA256SUMS` | `04e997650b29c3d870ce14017872b842a4bd517848792eb653a90ddede92617f` |
| `report/DEFENSE_REPORT.md` | `3adccebff901a4cd78f60a331165e26c0e275845042ed87c2a83e3108c800d7f` |
| `report/report-data.json` | `4c2c9839d8ccc9c6b601f76ab22859bb2fa231fa44ff536b909c255591c3e3c2` |
| `report/slide-data.json` | `c9857e7cb64609d6d7c1bfa9be981dbc027cb04d7dd8bfa74862aef36d07fdd3` |
| `report/input-manifest.json` | `bf6d5199ea9b779ff4c7ccefdea4310e3bcb1e2a40d2c07da404fd7d112222d2` |
| `report/report-receipt.json` | `e71a2085c268e6df7fe671e86653e1f4df02350972f0ddc8053fd3d643f502da` |
| `slides/DEFENSE_MVP_D5_DRAFT.pptx` | `675fee2e0d91d3c83deab36325adc606ff1ae65e0953b03c18d555e833ba572c` |
| `slides/slides-receipt.json` | `0f588146cc7084744ef8fea532e01d852ce673584d073f66c472e333c3040170` |
| `slides/contact-sheet.png` | `244d8987149aa961c9a41151e22a6b9528d3c4ac07a48b009b9ab2d24587a812` |
| `script/DEFENSE_SCRIPT.md` | `e8f7f89b6c47e874a6a7593dbad6effac15352e5175317a1392e8409756fa788` |
| `script/RECORDING_PLAN.md` | `f9e5cf8464d470a277e8c7f839a23e85fc295ea2a94926c6bc6899857a500d35` |
| `visual-qa.json` | `bb5f1a5a6a7924686dd081917e98afbc98397444402f3185bf2fb9f549bc43df` |
| `verification.json` | `77bf8d37a9f304d06e67bdc606aaa5e4aa47958dd8802e9452c6e57d1acc1fb9` |

## 7. 复验入口与发布

在仓库根调用以下命令；每次 verification 输出必须使用新文件，不能覆盖正式回执：

```powershell
$d5Audit = Join-Path ([IO.Path]::GetTempPath()) ('defense-d5-' + [guid]::NewGuid().ToString('N') + '.json')
uv run python -m defense_mvp.reporting verify-report --report artifacts/defense_mvp/DEFENSE-MVP-D5-v01 --aggregate artifacts/defense_mvp/DEFENSE-MVP-D4-v01/aggregate --analysis artifacts/defense_mvp/DEFENSE-MVP-D4-v01/analysis --d4-verification artifacts/defense_mvp/DEFENSE-MVP-D4-v01/verification.json --selection artifacts/defense_mvp/DEFENSE-MVP-v01/selection --metrics artifacts/defense_mvp/DEFENSE-MVP-v01/metrics --design artifacts/defense_mvp/DEFENSE-MVP-v01/design --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --config configs/defense_mvp/report-v1.yaml --output $d5Audit
```

公开副本复验命令（只读；去掉 `--verify` 可从正式根重新发布到新文档目录；遇到用户编辑硬失败）：

```powershell
uv run python scripts/defense_mvp/publish_d5_docs.py --root artifacts/defense_mvp/DEFENSE-MVP-D5-v01 --destination docs/defense_mvp --verify
```

完整 report 生成命令见 [D5 施工方案](D5_CONSTRUCTION_PLAN.md) 和 DEVLOG 媒体 gate；现场 runtime
位置由 workspace dependency loader 得到并记于忽略 report receipt，不写机器绝对路径进 Git。
禁止为复现覆盖 v01；如有后续正式修复，先新协议/工程记录和 fixture 回归，再使用新目录。

冻结工程提交 `bd55d4f60963f05d92fc05615a35aa5ac616dfd7` 已普通推送 main。
本回执、公开文档和总计划通过随后草稿验收审计提交发布；该提交 SHA 与 push 实际结果记于
DEVLOG 的 D5.5-COMPLETION-COMMIT/PUSH 记录，可用 `git log -- docs/defense_mvp/D5_IMPLEMENTATION_RECEIPT.md`
定位。本回执不写自引用 commit SHA。发布适配器独立于正式报告冻结源码，版本 2 public-export
另绑定其 SHA，不改变正式 v01 的来源身份。每次先 fetch、核对远端，再显式 allowlist 暂存、检查
whitespace/大小/NUL/二进制/敏感载荷，普通 push main；最终 push 回执可为唯一未提交 tracked 增量。

Git 只包含 D5 代码/配置/测试、Markdown、3 CSV 和 8 张小型非媒体图；tar/sidecar、raw、artifacts、
PPTX/PDF、案例图片、contact sheet、正式导出/答案/私有映射不暂存。公开导出后一次临时日志脚本
参数错误已记录并独立复验现有文件，没有覆盖重导出；正式工程和输出身份未受影响。发布审计又发现 SVG path 行尾空白导致 cached
whitespace 检查失败，独立适配器仅规范化公开 SVG 并更新其映射，不禁用守卫、不重生成正式报告。
相关公开文件、发布脚本与测试由 `.gitattributes` 固定为 LF，保证启用 `core.autocrlf` 的新 checkout
仍能复验版本 2 文件 SHA；PNG 未声明为文本。

## 8. D6 接续边界

D6 后续工作是展示排版与兼容性冻结、最终 PDF/交付 manifest、60–90 秒录屏、两次计时演练及
失败降级材料。所有这些尚未启动。本轮不自动接续，不把草稿称最终答辩版，不修改固定研究
协议、样本、指标、案例或人评。D5 已达阶段验收；完整 Defense MVP 仍需 D6 展示交付。
