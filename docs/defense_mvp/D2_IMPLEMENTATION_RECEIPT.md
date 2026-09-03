# Defense MVP：D2 实现回执与 D3 接口

更新：2026-09-03。实验：`DEFENSE-MVP-v01`。环境：本地 Windows、CPU-only。
本文记录真实 E0 媒体上的工程测量，不是人评结果，也不是 E1/E2 研究结论。
测试与发布状态以 `DEVLOG.md` 末尾的逐步回执为准。

## 1. 已完成与尚未完成

- 已完成：限定兼容接收、不可覆盖 ingest、F/P/T/Q、N=1/2/4 平衡设计、三方法选择。
- 已完成：35/35 定量候选评分；15/15 定性候选验证帧解码且分数为 null。
- 已完成：35 个 trial、105 个嵌套子集、315 条选择记录、42 个比较计划。
- 未开始：正式双人标注、聚合统计、win rate/置信区间、最终 slides 和录屏。

D2 不要求 Proposed 胜出。不要把 CPU 代理均值、选择次数或 automatic tie 当成人类偏好。

## 2. 只接受这一个兼容包

`--compat-profile server-agent-20260902-v01` 固定绑定外层 tar、manifest、SHA 清单与
verification 的 SHA-256；未知档案或任何身份漂移硬失败。默认严格模式不变。

已验收的媒体：10 个 sample、50 个 candidate、60 个 MP4、160 张 source frame、
160 张 mask、800 张 candidate frame。tar 有 1265 个常规文件、无目录/链接等特殊项，
展开 481,708,044 bytes；manifest payload 为 1259 文件、480,920,099 bytes。

允许的四类偏差只限于本包：

1. tar 没有顶层 package 目录（仍保留 media/metadata 相对层级）；
2. `PACKAGE_VERIFICATION.json` 的一处已知 checksum 漂移；
3. verification 无 status，但 v1–v15 全 pass、failures=[]、ready_for_transfer=true；
4. manifest 帧数组转 FrameSet，计算候选 combined checksum，重排固定 7+3 和 seed 顺序。

原始 tar、sidecar、解包后的控制文件与媒体全部保持原样。规范化只写入独立 ingest。
两个 `compatibility-receipt.json`（raw 目录旁和 ingest 内）保存原始/实际指纹、checksum
偏差和规范化说明；完整原始控制文件保留在 raw。原包额外 warnings/缺失可选项均为空。

| 身份 | SHA-256 |
|---|---|
| tar | `0aa0bd951f4609ef779013d78e424fa373201823a8e16e29cbdd070f3a66abdb` |
| sidecar 文件 | `5155e42e63ffde4fb079c8bef6897e9a0f834db16cd14d35b4c79687d8e034cd` |
| 原始 manifest | `6c41bdd0f4d8c35445a2ce6fa26a7d9606226ea5aefb9c1888318ee5d4a4856e` |
| 原始 SHA 清单 | `1ce2e1b87838092e0382489d6ac983c784f6f0fc088d3c29c642c69997e48be5` |
| verification 清单声明值 | `548fa36552d18a139490d3dee0fbf0304389e9e2684d790a12ed86f8dadbeff3` |
| verification 实际值 | `2c6477c7ae1f66f8af17f8cd81ad1dfc11b0e25d90d6a56bfed79cf1f18bafcc` |

没有媒体校验失败，不需要重新索取约 484 MB 服务器包；本地没有连接学校服务器。

## 3. 冻结指标与能力边界

协议 `cpu-fptq-v1`，NumPy/Pillow，不加载深度模型。16 帧完整计算，没有抽样缩减。

- F：mask 内 RGB MAE 与 HSV 目标色支持度的几何平均；三个 local 任务排除 source
  已经属于目标色的像素。它是颜色编辑代理，不能验证背包/头盔等对象真的出现。
- P：1 减 mask 外 RGB MAE；前景内非目标部位的破坏不一定被 P 捕获。
- T：1 减相邻编辑残差 MAE；另存相邻 mask 并集内/外值。无光流或运动补偿。
- Q：梯度保留、正常曝光比例、亮度残差稳定性的几何平均，不是感知质量模型。

DAVIS palette mask 必须按非零类别索引解码，不能转灰度再阈值化；所有前景类别取并集。
真实 160 张 mask 覆盖率约 0.0105–0.7760，均在冻结边界 [0.001,0.95] 内。
local mask 是前景对象而非目标子部位，不能宣称精细定位能力。

15 个对象转换候选的 `measurement_status=qualitative_only`，scores/components/per_frame
均为 null；不进入排序与定量主表。其图像和 source/masks 仍经过尺寸、模式和解码验证。
MP4 做身份 checksum 验证；D2 不重新解码 MP4 验证播放效果，D3 另做浏览器播放验收。

| 维度 | 最小 | 均值 | 最大 |
|---|---:|---:|---:|
| F | 0.2450 | 0.3794 | 0.5149 |
| P | 0.6324 | 0.8578 | 0.9271 |
| T | 0.8342 | 0.8829 | 0.9225 |
| Q | 0.7341 | 0.8847 | 0.9714 |

检测到 14 个异常帧（计入候选内计数），全部保留，没有据此删除帧或候选。
上表仅是 35 候选代理分分布，不证明某方法更好。

