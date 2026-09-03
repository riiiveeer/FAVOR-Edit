# D3 本地双人盲评实现回执

日期：2026-09-03；环境：Windows CPU-only。状态：**D3 工程验收通过，可以邀请真人标注**。
审计提交与普通推送身份见 DEVLOG 最终发布回执。
停止点：工程 ready 后邀请真人。正式人工回答 **0**；未启动正式会话，未进入 D4。

## 实现与冻结输入

新增独立 `defense-blind-v1` 模型、annotation-v1.yaml、输入/映射/展示锁、单写会话、
原子逐题记录、草稿 CAS、幂等恢复、127.0.0.1 匿名 HTTP/Range、三路播放器与表单、
不可覆盖导出和双人 coverage verifier。四个 CLI 已落地，命令见 ANNOTATION_GUIDE。

现场接手基线为 main/HEAD/origin/main d5ae95e5f35320ad3d749b637db63197c77a519e。
保留原 DEVLOG/交接文档及未跟踪 tar/sidecar；D2 无重跑、无源码/配置/结果改变。
prepared 包复验 20 个关联输入文件、全部 60 原始 MP4、D2 跨锁链、315 条选择关系、
42 比较的角色/sample/candidate/source/路径/SHA；formal 另绑定四个既有 SHA。

| 冻结输入 | SHA-256 |
|---|---|
| pilot.yaml | 19f827d1ce84604eb68336fe549b7530a67d6b4074ad92b05b4cc8d63663feae |
| normalized-manifest.json | b0eee7ab41aff575220957fae4dd67afd0fbaac85e4f756d023a9e42929f0b46 |
| comparisons.json | 486dad879372b6f687a380ebe4e102d61b6df89392426c7cc3aea7e9aeffb9cb |
| selection-lock.json | 99ce0522397707649aa34d82cfde3c3df4a5d898acbc702d6e53282f07741fb2 |

D2 35 scored/15 qualitative_only、315 selections、26 个 N=2 fallback 原样保留。
28+14 比较中原始 SHA 相等的 6+4 项是自动平局；实际显示 22+10=32。
annotator-a/b 的方向均为 11/11+5/5，顺序使用独立目的哈希，自动题无显示方向。

## 真实浏览器发现与修复

首次真实播放发现候选为 MPEG-4 Part 2 (mp4v)，当前 Chromium 不支持，source 为 H.264。
原始视频均可由既有 ffmpeg 解码；不能把 HTTP 字节测试算作播放验收。
最终采用独立 `lossless-vp9-yuv420p-v1` 展示副本：39 个引用视频、624 帧的 RGB24 SHA、
512×512、16帧/8fps 时间精确相等。原始与展示 SHA 双重锁定，原始不改写、不做有损替代。
formal 包转换/等价验证 55.07 秒，CPU-only。工具版本/SHA/命令/逐帧证明随包保留。

浏览器实际暴露并修复：Windows 锁读取异常分类、原生 confirm 控制阻塞、旧 root cookie
与新 Path 同名冲突。最终为页面内二次确认、启动随机 URL 前缀、独立 cookie 名称与 Path。
同机旧页即使带新cookie也不能访问新会话；固定错误码不会反射路径/方法/答案。

真实 In-app Browser 已完成：三路同步播放/暂停/重播/seek、草稿刷新和服务重启恢复、
全部五种字段及 confidence、script 字面量备注不执行、返回修改、确认后前进与无预填，
两位身份顺序独立、32+32 全套练习、完成页刷新不重答。错误媒体在全字段填完后仍禁止提交。
练习均为自动化固定值，**不是视觉偏好判断或研究测量**。

## 本地产物

根：`artifacts/defense_mvp/DEFENSE-MVP-D3-v01/`，全部 Git 忽略。

| 目录/文件 | 用途 |
|---|---|
| formal-bundle | 正式 prepared 包，尚无会话；SHA c03640b39ad1e7769ccdf4c2c133821a893fa26de7d4285c75f47dfb6eb00da6 |
| practice-bundle | 用户新练习包；SHA 80cf70cbefc73815f0cd016db7741a99bf43b858f2fe9ce2b329a8cfd4ec3da9 |
| qa-v02/practice-bundle | 完整浏览器工程验收包，SHA f72a111869cb449c88b9b121dd1a7b12f565fcf46fde68a075887d0937fe3958 |
| qa-v02/annotator-a、annotator-b | 各32条固定值 practice 事实记录，独立 runs/草稿/锁 |
| qa-v02/exports/annotator-a-v01、annotator-b-v01 | 已验证不可覆盖导出 |
| qa-v02/dual-verification.json | dual practice complete，64回答+10共享规则，各42 coverage |
| qa-initial、qa-media-error | 编码失败/门禁验收诊断，保留，不用于正式作答 |
| output/playwright | 真实浏览器截图和逐题播放状态 |

截图 01-playback、02-draft-restored、03-a-complete、04-b-complete、05-media-error-blocked；
a-progress.json（第2–32题；第1题有独立DEVLOG证据）、b-progress.json（全部32题）。
全过程没有正式 human 来源记录，也没有人评胜率、kappa、BT、bootstrap。

## 测试矩阵与证据

`test_blind_annotation.py` 76 项覆盖：四类锁/清单漂移、重新计算清单后的角色/类别/样本/
qualitative/源/候选/假tie篡改，全部方向映射，字段严格性，草稿CAS、fsync/rename故障、
不确定确认丢失、双标签/双进程/内核崩溃锁、错误resume/损坏记录、HTTP身份与匿名内容、
Range、旧页、practice/formal、双人coverage、伪造导出，以及可播放tiny无损像素证明。

首轮70通过1失败后修复，之后72/72；补强后76/76通过。历史定向记录不是最终全仓结果。
最终源码实际验收：

| 命令/检查 | 结果 |
|---|---|
| `uv run pytest tests/defense_mvp -o addopts='' -q` | 115 passed，364.72秒，退出码0 |
| `uv run pytest -o addopts='' -q` | 218 passed，613.64秒，退出码0 |
| `uv run python -m compileall -q src tests` | 退出码0，1.13秒 |
| version、validate-config、10个命令help与正式包verify CLI | 全部退出码0，2.89秒 |
| `git diff --check` | 通过，无空白错误 |
| 最终正式/练习包、输入前后SHA、源码snapshot | 通过，3.88秒；60原MP4不变、39展示引用有效 |
| 最终会话/记录扫描 | formal会话0、人答0；64条确认全为practice |

`final-identity-verification.json` 保存最终只读校验。正式/用户练习包的源码文件SHA与
已测试最终源码一致。Git staged path/binary/size/whitespace guard 和发布身份在 DEVLOG
逐步记录，不把历史测试数目拼成一次全仓结果。所有练习服务与临时浏览器页面已关闭。

## 边界与下一步

一位评审为开发者，属于同机配合式盲评而非双盲；近似同步不宣称逐帧同步；当前view耗时
不宣称精确人工成本。包的源码文件 SHA 与运行环境留证，准备时Git HEAD是发布前基线。
协议/输入身份与方向不可在正式开始后调整。缺题保留 incomplete，误操作不改写已确认事实。
本地文件管理员仍能主动破坏/伪造文件，此系统提供可验证身份链而非防管理员攻击或真人认证。

用户按指南先熟悉按钮，再先后启动 formal annotator-a/b；本轮不代替其启动或作答。
