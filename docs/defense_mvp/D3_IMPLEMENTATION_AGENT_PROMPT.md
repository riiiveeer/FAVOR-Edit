# D3 本地施工：新对话交接提示词

交接快照：2026-09-03。以下是给承接 agent 的完整任务指令；用户让你阅读并执行本文时，按本地施工任务处理，不只复述方案。

## 1. 任务、授权与停止点

请在 `D:\lab idea` 承接 Defense MVP，完成 D3 本地双人盲评工程。项目暂定题目为“基于约束式多目标排序的指令视频编辑候选选择与盲评系统”，总交付日为 2026-09-08。两位评审是项目开发者本人和另一位同学，先后使用同一台 Windows 电脑。

先核对现场，把 D3 的数据模型、CLI、文件状态和验收方案写成详细施工文档，然后直接分阶段实现、测试、记录和发布。普通接口/实现细节自行选择，不反复询问已明确的需求。只有身份校验失败、无法保留的重叠改动、真正缺少必要权限或必须改变实验协议时才停下来说明证据并询问。

沿用根目录 AGENTS.md 中 Defense MVP 的本地 CPU 开发、审计提交、普通推送 main 授权。此次只实现 D3：不得扩大到 D4 统计、训练模型或为结果调参。默认单 agent 执行，不自行创建新对话、自动任务或远程工作。

本次终点是“工程验收通过，可以邀请真人开始标注”，不是“正式人评完成”。你可以用隔离的练习数据测试，但不得代替两位评审生成正式答案，不得自动开启正式作答或声称已有真实人评胜率。

## 2. 首轮核对：必要上下文而非重做 D2

按顺序阅读并核对：

