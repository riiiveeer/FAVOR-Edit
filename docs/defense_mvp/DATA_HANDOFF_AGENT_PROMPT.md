# 学校服务器 E0 回传包 Agent 提示词

> 用途：将本文件第 2 节至第 11 节整体发送给学校服务器端 agent。
> 目标：只读收集 Defense MVP 所需 E0 数据，建立可校验、可传输、不可覆盖的独立回传包。
> 本提示词不授权本地 Codex 连接学校服务器；实际操作由用户或服务器端 agent 执行。

## 1. 使用前填写

建议的唯一目标目录：

`/DATA/DATA4/hfy/deliveries/DEFENSE-MVP-E0-HANDOFF-v01`

如该路径、同名 staging、failed 目录、tar 或 tar checksum 任一已经存在，不得复用、
删除或覆盖。停止并向用户申请新的 package ID。

---

## 2. 你的角色与目标

你是学校服务器端的数据回传 agent。请在学校服务器上只读核对既有 E0 产物，并建立一个
新的 Defense MVP 回传包。目标包只包含复现实验和 CPU 分析所需的数据、媒体、checksum、
审计材料和运行身份；不要复制模型权重、conda 环境、cache、inversion latent 或无关大文件。

你必须先发现并验证真实路径，不能根据本提示词猜测路径。历史记录提示 E0 可能位于
`/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01`，visual audit 可能位于
`/DATA/DATA4/hfy/outputs/E0-visual-audit-v01`，但这些只是候选线索，不是已验证事实。

最终目标目录固定为：

`/DATA/DATA4/hfy/deliveries/DEFENSE-MVP-E0-HANDOFF-v01`

package ID 固定为 `DEFENSE-MVP-E0-HANDOFF-v01`。

## 3. 权限与禁止事项

允许：

- 只读检查 E0、visual audit、Git/DEVLOG 和现有日志；
- 在新的唯一 staging 目录复制必需文件；
- 在 staging 内生成 package manifest、checksum、验证报告和打包日志；
- 通过同文件系统 no-replace rename 发布新的 final package；
- final 验证通过后在 final 同级创建唯一 tar 和 tar.sha256。

禁止：

- 修改、移动、重命名、删除或补写任何 E0/audit 源文件；
- 删除已有 final/staging/failed/tar 来重试；
- 修改服务器 Git worktree或就地 patch 仓库；
- 启动 GPU、加载模型、重新生成候选或运行 judge；
- kill 他人进程、清缓存、清理他人数据或 reset GPU；
- 把缺失文件、空 audit、mock reward 或推测信息补造成正式产物；
- 复制模型、环境、cache.sqlite3、latent、checkpoint 和无关仓库。

任一硬门失败时立即停止，保留 staging 或改名为具名 failed artifact，并回传证据。

## 4. 预检与源发现

开始时执行并完整记录：

```bash
set -euo pipefail
date --iso-8601=seconds
hostname
id
pwd
df -h /DATA/DATA4/hfy
df -i /DATA/DATA4/hfy
git -C /home/sunyinan/FAVOR-Edit rev-parse HEAD || true
git -C /home/sunyinan/FAVOR-Edit status --short --branch || true
```

随后只读定位并记录以下文件的绝对路径、大小、mtime 和 SHA-256：

- E0 `plan.json`；
- E0 `candidates.json`；
- E0 `report/W1_REPORT.md`；
- visual audit `audit-manifest.json`；
- visual audit `audit.csv`；
- visual audit README、contact sheets、proxies 和 SHA256SUMS；
- E0 command log、runner summary、Git snapshot/revision 记录。

路径存在多个候选时，不要自行选最新目录。比较 DEVLOG、experiment_id、50/50 completion、
plan/candidates checksum 和 code snapshot。身份仍不唯一时停止并询问用户。

## 5. 硬输入门

创建 staging 前，用只读脚本解析 plan/candidates 并确认：

1. plan 恰好 10 个 inversion、50 个 candidate task；
2. candidates 恰好 50 条，candidate_id 唯一，全部 `status=succeeded`；
3. sample_id 恰好为 `bear-white, bus-red, elephant-pink, classic-car-blue, dog-tiger,
   horse-zebra, mallard-swan, hiker-backpack, rider-helmet, car-headlights`；
