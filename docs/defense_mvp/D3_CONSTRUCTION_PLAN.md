# D3 本地双人盲评详细施工方案

日期：2026-09-03；环境：本地 Windows / CPU；协议：`defense-blind-v1`。
停止点：工程验收通过，可邀请真人标注。正式作答由用户启动，施工期间为 0 条。

实施状态：D3.1–D3.5 工程验收通过。最终 Defense 115项、全仓218项通过；双人64条
practice完整演练与真实浏览器验证完成。正式会话/人答为0；详见实现回执和标注指南。

## 现场与输入

实际交接文件为 `docs/defense_mvp/D3_IMPLEMENTATION_AGENT_PROMPT.md`。
main/HEAD/origin/main 初始均为 d5ae95e5f35320ad3d749b637db63197c77a519e。
保留已有 DEVLOG 回执、交接文档、未跟踪 tar/sidecar；后两项不得暂存。
D2 已交付 10/50、35 scored/15 qualitative_only、315 selections、42 comparisons。
已核对 pilot、ingest、comparisons、selection-lock 四项 SHA 与 D2 回执一致。
不重新解包、评分或选择。prepare 补充核对全部关联清单、锁和引用媒体。

## D3.1 包与输入门禁

新增 `annotation_models.py`、`annotation_bundle.py` 与 `annotation-v1.yaml`。
严格模型拒绝额外字段；Comparison、Display、Answer、Session、Coverage 各自建模。
formal 模式绑定 D2 已验收的 pilot/ingest/comparisons/selection-lock SHA；practice 使用
同一协议与身份检查，但永远带 practice 来源，正式 verifier 拒绝。
读取 selection/metrics/design/ingest 各 SHA256SUMS，核对跨目录 SHA 链、7+3 和
50 个候选矩阵；核对 35 trial/315 selection 的角色、子集、视频；42 个 comparison
必须精确覆盖 7 sample × (4+2)，指令/source/candidate/路径/SHA 与 ingest 相符。
重新读取媒体计算 SHA，自动平局只由 X/Y 视频 SHA 相等决定；formal 必须 6+4 ties。

包通过 staging + no-replace 发布，失败 staging 保留。包中包括：
`bundle.json`（模式、输入路径/SHA、协议/配置、原始 42 比较）、`private-mapping.json`、
`automatic-ties.json`、`prepare-receipt.json`（Git HEAD、Defense 源码与依赖文件 SHA、
Python/平台/依赖版本、时间）、`SHA256SUMS`。全部放忽略目录，无 HTTP 静态目录服务。
bundle 身份是 bundle.json 的 SHA；映射独立 SHA 写入 bundle.json。

哈希输入为 UTF-8 JSON，sort_keys=True，ensure_ascii=False，分隔符逗号/冒号，无空格。
direction/order 使用不同 purpose，域包含 protocol、seed=20260901、annotator_id、
comparison_id。每类别非自动题按 (direction hash, comparison_id) 排序，前一半 X→A，
后一半 X→B，真实数据为 11/11 和 5/5。独立 order hash 排序全部 32 题。
自动题没有 direction。映射只留服务端；HTTP 的题句柄每次启动/展示随机产生。

## D3.2 会话与存储

新增 `annotation_store.py`。只接受 annotator-a/b；会话目录名称必须对应身份，
元数据锁定 bundle SHA、protocol SHA、mode、annotator、session UUID。
一次进程仅打开一位；普通启动遇到已有目录拒绝，恢复必须 `--resume`。
单写采用内核文件锁（Windows msvcrt / POSIX flock），不是仅凭 PID 判断存活。
锁文件保留，owner 信息为诊断；恢复先抢内核锁，再严格检查已有 session/records/drafts。
中断释放内核锁；未知目录/损坏元数据拒绝，绝不删除未知锁。

每题正式事实源 `records/<顺序号>.json`，先 fsync 临时文件，再原子 no-replace rename。
正式记录不可变，包含屏幕答案、canonical X/Y、五维、confidence、notes、方向、
comparison 与媒体身份、服务端 UTC、会话/包身份、request_id、内容哈希。
同 request_id 同内容重试返回原记录；不同内容或另一标签页重复题返回冲突。
草稿采用独立 draft 文件、版本 compare-and-swap；原子 replace 仅允许草稿，绝不覆盖正式记录。
未发布临时文件保留用于诊断，但不作为答案；任何损坏已发布记录拒绝恢复。
计时记录本次服务端展示至提交的 elapsed，重启前/隐藏页/空闲不能宣称精确人工成本。

## D3.3 本地 HTTP 与界面

新增 `annotation_server.py`、`annotation_ui.html`。标准库 HTTPServer，固定 127.0.0.1。
启动令牌由 secrets 产生；一次性 entry 换取 HttpOnly SameSite=Strict 会话 cookie；
写 API 校验 Host、Origin 和 CSRF；每次重启轮换，旧会话与串会话均拒绝。
一次性 /entry/<令牌> 换取 HttpOnly cookie；每次启动独立 cookie 名称和 Path。
页面、API、媒体均限定在 /review/<随机启动标识>/ 下，旧页不能访问下一次会话。
该前缀内仅精确路由 /、/api/current、/api/draft、/api/submit、/api/media-state、
/media/<随机句柄>/<source|A|B>。
只提供当前未完成题允许的媒体；无目录、路径参数、任意下载或方法身份字段。
错误仅使用固定匿名错误码/中文说明，服务端不回传异常路径。
Range 支持完整、闭区间、开区间、suffix；无效或多段返回 416。