1. `D:\lab idea\AGENTS.md` 及适用的目录级规则。
2. `D:\lab idea\docs\DEFENSE_MVP_CONSTRUCTION_PLAN.md`，重点是盲法、标注字段、双人分歧处理、截止日期和禁止边界。
3. `D:\lab idea\docs\defense_mvp\D2_IMPLEMENTATION_RECEIPT.md`。
4. `D:\lab idea\DEVLOG.md` 末尾及与 D2 相关的必要记录；不要一开始反复输出整个长文件。
5. `D:\lab idea\src\defense_mvp\` 中的 models、io、cli、selection、design、ingest，以及相关测试和 pyproject.toml。
6. 只读检查下面列出的真实输入与身份锁。按需要读取 E1/E2 的纯工具函数，但不套用它们的正式协议。

本提示词记录的是交接快照，不替代实际检查。先检查 git status、branch、HEAD、origin/main。如果新对话开始时已有后续提交或 D3 改动，识别并接着做，不 reset、不覆盖、不强行回到旧基线。

交接时：

- 分支 main；HEAD/origin/main 均为 `d5ae95e5f35320ad3d749b637db63197c77a519e`。
- D2 功能提交 `94a67799a31fa5c9eb0753de0a9869be2b1d1222`，发布回执提交 d5ae95e。
- DEVLOG 有允许保留的未提交最终发布回执；本提示词也是本次交接新增的本地文档，都要保留。
- 根目录 `DEFENSE-MVP-E0-HANDOFF-v01.tar` 和 `.tar.sha256` 未跟踪，禁止暂存。data/raw 与 artifacts 已被忽略。
- D2 最终源码全仓 130 项通过，补强后的 Defense 39 项另行通过，联合覆盖当时最终 collection 的 142 项；不是一次“142 passed”的历史运行。D3 结束后重新跑最终全仓回归。
- D3 的上一版计划只在聊天中讨论；本文补齐其交接内容，不能假设任何 D3 命令已经存在。

首次对用户简短报告：已存在什么、剩余什么、工作树有无冲突、准备从哪个 D3 子步骤开始。不要无条件重新解包、重新评分或重新选择，也不要要求再次下载已完整的服务器包。

## 3. 冻结输入与真实数量

工作区根目录为 `D:\lab idea`，下列路径均相对该根目录：

- 只读媒体：`data/raw/defense_mvp/e0-delivery-v01/`。
- 规范化输入：`artifacts/defense_mvp/DEFENSE-MVP-v01/ingest/normalized-manifest.json`。
- 评分：`artifacts/defense_mvp/DEFENSE-MVP-v01/metrics/`。
- 设计：`artifacts/defense_mvp/DEFENSE-MVP-v01/design/`。
- 选择、比较及锁：`artifacts/defense_mvp/DEFENSE-MVP-v01/selection/`。

至少固定核对：

| 输入 | SHA-256 |
|---|---|
| `configs/defense_mvp/pilot.yaml` | `19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae` |
| `selection/comparisons.json` | `486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb` |
| `selection/selection-lock.json` | `99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2` |

其他输入/产物 SHA 见 D2 回执及各目录 SHA256SUMS。prepare 阶段必须核对关联锁、42 项比较与选择/ingest 的 sample、candidate、source、路径和媒体 SHA 关系，不能仅检查上表三个文件。不得修改锁来“接受”漂移。

已完成：10 sample、50 candidate、60 MP4、160 source frames、160 masks、800 candidate frames；35 个候选有 F/P/T/Q，15 个对象转换候选为 qualitative_only，不进入正式定量盲评；315 条选择记录。

固定比较计划：

- 28 项 Proposed N=4 vs N=1，其中 6 项自动平局、22 项需人工观看。
- 14 项 Proposed vs Linear N=4，其中 4 项自动平局、10 项需人工观看。
- 合计 42 项，每人实际观看 32 项，10 项共享自动平局。
- 自动平局只由两侧视频 SHA 相等确定，重新核对，不盲信 JSON 的布尔标志；不同文件即使看起来相似也不能自动记平局。
- 26 次 Pareto fallback 全在 N=2，是应保留的真实现象，不是 D3 要修掉的算法问题。

兼容 profile 仍为 `server-agent-20260902-v01`，仅绑定原包。确需只读复验时使用既有 verify-delivery 命令及该参数；默认严格模式不得放宽。

## 4. D3 必须实现的行为

### 4.1 独立盲评包与协议锁

新增 Defense 专属的 comparison/annotation/session/coverage 严格模型，以及独立的 `configs/defense_mvp/annotation-v1.yaml`。不修改已评分的 pilot.yaml、原始 comparisons、D2 输出、评分和选择公式。

在正式人评前固定：字段与说明、confidence 编码、方向/顺序算法、草稿与正式记录状态、提交重试和恢复规则。使用版本化 `defense-blind-v1` 协议与明确的输入/配置/展示映射锁。prepare 输出 staging + no-replace，并保存源码版本、依赖/环境证据和运行回执。

### 4.2 匿名展示与确定性随机化

- 浏览器只看到当前进度、指令、原视频、A/B 和表单，不看到方法、N、seed、CPU 分数、candidate_id、原始路径、后台 X/Y 映射。
- 现有 comparison_id 含方法名；不能把它放进 DOM、隐藏 input、URL、JS、API 响应、错误信息或下载文件名。
- 使用不透明的服务端映射和会话绑定媒体 URL；只服务当前会话允许的媒体，禁止目录浏览和任意文件读取。不得直接暴露公开可逆映射或将完整比较计划发给客户端。
- 使用固定 seed=20260901；分别按 annotator_id、comparison_id 和 purpose 派生确定性哈希。方向与题序使用不同 purpose；具体规范写入协议锁。
- 在各比较类别的非自动平局项内按方向哈希排序，一半 X 显示为 A，另一半 X 显示为 B：22 项分 11/11，10 项分 5/5，每位评审共 16/16。相同输入复跑和恢复时方向不变。
- 题序使用独立哈希排序；两位评审独立生成，不要求每一题都反向。自动平局不加入 32 项显示队列，不伪造显示方向。

### 4.3 同机双人隔离与本地服务

- annotator-a/b 分别绑定独立会话和输出目录，一次启动仅服务一位评审；不提供页面内切换身份或读取另一人的答案。
- 仅绑定 127.0.0.1；无需云服务、部署、外部 API 或账号系统。使用合适的会话令牌/请求来源校验，拒绝串会话、旧会话和越权写入。
- 同一正式目录只允许单个写进程；锁恢复规则要能区分活动进程与中断遗留锁，不能直接删除未知锁。
- 前一位退出后关闭页面和服务，再启动另一位；不展示累计结果和方法表现。
- 这是配合参与者的盲评流程，不宣称防止本机管理员主动读文件；报告应披露其中一位是项目开发者，不把“双人盲评”夸大为“双盲实验”。

### 4.4 播放与判断表单

- 使用本地 Python 服务和轻量 HTML/CSS/JS；先追求可靠桌面使用，不引入不必要的大型前端框架。
- source/A/B 同步播放、暂停、重播、统一拖动，并允许单独查看；说明同步精度，支持浏览器所需的完整/分段媒体读取。
- 核对真实媒体播放与拖动。媒体错误时阻止提交并给出不泄漏身份的诊断；不能用 uncertain 替代播放失败。
- 五字段：overall、faithfulness、preservation、temporal_consistency、visual_quality；每项主动选择 A/B/tie/uncertain，不预填判断。
- 人按指令和视觉判断，不显示 CPU 公式或要求其模仿颜色代理。明确 tie 是可比较但无明显偏好，uncertain 是不能可靠判断。
- confidence 使用明确冻结的 [0,1] 编码，由评审主动填写/选择；notes 可选并限制长度；提交前可修改，确认提交后只读。
- 服务端重新验证字段、身份和方向，保存屏幕答案及 canonical X/Y 答案；不信任客户端传入的 candidate、方法、checksum 或 annotator 身份。
- 保存真实服务端时间和可解释的耗时；恢复会话造成的空闲时间与观看时间不要混称为精确人工成本。

### 4.5 保存、恢复与封存

- 区分可恢复草稿和已确认正式回答；草稿不得进入统计或覆盖正式回答。
- 正式回答逐题原子落盘，持久化成功后才显示“已保存”并前进。可用每题不可变文件作为事实源，最后导出 JSONL，避免直接 append 导致半行损坏。
- 同一请求/相同内容重试保持幂等；重复提交不同内容、双标签页竞争必须明确拒绝，不新增重复答案。
- 刷新、重启、崩溃后只恢复本人的相同输入/协议会话，校验全部已有记录后回到未完成题；损坏或身份冲突不得静默跳过。
- 明确 --resume；已有目录不能被普通启动覆盖。MVP 已提交答案只读，误操作先记录并核实，不偷偷改写或用 AI 改答案。
- 导出排序确定的 no-replace JSONL、checksum、coverage 与运行回执；封存后再次导出用新目录。

### 4.6 自动平局与 D4 接口

- 每人最终原始人答 JSONL 为 32 条；另有 10 项共享自动平局清单，来源标记为 automatic_tie/media_identity，无伪造的人答、confidence、人工时间。
- 覆盖验证按“32 个人工 comparison ID + 10 个自动 comparison ID = 42”检查每位评审；两人的待答集合相同，顺序/方向可不同。
- 最终应是 64 条真人回答 + 10 条共享系统规则记录，解释两份 42 项 coverage，不能声称 84 条真人回答。
- 不更改既定双人分歧聚合规则；D3 只给 D4 提供可验证的原始记录、方向、来源和身份链，不计算人评胜率、kappa、BT 或 bootstrap。

## 5. 实施顺序与产物

先创建 `docs/defense_mvp/D3_CONSTRUCTION_PLAN.md`，把实际模型、目录、CLI、锁/恢复语义和测试矩阵写清，然后按下列里程碑执行：

1. D3.1：输入验证、独立配置/模型、匿名包、确定性映射。
2. D3.2：单写进程、逐题记录、草稿/正式分离、幂等、断点恢复。
3. D3.3：匿名媒体路由、Range、播放与桌面表单。
4. D3.4：导出、自动平局、双人 coverage、封存 verifier。
5. D3.5：隔离练习流程、真实只读播放验收、完整回归、文档与审计发布。

拟新增 CLI（目前不存在；可调整参数但必须文档一致）：

- defense prepare-annotation：接收冻结 selection 目录、normalized ingest，输出新盲评包。
- defense annotate：指定包、annotator、独立会话目录，可显式 --resume。
- defense export-annotations：从确认记录导出新目录。
- defense verify-annotations：校验包、单人或双人输出，明确 incomplete 与 complete 状态。

模块限定在 src/defense_mvp；测试在 tests/defense_mvp。可通过窄接口复用已测试的 read_media_range 等纯函数，不能修改 E1/E2 或复用它们的 80 项/第三人裁决门禁。

prepared bundle、private mapping、练习会话和未来正式会话放在 artifacts/defense_mvp 下的独立新目录，明确 practice/formal 标记。练习答案永远不能被正式 verifier 接受，不覆盖 D2 或任何历史失败目录。

另交付 `docs/defense_mvp/ANNOTATION_GUIDE.md` 和 D3_IMPLEMENTATION_RECEIPT.md；更新总施工方案中已实现 CLI 和阶段状态。不要只留下聊天说明。

## 6. 测试与验收矩阵

实现之后逐项提供证据：

- 输入：manifest/lock/媒体漂移、42 项数量/唯一性、类别/角色错配、自动平局真假、qualitative 候选越界均拒绝。
- 随机化：两类分别 11/11 与 5/5，同输入同评审复跑一致；题序不丢题重复；X/Y 与 A/B 的全部组合含 tie/uncertain 映射正确。
- 匿名化：检查 HTML、JSON、URL、headers、报错与可访问路由；不能仅检测可见文字。越权 token、遍历路径、串会话访问拒绝。
- 表单：缺字段/非法枚举/越界 confidence/过长 notes/注入文字、客户端篡改身份或方向拒绝或安全处理。
- 存储：断电式中断模拟、持久化失败、重复请求、冲突请求、双标签页/双进程、残留锁恢复、损坏记录、错误 --resume、已封存输出覆盖。
- 播放：有效 Range/错误 Range、seek/replay/暂停/同步、媒体不存在/不能解码时阻止提交；使用真实浏览器做端到端检查，并保存证据到忽略目录。
- 覆盖：一份缺题、两人身份相同、重复题、不同包混用、将 practice 混入 formal、伪造自动平局，都不能得到正式 complete。
- 真实数据：只读校验全部引用媒体；正式包是 42/10/32，人工答案初始仍为 0。完整人答导出/coverage 流程用隔离 fixture 演练，不为了测试完整状态写正式答案。

注意：已有 handoff_factory 的媒体有 tiny fake 字节，仅适合身份门禁测试，不一定能被浏览器解码。播放测试必须另用可播放 fixture 或真实只读媒体。pytest 曾因不同目录同名 test_metrics.py 收集冲突；新测试命名先检查现有文件。

使用环境中可用的浏览器工具，并先阅读适用 skill；浏览器工具缺失时先找安全的可用替代，不得把静态 HTML 测试冒充真实播放验收。不能完成的验证须明确列为未通过。

最终运行 Defense 定向测试、最终源码状态的全仓 pytest、CLI smoke、compileall、输入前后 checksum、git diff --check 和 staged path/binary/size guard。历史通过记录不能代替本次回归；记录实际命令、数量、耗时、退出码与诊断。

## 7. 不可越过的边界与工作纪律

- 只在本地 CPU 工作；不连接学校服务器、不读写 DATA4、不加载真实 judge/视频生成模型、不做 GPU 工作。
- 不改 sealed E0、E1/E2 门禁、D2 指标/选择/候选/42 项计划，不调阈值追求正结果。负结果与自动平局都保留。
- DEVLOG 每完成一个可验证开发/测试/实验/协议细化步骤立即追加；失败或中断也记录。包含时间、环境、步骤 ID、行动/配置、结果、产物和下一步，禁止最后一次性补账。
- 保留现有未提交改动。文件编辑用 apply_patch；输出 staging + no-replace，恢复与草稿行为须明确区分，不能通过删除旧目录重跑。
- 不把 tar、sidecar、媒体、private mapping、会话令牌、原始人答或实验目录加入 Git；发布只用明确路径 allowlist，不用 git add .。
- 完成 D3 验收后，按既有授权创建审计提交并普通推送 main；若远端前进先核对，禁止 force-push/重写历史。记录 push receipt，允许最终 DEVLOG 回执留作唯一未提交 tracked 修改。
- 若必须修改本提示词的研究边界，先说明为何、受影响文件和证据，再请求用户方向；一般工程实现选择无需逐项请示。
- 中断恢复时从 DEVLOG、真实文件和回执确认下一步，不重做已经通过且代码/输入未变的步骤。只有所有 D3 验收完成或真正需用户决策的阻碍时结束，不把“代码写完”当作交付。

## 8. 最终向用户交付

用中文简洁说明：已完成项、实际测试与浏览器证据、提交/推送身份、剩余风险；链接详细施工方案、标注指南与实现回执。

给出可复制的练习启动、退出、恢复、正式 annotator-a/b 启动、导出及 verifier 命令；命令中的目录必须与真实已验收产物一致。首次正式启动由用户执行或明确要求后再操作。

最后明确：D3 工程是否 ready；正式人工回答有多少（本次施工应仍为 0）；用户接下来需要做什么。不要自动继续 D4，也不要说整个 Defense MVP 已完成。
