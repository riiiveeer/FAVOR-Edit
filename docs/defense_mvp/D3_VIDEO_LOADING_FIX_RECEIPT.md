# D3 视频加载修复回执

日期：2026-09-03；范围：本地 CPU 媒体读取和恢复界面。

## 现场与处理

用户 practice/annotator-a 第1/32题的题目/API正常，但三路均 readyState=0，无首帧、
缓冲和时长。终端曾有一次 session_rejected，缺少逐请求证据，不能断言唯一根因。
原生媒体读取停滞时，旧页面还缺少超时与重试。原用户没有已保存或未保存的答案。

新加载器使用同源认证 fetch 完整读取当前三路，显示百分比，核对类型/长度/大小，
然后以临时 blob URL 播放原有无损WebM字节。服务端角色路由、Cookie/Origin/CSRF、
媒体SHA、提交前原始/展示身份校验保持有效；Range路由继续受测。
不预加载后续题目，不持久缓存媒体，不重编码或替换已验收输入。

单路读取20秒超时，网络失败最多自动再试一次；403/409等明确错误不自动重试。
完整读取后的解码另有20秒超时。每路最多64MiB；切题/重载取消请求并回收对象URL。
重新加载保留本题、方向、表单和草稿，重新播放后才允许提交；旧事件不能污染新题，
就绪状态更新串行化。错误提供匿名诊断，故障不能用 uncertain 代替。

## 实测与记录

证据根：`artifacts/defense_mvp/DEFENSE-MVP-D3-v01/qa-loading-v01/`（忽略目录）。

- 最终加载器10项Node测试通过：认证/原字节、403、重试、长度/类型/大小、连接/body
  超时、取消后迟到响应、解码失败/超时、资源回收及诊断不泄漏。
- 真实浏览器三次“重载→播放→暂停”各924/855/858毫秒，含自动化交互，不是纯网络
  性能基准；三路均readyState=4、2秒、时间实际推进、无播放错误。
- 重载保留固定practice草稿；重启 --resume 也恢复。统一拖至2秒、重播有效。
  隔离练习确认1条固定tie测试答案后进入第2题，三路可播放且新题表单清空。
- 原始mp4v故障包A/B明确显示无法解码；即使填齐practice字段，提交仍禁用。
- 原用户8765练习服务按相同包/身份/目录 --resume，原标签页已恢复并验证播放。
  用户session.json SHA前后均为 `54d03890e4bf1166d7ade041a6a0344d3d9084e0f837922109feb6d99be01093`。
  没有替用户填写或确认答案；用户练习服务继续保留供试用，QA服务/页面已关闭。

`browser/reloads.json`、`next-question.png`、`decode-error.png`、
`user-session-restored.json/png`保存实际浏览器状态。`identity-verification.json`
复核60原MP4、39展示引用和冻结输入/映射/展示证明；正式/练习bundle SHA均未变。
运行回执增加JS源码SHA，旧prepared bundle保持原样，准备时代码和修复后运行代码分别留证。
截至核对，正式会话0、正式人答0；本次新增确认只有1条隔离practice固定答案。

## 最终回归与发布

最终源码验收通过，D3仍可邀请真人标注：

| 检查 | 结果 |
|---|---|
| `uv run pytest tests/defense_mvp -o addopts='' -q` | 116 passed，397.93秒，退出0 |
| `uv run pytest -o addopts='' -q` | 219 passed，689.45秒，退出0 |
| `node --test tests/defense_mvp/annotation_playback.test.cjs` | 10 passed，281.8毫秒 |
| CLI、全src/tests compileall、输入和会话SHA、diff检查 | 全部通过 |
| Git暂存审计 | 显式12路径，二进制0，媒体/原始记录/artifacts全部排除 |

日志分别为 `defense-tests.txt`、`repository-tests.txt`；Node故障测试也由pytest入口执行。
CLI正式包只读verify为prepared_bundle/incomplete，42/10/32且导出回答0。
审计提交和普通推送main的最终身份在DEVLOG发布回执；不强推、不重写历史。
不改变D2或评审协议，不启动正式人评，不进入D4。
