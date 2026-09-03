# D3 双人独立盲评操作指南

协议：`defense-blind-v1`。本指南仅覆盖本地标注和原始记录导出，不做 D4 统计。
工程施工中的 64 条测试回答全是 practice 固定值；正式人答仍为 0。
先阅读 D3_IMPLEMENTATION_RECEIPT 的最终验收状态，再邀请两位评审。

## 参与方式与判断

两位评审为开发者本人（annotator-a）和另一位同学（annotator-b），先后使用同一台电脑。
不要交换身份，不讨论具体比较，不查看 private mapping、选择分数或另一人的答案。
一次只开一个服务和一个作答标签页；前一位关闭页面并退出服务后再交接电脑。
页面无身份切换功能，也不展示方法表现。此为配合参与者的独立盲评，不能称为“双盲实验”，
也不防止本机管理员主动读取文件。报告须披露开发者参与和此前对数据的接触。

每人实际观看 **32 题**；另有 **10 项共享的媒体同一性自动平局**，无需作答。
每人覆盖 42 项；最终应有 64 条真人回答和 10 条共享规则记录，不是 84 条真人回答。
两人题目集合相同，顺序/方向独立固定；每人两类方向分别 11/11、5/5。

| 字段 | 判断内容 |
|---|---|
| 总体偏好 | 综合指令完成与观看效果 |
| 指令忠实度 | 编辑是否实现指令要求 |
| 非目标保持 | 不应改变的内容是否保持 |
| 时序一致性 | 运动与编辑稳定性，闪烁或跳变 |
| 视觉质量 | 清晰度、自然度与明显伪影 |

每项主动选择 A 更好、B 更好、平局或不确定，无默认答案。
平局表示能比较但没有明显偏好；不确定表示无法可靠判断。依据指令与视觉判断，
不需要模仿任何 CPU 指标。播放失败时停止操作，不能填写“不确定”代替故障。
整体信心也需主动选择：0 无法确信、0.25 较低、0.5 中等、0.75 较高、1 很高。
备注可选，最多 1000 字符。

## 播放、草稿、确认

三路分别为原视频、A、B。先使用同步播放；可全部暂停、从头重播、统一拖动，
也可使用每个视频的独立控制条。同步以原视频为基准，偏差超过约 0.12 秒时校正，
是浏览器近似同步而非逐帧同步。三路加载并播放、所有字段填完后才可提交。

真实候选的 mp4v 编码不受当前浏览器支持，页面播放独立的 VP9 无损展示副本。
全部 39 个引用视频的 624 帧 RGB24 SHA、512×512 尺寸、16 帧/8fps 时间均与原媒体一致；
原视频不改写。原始与展示 SHA 同时锁定，自动平局仍使用原始视频 SHA。

输入后自动保存草稿；离开前等待“草稿已保存”。草稿不会进入统计，刷新/重启会恢复。
点击“确认提交并继续”后还需点击“确认保存本题”；此时也可以“返回修改”。
只有原子落盘成功才进入下一题，已确认题只读，不能返回偷偷改写。
网络失败用“重试同一提交”；冲突提示时刷新核对，避免两个标签页同时作答。
完成页不展示结果。若误提交，先保留原记录并在 DEVLOG 登记问题，请维护者核实，
不要删文件、手改 JSONL、让 AI 修改答案或重建同名目录。

耗时字段是本次服务器展示至提交的经过时间，可能包含停顿与后台时间；恢复后重新计时。
它不是精确观看时长，也不能把重启前空闲时间包装成精确人工劳动成本。

## 启动与退出

以下 PowerShell 命令均在仓库根 `D:\lab idea` 执行。`$d3` 是本次真实交付根。
运行时复制终端第一条 `/entry/` 链接到浏览器；入口一次有效，刷新用工作页面。
链接包含临时令牌，勿转发。第二条工作页面链接依赖已建立的本机会话 cookie。
重启令牌、cookie 名称、随机路径全部轮换；旧页不能进入新会话。