4. 每个 sample 恰好 5 个 seed：`101,202,303,404,505`；
5. 每个 candidate 恰好 1 个 MP4、16 个 frame path、16 个 frame checksum；
6. candidate MP4 SHA-256 等于 `video_checksum`；
7. 16 个 candidate frame SHA-256 逐项等于 `frame_checksums`；
8. 每个 sample 的 source MP4、16 source frames、16 masks 都存在；
9. source MP4 SHA-256 等于 plan input 的 `video_checksum`；
10. source frame combined checksum 等于 `source_checksum`；
11. mask combined checksum 等于 `mask_checksum`；
12. generation backend 为 anyv2v，分辨率/帧数/fps 为 512×512/16/8；
13. model revision、AnyV2V commit、code snapshot 和 runtime/VRAM 字段可追溯；
14. audit.csv 若存在，必须覆盖 50 个 candidate_id；已填写则保留，未填写不得补造。

combined checksum 必须复用仓库 `w1_pipeline.hashing.combined_file_sha256` 的语义，
不得用简单字符串拼接 SHA 替代。

## 6. 唯一 staging 与目录布局

先验证 final、staging、failed、tar、tar.sha256 全部 ABSENT。使用同一 DATA4 文件系统的
唯一 staging，例如：

`/DATA/DATA4/hfy/deliveries/.DEFENSE-MVP-E0-HANDOFF-v01.prepare-<UTC>-<PID>.staging`

staging 内固定布局：

```text
metadata/
  original-plan.json
  original-candidates.json
  W1_REPORT.md
  e0-audit/
    audit-manifest.json
    audit.csv
    README.md
    SHA256SUMS.original
    contact-sheets/
    proxies/
  logs/
media/
  sources/<sample_id>/
    source.mp4
    frames/00000.png ... 00015.png
    masks/00000.png ... 00015.png
  candidates/<sample_id>/seed-<seed>/
    video.mp4
    frames/00000.png ... 00015.png
PACKAGE_MANIFEST.json
PACKAGE_VERIFICATION.json
PACKAGE_BUILD_LOG.txt
PACKAGE_BUILD_SCRIPT.py
PACKAGE_SHA256SUMS
README.md
```

源文件复制到 staging 后改用上述稳定相对路径。`original-plan.json`、
`original-candidates.json` 和原 audit 文件必须按字节原样复制，不重写其中的服务器绝对路径。

## 7. PACKAGE_MANIFEST.json 最小 schema

manifest 至少包含：

- `schema_version: 1`；
- `package_id`、`created_at`、`created_by`、hostname；
- E0 experiment_id、源根绝对路径、plan/candidates/audit 原始 SHA；
- server repo HEAD、status、E0 code_snapshot、model_commit、anyv2v_commit；
- package status：`passed` 或 `failed`，不得预填；
- 10 个 sample 条目；
- 50 个 candidate 条目；
- 每个文件的 POSIX `relative_path`、role、sha256、size_bytes；
- 总文件数、总字节数和按 role 的计数；
- warnings 和 missing_optional_artifacts。

请严格使用以下字段名，避免本地 ingest 猜测字段：

```json
{
  "schema_version": "1",
  "package_id": "DEFENSE-MVP-E0-HANDOFF-v01",
  "created_at": "<ISO-8601>",
  "created_by": "<agent/user>",
  "hostname": "<host>",
  "status": "passed",
  "source": {
    "e0_root": "<absolute source root>",
    "audit_root": "<absolute audit root or null>",
    "repo_head": "<40-char HEAD or recorded snapshot>",
    "repo_status": "<verbatim short status>",
    "plan_sha256": "<sha256>",
    "candidates_sha256": "<sha256>",
    "audit_manifest_sha256": "<sha256>",
    "e0_code_snapshots": ["<identity>"],
    "model_commits": ["<identity>"],
    "anyv2v_commits": ["<identity>"]
  },
  "counts": {
    "samples": 10, "candidates": 50, "mp4": 60,
    "source_frames": 160, "masks": 160, "candidate_frames": 800,
    "files": "<payload inventory count>",
    "total_bytes": "<payload inventory bytes>"
  },
  "samples": [],
  "candidates": [],
  "files": [],
  "warnings": [],
  "missing_optional_artifacts": []
}
```

`files` 只清点 `metadata/` 与 `media/` 下的 payload 文件，避免 manifest 自哈希循环；
`counts.files/total_bytes` 必须等于该 payload inventory。`PACKAGE_SHA256SUMS` 则覆盖 final
树中除自身外的全部常规文件，包括 manifest、verification、README、build log/script。

每个 sample 条目必须包含：

- sample_id、sequence、task_type、instruction、target_caption；
- source MP4 relative path/SHA；
- 16 source frame relative paths/逐文件 SHA；
- source combined checksum；
- 16 mask relative paths/逐文件 SHA；
- mask combined checksum；
- crop 参数。

每个 candidate 条目必须包含：

- candidate_id、sample_id、seed、status；
- video relative path/SHA；
- 16 frame relative paths/逐文件 SHA；
- generation_key、完整 generation config；
- runtime_seconds、peak_vram_mb、code_snapshot。

