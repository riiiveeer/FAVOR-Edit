# D3 正式双人标注完成回执

日期：2026-09-04；环境：本地 Windows CPU-only。
状态：**D3 正式双人标注完成并通过封存验证**。

## 保存与进程状态

- `annotator-a`、`annotator-b` 各有 32 个逐题不可变确认记录；两边 `pending/` 均为 0。
- 两个标注服务均已退出，8765/8766/8767 无 D3 标注监听进程。
- 草稿与确认记录分开保存；正式事实源没有因导出或验证被修改。
- 没有由自动化或 AI 生成、修改、补齐正式答案。

## 封存与验证

忽略目录中的正式封存产物：

- `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-exports/annotator-a-v01/`
- `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-exports/annotator-b-v01/`
- `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-exports/verification-annotator-a-v01.json`
- `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-exports/verification-annotator-b-v01.json`
- `artifacts/defense_mvp/DEFENSE-MVP-D3-v01/formal-exports/dual-verification-v01.json`

现有 D3 verifier 的最终输出为：

| 项目 | 结果 |
|---|---|
| mode / scope / status | `formal` / `dual` / `complete` |
| 真人确认记录 | 64（A 32 + B 32） |
| 共享自动平局 | 10（媒体同一性规则，不伪造人答） |
| A 覆盖 | 42/42，缺题 0 |
| B 覆盖 | 42/42，缺题 0 |
| 身份集合 | `annotator-a` + `annotator-b` |
| checksum / 逐题身份、方向、来源链 | 通过 |

冻结输入与封存清单 SHA256：

- formal `bundle.json`：`c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6`
- A 导出 `SHA256SUMS`：`ad796e6aca1991b72f9820d2eee807c4fec89a9c80e9574ee1aae8ed3ffcae85`
- B 导出 `SHA256SUMS`：`91e6a169b81ef825e29e808a8777c264be55b5f88d5eed8ab9f82d5afc936a3a`
- 双人验证回执：`280b099845be84936021e3bffa9e4f69ab24749a7833f03ea3909f18737bd357`

A、B 导出时分别比较源会话全部 JSON SHA，导出前后相同；联合验证前后两个封存目录
全部文件 SHA 也保持相同。该验证只确认保存、身份和覆盖完整，不读取或计算方法胜率、
一致性、分歧、BT 或 bootstrap。

## D3 结束点与下一步

D3 已没有剩余工程或人工标注任务。正式原始记录和验证报告应保持只读；如果发现误提交，
先保留事实并审计，不删除或手改记录。

后续工作属于 D4：冻结本回执列出的两个正式导出作为输入，按既定双人分歧聚合规则生成
诚实统计和报告，保留负面、不确定和分歧结果。D4 必须作为单独阶段明确接续；本次没有
运行 D4，也没有查看或披露具体偏好结果。