```powershell
Set-Location 'D:\lab idea'
$d3 = 'artifacts/defense_mvp/DEFENSE-MVP-D3-v01'

# 只读确认已准备包：应为 prepared_bundle / incomplete，尚无正式导出
uv run defense verify-annotations --bundle "$d3/formal-bundle"

# 熟悉控件的练习（新目录；不需要重复跑完施工用的64条测试）
uv run defense annotate --bundle "$d3/practice-bundle" --annotator-id annotator-a --output "$d3/practice/annotator-a"
```

退出：先等草稿保存或当前确认完成，再关闭页面；在服务终端按 **Ctrl+C**。
Windows/uv 的控制中断可能返回 1，内核写锁随进程退出释放。不要删 writer.lock。
重开 PowerShell 时重新执行 `$d3 = ...`。练习恢复必须显式指定：

```powershell
uv run defense annotate --bundle "$d3/practice-bundle" --annotator-id annotator-a --output "$d3/practice/annotator-a" --resume
```

正式首次启动由用户执行；施工没有执行以下命令。两条命令**顺序执行**，前一服务退出后再运行后一条：

```powershell
uv run defense annotate --bundle "$d3/formal-bundle" --annotator-id annotator-a --output "$d3/formal/annotator-a"

uv run defense annotate --bundle "$d3/formal-bundle" --annotator-id annotator-b --output "$d3/formal/annotator-b"
```

中途休息后，用原命令末尾追加 `--resume`；目录和 annotator 必须与原会话一致。
普通启动遇到已有目录会拒绝；错误身份、包漂移、损坏记录、未知锁也会拒绝。
遇到“会话被占用”先确认另一个终端是否仍运行。不要按文件时间猜测锁失效，
不要删除未知锁文件。`pending/` 是未发布临时文件，保留诊断，不当作答案。

## 导出与核对

关闭标注服务后导出。输出必须是全新目录；不完整也可以封存为 incomplete，继续标注后
再次导出用 v02 等新名字。已导出目录不覆盖，逐题事实源不被导出操作修改。

```powershell
uv run defense export-annotations --bundle "$d3/formal-bundle" --session "$d3/formal/annotator-a" --output "$d3/formal-exports/annotator-a-v01"
uv run defense export-annotations --bundle "$d3/formal-bundle" --session "$d3/formal/annotator-b" --output "$d3/formal-exports/annotator-b-v01"
uv run defense verify-annotations --bundle "$d3/formal-bundle" --export "$d3/formal-exports/annotator-a-v01" --export "$d3/formal-exports/annotator-b-v01"
```

有效双人完整输出应为 `mode=formal, scope=dual, status=complete, exported_answers=64`，
`automatic_ties_shared=10`，两份 coverage 各 42。缺题返回 incomplete；身份/方向/来源/
checksum 不合格直接失败。单人 complete 只代表该人完成，须检查 scope。

要核对本次工程练习证据，使用下列只读命令；`--allow-practice` 表示只承认工程练习：

```powershell
uv run defense verify-annotations --bundle "$d3/qa-v02/practice-bundle" --export "$d3/qa-v02/exports/annotator-a-v01" --export "$d3/qa-v02/exports/annotator-b-v01" --allow-practice
```

`answers.jsonl` 仅含确认回答；`automatic-ties.json` 单独标记系统规则，没有伪造信心或人工时间。
`records-manifest.json` 连接逐题原子文件与 JSONL，`coverage.json` 列明缺题/覆盖，
`export-receipt.json` 与 `SHA256SUMS` 保存封存信息。它们及私有映射、会话、媒体全部留在
忽略的 artifacts 内，不加入 Git。D3 verifier 不计算胜率、kappa、BT 或 bootstrap。

人评结束后的 D4 必须另行接续，保持原双人分歧规则和全部负/不确定结果。