首次成功评分约 27.67 秒；最终加入全部定性帧解码验证后的复跑约 52.35 秒。
回执字段 `total_cpu_seconds`/`cpu_seconds` 实际使用 perf_counter，表示 CPU-only
流水线的经过时间，不是进程 CPU 核时，也不是 GPU 生成时间。

## 4. 选择与比较计划

每个定量 sample 按 seed 101/202/303/404/505 做 5 次循环位移，每个位置恰好覆盖所有
seed。N=1/2/4 取同一排列前缀。rank-percentile 按原始值、candidate_id 升序生成
`rank/(N-1)`；N=1 记 1，同值按 ID 决胜，不使用平均秩。

random、equal-linear、constrained-pareto 各有 105 条记录。Proposed 先对 rank 分执行
F 中位数/P 25% 分位门槛（线性分位数），再取 Pareto 前沿，按 max-min、几何平均、ID
决胜；空集按 min(F,P)、T、Q、ID fallback。

- 26 次 fallback，全在 N=2；N=1/N=4 没有 fallback。这是小子集 F/P 冲突的真实现象，
  不通过改阈值消除。
- 28 项 Proposed N=4 vs N=1，其中 6 项相同媒体；14 项 Proposed vs Linear N=4，
  其中 4 项相同媒体。
- 共 10 项 automatic tie，42 项全部保留。每位标注者需实际观看 32 项；两人各自仍
  必须形成完整 42 项 coverage。automatic tie 不伪装为人类实际作答。

`comparisons.json` 当前是含方法身份的后台 X/Y 规范计划，**不是可直接展示的盲评页面**。
D3 必须将方法、seed、N、分数、candidate_id 与带身份的文件路径从评审可见内容中移除。

## 5. 产物与确定性身份

根目录：`artifacts/defense_mvp/DEFENSE-MVP-v01/`（Git 忽略）。

| 产物 | SHA-256 |
|---|---|
| `configs/defense_mvp/pilot.yaml`（仓库内） | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |
| `ingest/normalized-manifest.json` | `b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46` |
| `metrics/metrics.jsonl` | `c9828aaec312187fafa2e7f5d6a6c77170cb2ff7caf23d9ada8218d440515dac` |
| `metrics/metrics-summary.json` | `7f5f6f3e008dfdccf29e21e31f17ba933dd9416eb053c5c0458491742cedd9a8` |
| `metrics/metrics-config-lock.json` | `65b3ec0124e32703ca6e1046c9c460d0e1af383d19690c9693e75754cf1e74f7` |
| `design/design.json` | `891ee8b0d75acf5c825fd01d529d545f12a7fb1b72a4310364a805d8d6cd1ff5` |
| `selection/selections.jsonl` | `aae1410de8d9d90c1266c43cadf17f1fce8666bdc163b709d82504689b38afaf` |
| `selection/comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| `selection/selection-summary.json` | `2cf97da4f8bf704bbd7d2d9e62f1e8237873db89a805aefc168266133b115f3f` |
| `selection/selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |

`metrics-replay-v01`、最终 `metrics-replay-v02` 的三个核心 metrics/summary/lock 文件与
主产物逐字节一致；`selection-replay-v01` 的四个核心文件同样一致。计时/运行回执有意
单独存储，带计时的整目录 SHA 清单不要求跨次相同。

这些 SHA 对应当前本地路径和冻结输入。搬到另一台电脑后，包含 delivery_root 的 ingest/
design/comparison 文件身份会变化；必须在新目录重建并保留新的关联锁，不能伪称原 SHA。
原始媒体 SHA 和同环境同配置的数值计算仍应可复验。

## 6. 使用与重建

已有正式目录不要再次写入。先只读检查：

```powershell
uv run defense validate-config
uv run defense verify-delivery --delivery data/raw/defense_mvp/e0-delivery-v01 --compat-profile server-agent-20260902-v01
uv run pytest tests/defense_mvp -o addopts='' -q
```

从既有 ingest 做完整复跑的示例（`manual-replay-v01` 必须尚不存在）：

```powershell
uv run defense score --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/metrics
uv run defense design --metrics artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/metrics/metrics.jsonl --ingest artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json --output artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/design
uv run defense select --design artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/design/design.json --metrics artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/metrics/metrics.jsonl --output artifacts/defense_mvp/DEFENSE-MVP-v01/manual-replay-v01/selection
```

若从 tar 重建，则使用全新的 raw 与 ingest 目录，两步均显式传固定兼容档案；不修改原包。
全仓回归：`uv run pytest -o addopts='' -q`；静态检查：
`uv run python -m compileall -q src tests` 和 `git diff --check`。

## 7. 下一段施工：D3 双人盲评

输入只使用本回执锁定的 `selection/comparisons.json` 和原始只读媒体。优先验收：

1. 本地 source/A/B 同步播放、拖动和 Range 请求；采用不带身份的媒体 URL。
2. annotator-a/b 在同一电脑分开会话；独立 A/B 方向与顺序，禁止展示累计结果。
3. overall/F/P/T/Q 各项 A/B/tie/uncertain、confidence、notes、时间和 checksum。
4. 自动保存/断点恢复/no-replace，不串写两位评审；10 项自动平局有独立来源标志。
5. 42 项 coverage、媒体身份和方向映射的 tiny fixture/浏览器验收通过后，才邀请正式作答。

D3 不得用已经看到的选择统计调 F/P 门槛，也不提前报告人评胜率。