本地 ingest 只信任 manifest 的相对路径及 checksum，不信任 original JSON 中的服务器路径。

## 8. 复制范围

硬要求复制：

- 10 source MP4；
- 160 source frames；
- 160 masks；
- 50 candidate MP4；
- 800 candidate frames；
- plan/candidates/audit manifest/audit CSV/W1 report；
- package build script、log、manifest、verification、全树 checksum 和 README。

尽力复制但允许明确 warning：

- visual audit contact sheets/proxies；
- E0 stdout/stderr、runner summary、环境/版本日志；
- 原 visual audit SHA256SUMS。

禁止复制：

- `rewards.json` 中的 mock 分数作为研究证据；
- model weights、Hugging Face cache、conda env；
- inversion latent、PnP 中间帧、cache.sqlite3；
- E1/E2 目录；
- 与 60 个最终 MP4、对应 frames/masks 无关的大文件。

## 9. staging 验证与发布

复制完成后，在 staging 内从相对路径重新验证：

1. 10 sample、50 candidate、60 MP4；
2. 160 source frames、160 masks、800 candidate frames；
3. 全部 SHA-256 与 manifest 和 original records 一致；
4. candidate/sample/seed/cardinality 完整；
5. MP4 可由 ffprobe 读取，16 frames、512×512、8 fps；
6. audit candidate_id 与 candidates 精确一致；
7. manifest 中没有 staging 绝对路径；
8. manifest 中没有模型/cache/latent 文件；
9. PACKAGE_SHA256SUMS 覆盖除其自身外的所有常规文件并按 POSIX relative path 排序；
10. 从 PACKAGE_SHA256SUMS 执行 `sha256sum -c` 全部通过。

`PACKAGE_VERIFICATION.json` 至少记录每个 check 的 id/status/summary、精确计数、warnings、
failures、验证开始/结束时间以及 `ready_for_transfer`。任何 failure 都强制
`ready_for_transfer=false`。

只有 verifier PASS 后才发布 final。发布前验证 Linux
`renameat2(RENAME_NOREPLACE)`；能力不可用则停止，不用可覆盖的 `mv` 降级。发布使用同文件系统
单次 no-replace rename。发布后在 final 上重新执行 `sha256sum -c` 和只读 verifier。

## 10. 传输归档

final direct verification PASS 后：

1. 在 final 同级创建唯一、未压缩 POSIX tar：
   `DEFENSE-MVP-E0-HANDOFF-v01.tar`；
2. MP4/PNG 已压缩，不要浪费时间做高强度 gzip/xz；
3. 生成 `DEFENSE-MVP-E0-HANDOFF-v01.tar.sha256`；
4. 对 tar 执行 `tar -tf`，确认没有绝对路径、`..`、symlink 逃逸或 final 外文件；
5. 记录 tar bytes、SHA-256、创建时长；
6. 不删除 final package。

本地收到 tar 后将重新校验 tar SHA、路径安全、全树 checksum 和 manifest，不以传输成功
替代内容验收。

## 11. DEVLOG 与最终回传

执行前在服务器 DEVLOG 写 PLAN，至少记录：

- package ID、源路径候选、目标 final/staging；
- repo HEAD/status；
- 预计文件数、大小、磁盘/inode 和时长；
- 完整命令/脚本路径；
- 源 E0 只读与 final ABSENT 结果。

结束或失败后立即写 COMPLETE/FAILED，记录：

- 源 plan/candidates/audit SHA；
- 10/50/60/160/160/800 精确计数；
- package final/tree checksum/tar/tar checksum；
- runtime、前后磁盘/inode；
- warnings、missing optional、failed checks；
- 未修改 E0、未使用 GPU、未修改 Git worktree 的确认。

最终只向用户回传以下摘要，不粘贴成千上万条 checksum：

```text
status: PASSED / FAILED
package_id:
source_e0_root:
source_audit_root:
source_repo_head:
source_repo_status:
plan_sha256:
candidates_sha256:
audit_manifest_sha256:
counts:
  samples: 10
  candidates: 50
  mp4: 60
  source_frames: 160
  masks: 160
  candidate_frames: 800
package_root:
package_manifest_sha256:
package_verification_sha256:
package_tree_sha256_file:
tar_path:
tar_size_bytes:
tar_sha256:
warnings:
failures:
ready_for_transfer: true / false
e0_source_unchanged: true / false
gpu_used: false
```

如失败，停止在失败现场，不删除、不覆盖、不换路径偷偷重试。把失败命令、exit code、stderr、
failed/staging 路径和下一步建议交给用户决定。