三视频统一播放/暂停/重播/拖动，保留单独 controls。统一播放以 source 为基准，
定时校正超过 0.12 秒偏差，属于浏览器近似同步，不承诺逐帧同步。
媒体加载/解码错误禁用提交；三路 loadeddata 和至少一次播放事件后才允许确认。
服务端校验媒体已成功请求并接收当前 view 的 ready 状态，提交再核对媒体 SHA。
五字段均主动 A/B/tie/uncertain，无预填；confidence 主动选 0/.25/.5/.75/1，
说明为无法确信/较低/中等/较高/很高；notes 最多 1000 字符，以 textContent 展示。
提交前确认，成功落盘后前进；网络失败保持原 request_id 和内容供幂等重试。
草稿自动保存可恢复，不属于正式答案。提交使用页面内二次确认，支持返回修改；
原生 confirm 在浏览器控制接口实测阻塞，已替换。页面不显示方法累计表现或切换身份入口。

## D3.4 导出与校验

新增 `annotation_export.py`。持有同一写锁读取并重新验证全部记录。
新目录 staging + no-replace 导出 `answers.jsonl`（comparison_id 排序）、
`coverage.json`、session 元数据、共享 automatic-ties、receipt 和 SHA256SUMS。
导出是不可覆盖的封存快照；不完整快照标 incomplete，原会话仍可继续，后续导出新目录。
32 人答 + 10 系统条目构成单人 42 coverage。双人需身份正好 a/b、同包同模式，
两人回答集合完整且一致，合计 64 人答 + 10 共享系统项。不产生 84 人答。
verifier 复验 checksum、严格模型、记录方向/来源/媒体/时间、集合和自动平局规则，
区分 invalid（退出非零）、incomplete 和 complete；practice complete 不代表 formal。
不计算胜率、kappa、BT、bootstrap，不更改已有双人分歧规则。

## CLI 与目录

所有命令从仓库根运行，CLI 文档/--help 同步：

```text
defense prepare-annotation --selection DIR --ingest FILE --output NEW --mode formal|practice
  [--metrics DIR --design DIR --config annotation-v1.yaml --pilot pilot.yaml]
defense annotate --bundle DIR --annotator-id annotator-a|annotator-b --output DIR [--resume] [--port 8765]
defense export-annotations --bundle DIR --session DIR --output NEW
defense verify-annotations --bundle DIR [--export DIR ...] [--allow-practice]
```

预定新目录根 `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/`：formal-bundle、practice-bundle、
practice/annotator-a 与 b、practice-exports；未来 formal/annotator-a 与 b 保持不存在。
浏览器证据在该根 output/playwright/，属于忽略目录。失败目录保留，不原地重跑。

## D3.5 验收矩阵与发布

### 浏览器编码兼容性细化（2026-09-03 首次实测后）

真实 source 为 H.264，候选为浏览器不支持的 mp4v。D3 展示包使用全路径一致的
`lossless-vp9-yuv420p-v1`：既有 ffmpeg CPU 解码后 VP9 lossless，保留 16 帧、8fps、
512×512；逐帧解码 RGB24 SHA 和精确帧时间必须与原媒体一致。只生成新的私有
presentation 副本，原始 MP4/帧/D2 全部只读。source 与候选均按同一规则处理。
自动平局仍比较原始视频 SHA；正式记录同时保存原始身份与展示身份，包保存转换命令、
工具 SHA/版本与逐帧等价证明。此项解决浏览器解码兼容性，不改变研究比较或评分协议。
tiny fake 测试显式 `--fixture-native-media`，只允许 practice；正式包必须无损展示。
首次 qa-initial 不可播放包保留，不复用为最终交付。

| 风险 | 必须证据 |
|---|---|
| 输入漂移 | manifest/锁/媒体漂移、42 唯一性、角色/类别/qualitative、假自动 tie 拒绝 |
| 随机化 | 重复一致、无丢题、真实 11/11+5/5、两方向所有四种答案映射 |
| 存储恢复 | fsync/rename 故障、幂等/冲突、双标签页、双进程、残锁、损坏记录/草稿、错误 resume |
| 匿名与边界 | HTML/JSON/URL/header/error 无方法、无路径；token/origin/traversal/旧会话拒绝 |
| 表单与播放 | 非法/缺字段、confidence、notes 注入、身份篡改、Range、真实浏览器 seek/replay/pause/解码错误 |
| coverage | 缺题、重复、同人、不同包、practice 混入、假自动 tie 不得 formal complete |
| 真数据 | 只读媒体 checksum 前后不变，formal 42/10/32，正式答案为 0 |

先里程碑定向测试并立刻记 DEVLOG，最终冻结源码后 Defense 全套 + 全仓 pytest，
CLI smoke、compileall、diff check。隔离 practice 演练完整双人导出；真实只读媒体播放
用 practice 会话且不生成正式答案。浏览器工具先按技能连接，缺失再安全替代。
交付 ANNOTATION_GUIDE、D3_IMPLEMENTATION_RECEIPT、更新总施工方案；明确开发者评审
披露、同机配合式盲评边界、计时限制、退出/恢复/正式启动/导出命令。
按显式文件 allowlist 审计 path/binary/size，fetch 核对远端后审计提交并普通 push main。
最终发布回执允许唯一 tracked 未提交项为 DEVLOG。不会自动继续 D4。
