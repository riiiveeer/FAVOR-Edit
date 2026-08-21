# E0 查验与 E1 Judge 可靠性施工手册

> 适用环境：学校 RTX A6000 服务器，不能直接访问国际互联网。  
> 执行者：服务器端 Cline。  
> 当前基线：`E0-anyv2v-w1-v01` 已完成 50/50 真实候选并通过媒体校验。  
> 本手册目标：不搬运完整视频目录，在服务器完成 E0 分层视觉查验；随后实现并运行 E1 Pilot，形成 W2 的 Judge 可靠性表、位置偏差统计和 `reward-v0` 决策。

---

## 0. 先理解 W2 与 E1 的关系

- `W1/W2/W3` 是周次和项目交付时间盒。
- `E0/E1/E2` 是有依赖关系的实验阶段。
- 已完成：`W1 + E0`，即真实视频生成、缓存、复现和媒体验收链路。
- 当前要做：`W2 + E1`，即人工校准集、Judge 消融、位置偏差和 `reward-v0`。
- 后续：E1 通过门槛后，W3 才进入 `E2 Best-of-N`。
- E1 如果失败，W2 仍可交付失败诊断和修订后的 prompt，但不得绕过 E1 直接进行 DPO 或批量生成偏好训练对。

E1 Pilot 使用当前 10 个输入、50 个候选进行工程与初步决策。它不是最终论文级泛化证据。论文级 E1 仍需扩展到约 100 个输入、600–1000 个 pair 判断。

---

## 1. Cline 执行约束

### 1.1 开始前必须阅读

Cline 开始任何修改前，必须完整阅读：

```text
AGENTS.md
DEVLOG.md
proposal.md
docs/SCHOOL_SERVER_DELIVERY.md
docs/E0_AUDIT_E1_EXECUTION.md
```

### 1.2 DEVLOG 规则

每完成一个可独立验证的步骤，先追加 `DEVLOG.md`，再进行下一步。不得在一天结束时把多个步骤合并成一条笼统记录。

每条记录至少包含：

- 日期与时间、时区；
- 本地或学校服务器环境；
- 唯一步骤/实验 ID；
- Git commit 或 dirty snapshot；
- 命令、配置、数据和模型 revision；
- 成功、失败或中断结果；
- 运行时间和峰值显存（使用 GPU 时）；
- 产物与日志的绝对路径；
- 下一步。

真实 GPU judge 作业启动前，必须先写一条 `RUNNING` 前置记录；结束或中断后立即补一条结果记录。

### 1.3 不得破坏 E0

以下目录是只读输入，不得删除、移动、覆盖或写入新文件：

```text
/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01
/DATA/DATA4/hfy/outputs/E0-anyv2v-smoke-v01
```

E0 查验使用新的唯一目录：

```text
/DATA/DATA4/hfy/outputs/E0-visual-audit-v01
```

E1 使用新的唯一目录：

```text
/DATA/DATA4/hfy/outputs/E1-judge-pilot-v01
```

如果目录已经存在，必须停止并检查；不得自动清空。需要重跑时改用 `-v02` 或更高版本。

### 1.4 单实例与断点续跑

- 同一 experiment dir 同时只能有一个写进程。
- E1 runner 必须建立排他锁；发现锁存在时直接失败并打印持有者信息。
- 成功记录必须缓存；中断后只重跑 pending/failed 项。
- 临时文件先写到同目录 `.tmp`，完成校验后原子重命名。
- 原始 judge 响应永远保留，不得只保存解析后的分数。

### 1.5 网络与依赖边界

- 不从 GitHub、Hugging Face 或来源不明的网站在运行时下载代码和模型。
- 可以使用已确认可访问的国内镜像准备依赖，但必须锁定版本并保存下载来源与 SHA-256。
- 模型优先在联网机器准备完整 snapshot，再以归档包上传服务器。
- 服务器真实推理必须设置 `HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1`。
- 没有真实 judge 权重时，只能完成代码、mock/replay、人工标注和报告框架，不能宣称 E1 实验完成。

---

## 2. 固定路径和环境

在服务器项目仓库根目录执行：

```bash
cd /home/sunyinan/FAVOR-Edit

export PROJECT="$(git rev-parse --show-toplevel)"
export DATA_ROOT=/DATA/DATA4/hfy
export CONTROL_ENV="$DATA_ROOT/envs/w1-control"
export GPU_ENV="$DATA_ROOT/envs/anyv2v-cu118"
export E0="$DATA_ROOT/outputs/E0-anyv2v-w1-v01"
export E0_SMOKE="$DATA_ROOT/outputs/E0-anyv2v-smoke-v01"
export E0_AUDIT="$DATA_ROOT/outputs/E0-visual-audit-v01"
export E1="$DATA_ROOT/outputs/E1-judge-pilot-v01"
export TMPDIR="$DATA_ROOT/tmp"
export HF_HOME="$DATA_ROOT/caches/hf"
export HF_HUB_CACHE="$DATA_ROOT/caches/hf/hub"
export PIP_CACHE_DIR="$DATA_ROOT/caches/pip"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
```

如果仓库实际位置不同，只修改第一条 `cd`；其他路径与已有 E0 记录一致。

执行只读预检：

```bash
set -euo pipefail

git status --short --branch
git rev-parse HEAD
test -x "$CONTROL_ENV/bin/python"
test -x "$CONTROL_ENV/bin/w1"
test -f "$E0/plan.json"
test -f "$E0/candidates.json"
test -f "$E0/cache.sqlite3"
test -d "$E0/candidates"
ffmpeg -version | head -n 1
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
df -h "$DATA_ROOT"
```

预期：

- Git 状态可解释，没有来源不明的冲突修改；
- GPU 为 RTX A6000；
- E0 的 `plan.json`、`candidates.json`、cache 和候选目录存在；
- DATA4 有足够空间创建轻量审计产物和 E1 缓存。

把预检结果写入 `DEVLOG.md`，步骤 ID 使用 `E0-audit-preflight-v01`。

---

# Part A：E0 服务器端查验

## 3. E0 硬验收复查

运行：

```bash
"$CONTROL_ENV/bin/w1" verify \
  --expected 50 \
  --candidates "$E0/candidates.json" \
  2>&1 | tee /tmp/e0-verify-v01.log
```

必须得到等价结果：

```json
{
  "valid": true,
  "count": 50,
  "errors": {}
}
```

额外检查清单和目录计数：

```bash
"$CONTROL_ENV/bin/python" - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["E0"])
records = json.loads((root / "candidates.json").read_text())

assert len(records) == 50, len(records)
assert all(x["status"] == "succeeded" for x in records)
assert all(len(x["frame_paths"]) == 16 for x in records)
assert all(len(x["frame_checksums"]) == 16 for x in records)
assert len({x["candidate_id"] for x in records}) == 50
assert len({(x["sample_id"], x["config"]["seed"]) for x in records}) == 50

print("status", Counter(x["status"] for x in records))
print("samples", len({x["sample_id"] for x in records}))
print("seeds", sorted({x["config"]["seed"] for x in records}))
print("runtime_seconds", sum(x.get("runtime_seconds") or 0 for x in records))
print("peak_vram_mb", max(x.get("peak_vram_mb") or 0 for x in records))
PY
```

完成后立刻追加 `DEVLOG.md`，步骤 ID：`E0-audit-hard-verify-v01`。保存 `/tmp/e0-verify-v01.log` 的结果摘要；不需要把临时日志加入 Git。

## 4. 实现轻量审计脚本

Cline 在仓库新增：

```text
scripts/build_e0_audit.py
tests/test_build_e0_audit.py
```

脚本不得修改 E0 输入。接口必须为：

```bash
python scripts/build_e0_audit.py \
  --plan "$E0/plan.json" \
  --candidates "$E0/candidates.json" \
  --output-dir "$E0_AUDIT"
```

### 4.1 脚本输入校验

启动时必须检查：

- 输出目录不存在；若存在立即失败；
- plan 恰好含 10 个 inversion、50 个 candidate task；
- candidates 恰好 50 条并全部为 `succeeded`；
- candidate ID、sample ID、seed 可与 plan 一一对应；
- 每个视频存在，checksum 与记录一致；
- 每个候选有 16 帧；
- `ffmpeg` 和 `ffprobe` 可执行。

### 4.2 全部 50 个联系表

为每个候选生成一张 JPEG：

```text
contact-sheets/<candidate_id>.jpg
```

要求：

- 16 帧完整排列为 4×4；
- 单帧缩放为 160×160；
- 不改变源视频和原始帧；
- 文件名使用 candidate ID；
- 生成后验证 JPEG 可解码。

等价 ffmpeg 滤镜：

```text
scale=160:160:flags=lanczos,tile=4x4:padding=2:margin=2
```

### 4.3 固定 22 个并排代理

固定抽查集合，不允许运行时随机改变：

- `bear-white`：5 seeds；
- `dog-tiger`：5 seeds；
- `hiker-backpack`：5 seeds；
- 其余 7 个 sample：seed 303。

共 22 个候选。每个代理左侧为源视频，右侧为候选：

```text
proxies/<candidate_id>.mp4
```

要求：

- 左右均缩放为 256×256；
- `hstack` 得到 512×256；
- 保持全部 16 帧和 8 fps；
- H.264、无音频、`crf=30`、`faststart`；
- 代理只用于审计和标注预览，研究测量继续引用原视频 checksum。

### 4.4 审计清单和模板

脚本还必须生成：

```text
audit-manifest.json
audit.csv
SHA256SUMS
README.md
```

`audit-manifest.json` 至少记录：

- E0 plan/candidates 的绝对路径和 SHA-256；
- 生成审计包时的代码 snapshot；
- 50 个 candidate ID；
- 22 个固定抽查 ID；
- 原视频、编辑视频、contact sheet、proxy 的路径和 checksum；
- instruction、target caption、task type、seed；
- ffmpeg 版本与生成时间。

`audit.csv` 表头固定为：

```csv
candidate_id,faithfulness,preservation,temporal_consistency,visual_quality,failure_tags,systematic_failure,usable_for_e1,reviewer,reviewed_at,notes
```

四个维度只允许 `0/1/2` 或空值：

- `2`：明显良好；
- `1`：部分成功或轻微问题；
- `0`：明显失败；
- 空值：尚未检查。

`failure_tags` 可使用分号分隔的以下值：

```text
under_edit
over_edit
identity_loss
background_change
flicker
motion_break
artifact
crop_failure
cannot_judge
```

这些粗分只用于 E0 视觉审计和 E1 样本诊断，不得作为正式人工 preference ground truth。

### 4.5 自动测试

单元测试必须用现有 mock fixture 或临时生成的 16 帧小视频验证：

- 输出目录已存在时拒绝运行；
- 输入不是 50 条时拒绝；
- 固定抽查集合恰好 22 条；
- 所有 50 张联系表可解码；
- 22 个代理均为 512×256、16 帧、8 fps；
- 输入 E0 文件的 checksum 在执行前后完全不变；
- `SHA256SUMS` 不包含自身，且可用 `sha256sum -c` 验证。

实现和测试通过后，立即写 `DEVLOG.md`，步骤 ID：`E0-audit-tool-v01`。

## 5. 运行 E0 轻量审计构建

先确认没有旧目录：

```bash
test ! -e "$E0_AUDIT"
```

运行：

```bash
"$CONTROL_ENV/bin/python" "$PROJECT/scripts/build_e0_audit.py" \
  --plan "$E0/plan.json" \
  --candidates "$E0/candidates.json" \
  --output-dir "$E0_AUDIT" \
  2>&1 | tee /tmp/e0-audit-build-v01.log

find "$E0_AUDIT/contact-sheets" -name '*.jpg' -type f | wc -l
find "$E0_AUDIT/proxies" -name '*.mp4' -type f | wc -l
du -sh "$E0_AUDIT"

cd "$E0_AUDIT"
sha256sum -c SHA256SUMS
cd "$PROJECT"
```

必须得到：

- 50 张联系表；
- 22 个并排代理；
- SHA-256 全部通过；
- 原 E0 再次执行 `w1 verify` 仍为 50/50 valid。

完成后立即写 `DEVLOG.md`，实验 ID：`E0-visual-audit-v01`。

## 6. 人工查验步骤

人工查验顺序：

1. 先浏览全部 50 张联系表；
2. 再完整播放 22 个并排代理；
3. 联系表发现异常的其他候选，直接打开 E0 原始 `video.mp4` 补看；
4. 在 `audit.csv` 填写四维粗分、failure tags 和 `usable_for_e1`；
5. 检查同一 sample 五个 seed 是否存在系统性失败。

每个视频按以下顺序判断：

1. **Faithfulness**：目标对象/属性/局部修改是否真正出现，是否只出现一两帧。
2. **Preservation**：背景、运动、非目标对象、主体身份是否被无关改变。
3. **Temporal consistency**：编辑区域是否闪烁、漂移、突然消失，运动是否连续。
4. **Visual quality**：是否有结构畸变、纹理破碎、色块和明显扩散伪影。

系统性失败判定：同一 sample 的五个 seed 全部出现相同严重问题，或五个结果几乎不可区分且都无法构成有意义偏好。

人工完成后运行审计验证命令。`build_e0_audit.py` 应提供：

```bash
"$CONTROL_ENV/bin/python" scripts/build_e0_audit.py \
  --verify-existing "$E0_AUDIT"
```

验证内容：

- 50 行审计记录，无重复 ID；
- 50 个候选都有 reviewer、reviewed_at 和 `usable_for_e1`；
- 22 个固定抽查候选完成四维粗分和完整视频检查；
- failure tag 全部属于枚举；
- `usable_for_e1` 只能为 yes/no；
- E0 输入 checksum 未变化。

完成后写 `DEVLOG.md`，步骤 ID：`E0-visual-review-v01`，汇总：

- 每个 failure tag 数量；
- 三类任务的可用候选数；
- 系统性失败 sample；
- 可用于 E1 的 pair 预计数量；
- 是否允许进入 E1 Pilot。

### 6.1 E0 视觉放行规则

满足以下条件即可进入 E1 Pilot：

- 硬验收仍是 50/50 valid；
- 每类任务至少存在可判断的候选差异；
- 至少 7/10 个 sample 能形成有效 pair；
- 没有因路径错配导致“源视频和候选不属于同一 sample”的问题。

注意：E0 不要求 50 个结果视觉上全部成功。欠编辑、过编辑、闪烁和失败案例正是 E1 校准需要覆盖的数据。

`usable_for_e1=no` 只用于媒体无法判断、源/候选错配或严重裁剪错误等协议级问题。不能因为结果欠编辑、过编辑或视觉质量差就排除；这些真实失败必须保留给 E1。

---

# Part B：E1 Judge 可靠性施工

## 7. E1 Pilot 的冻结协议

### 7.1 数据范围

- 数据集：DAVIS 2017 train，仅使用 E0 的 10 个输入。
- 候选：E0 的 50 个真实候选，五个固定 seed。
- IVEBench：完全隔离，不得进入 E1 prompt 开发、人工校准或阈值选择。
- 每个 sample 对五个候选做全量两两组合，共 `C(5,2)=10` 个无序 pair。
- 总计：100 个唯一 pair。

### 7.2 开发/冻结评估划分

Prompt 开发集固定为：

```text
bear-white
dog-tiger
hiker-backpack
```

共 30 pairs，各覆盖属性、对象替换和局部编辑。

冻结评估集固定为：

```text
bus-red
elephant-pink
classic-car-blue
horse-zebra
mallard-swan
rider-helmet
car-headlights
```

共 70 pairs。冻结评估集只能在 prompt、解析规则、置信阈值和绝对分数差阈值锁定后运行。

禁止根据冻结评估结果修改同一版本 prompt 后重新报告。如果修改，必须：

- 新建 prompt version；
- 保留旧 raw response 和指标；
- 在 DEVLOG 说明修改原因；
- 使用新的实验 ID 或明确的 run 子目录。

### 7.3 Judge 方法

固定比较四种方法：

1. `absolute-v1`：50 个候选分别做绝对四维评分，再根据开发集冻结的差值阈值推导 100 个 pair。
2. `pairwise-single-v1`：100 个 pair，每对只按确定性随机方向判断一次。
3. `pairwise-swap-v1`：每对执行 A/B 和 B/A 两次，映射回候选身份后检查一致性。
4. `rubric-swap-v1`：分四维判断、给出证据与置信度，同样执行双向换位。

每个 judge 模型的标准调用预算：

| 方法 | 调用数 |
|---|---:|
| absolute | 50 |
| pairwise single | 100 |
| pairwise swap | 200 |
| rubric swap | 200 |
| 合计 | 550 |

真实运行前先使用 mock/replay 完成全部 550 条的 schema、缓存和报告验收。

---

## 8. E1 工程结构

Cline 新增独立包，不修改 W1 的 `mock/replay` 研究边界：

```text
src/e1_judge/
├── __init__.py
├── cli.py
├── models.py
├── hashing.py
├── pairs.py
├── packets.py
├── annotations.py
├── prompts.py
├── cache.py
├── runner.py
├── ranking.py
├── metrics.py
├── reporting.py
└── backends/
    ├── __init__.py
    ├── base.py
    ├── mock.py
    ├── replay.py
    └── command.py

configs/e1/
├── pilot.yaml
├── prompt-absolute-v1.yaml
├── prompt-pairwise-single-v1.yaml
├── prompt-pairwise-swap-v1.yaml
└── prompt-rubric-swap-v1.yaml

tests/e1/
├── test_models.py
├── test_pairs.py
├── test_packets.py
├── test_annotations.py
├── test_cache_and_resume.py
├── test_swap_logic.py
├── test_metrics.py
└── test_e2e_mock.py
```

更新 `pyproject.toml`：

```toml
[project.scripts]
w1 = "w1_pipeline.cli:app"
e1 = "e1_judge.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/w1_pipeline", "src/e1_judge"]
```

控制层优先只使用现有依赖和 Python 标准库，不把真实 VLM 的大型依赖加入 `w1-control`。真实模型通过独立 Python 环境和 command backend 调用。

更新入口后重新安装 editable 包并检查命令：

```bash
"$CONTROL_ENV/bin/pip" install --no-deps -e "$PROJECT"
"$CONTROL_ENV/bin/e1" --help
```

完成包骨架、CLI help 和 schema 测试后，写 `DEVLOG.md`，步骤 ID：`E1-scaffold-v01`。

---

## 9. E1 数据模型

所有 Pydantic model 使用 `extra="forbid"`。关键类型如下。

### 9.1 PairRecord

必需字段：

```text
pair_id
sample_id
task_type
instruction
target_caption
source_video_path
source_checksum
mask_paths
candidate_left_id
candidate_left_checksum
candidate_left_path
candidate_right_id
candidate_right_checksum
candidate_right_path
canonical_candidate_a_id
canonical_candidate_b_id
display_direction
split
randomization_seed
pair_schema_version
```

规则：

- canonical A/B 按 candidate ID 字典序固定，不能随展示方向变化；
- `display_direction` 只能为 `a_vs_b` 或 `b_vs_a`；
- 同一 pair 的 `pair_id` 不随 display direction 改变；
- 两个候选必须来自同一 sample，且 candidate ID 不同；
- 两个不同 seed 偶然产生相同 checksum 时仍是合法 pair，记录 `identical_media=true`，人工预期可以标为 tie；
- pair key 包含两候选 ID 和 checksum、源 checksum、instruction、target caption 和 schema version；
- 任何字段含 `IVEBench` 时拒绝。

### 9.2 HumanAnnotation

必需字段：

```text
annotation_id
pair_id
annotator_id
display_direction
faithfulness_preference
preservation_preference
temporal_consistency_preference
visual_quality_preference
overall_preference
confidence
failure_tags_a
failure_tags_b
notes
started_at
submitted_at
annotation_schema_version
```

每个 preference 只能为：

```text
a
b
tie
uncertain
```

保存前必须把屏幕上的 left/right 映射回 canonical A/B。原始展示方向仍要保留。

### 9.3 JudgeRequest

至少包含：

```text
request_id
pair_id 或 candidate_id
method
comparison_direction
source_checksum
candidate_a_checksum
candidate_b_checksum（absolute 时可空）
instruction
target_caption
task_type
media_packet_checksum
backend
model_name
model_revision
prompt_version
parser_version
generation_parameters
```

### 9.4 JudgeResult

至少包含：

```text
request_id
judge_key
status
dimensions_a
dimensions_b
per_dimension_preference
overall_preference
confidence
evidence
raw_response
parse_error
runtime_seconds
peak_vram_mb
prompt_version
model_revision
created_at
```

`raw_response` 必须保存原始文本或结构化响应，不得只保存最终 preference。

### 9.5 AdjudicatedLabel

保存：

- 两名独立标注；
- 是否一致；
- 第三人裁决（需要时）；
- 最终四维与 overall ground truth；
- human tie/uncertain；
- 裁决时间和协议版本。

完成 schema、序列化和拒绝非法数据的测试后，写 `DEVLOG.md`，步骤 ID：`E1-schema-v01`。

---

## 10. Pair 构造与视觉包

### 10.1 CLI

实现：

```bash
e1 build-pairs \
  --plan "$E0/plan.json" \
  --candidates "$E0/candidates.json" \
  --audit "$E0_AUDIT/audit.csv" \
  --config configs/e1/pilot.yaml \
  --output "$E1/pairs.jsonl"
```

要求：

- 输出 100 个无序 pair；
- 30 个 dev、70 个 frozen eval；
- 每个 sample 10 个 pair；
- pair 无重复、无跨 sample 组合；
- E0 审计中 `usable_for_e1=no` 的候选仍保留在原始清单，但相关 pair 标记 `excluded_reason`，不得静默删除；
- 默认主分析使用无 excluded reason 的 pair，并同时报告排除率。

### 10.2 确定性展示随机化

展示方向由以下信息的规范化 SHA-256 决定：

```text
pair_id + annotator_id + randomization_seed
```

不得调用未固定 seed 的随机数。不同 annotator 可以看到不同方向，但同一 annotator 断点恢复后方向必须不变。

### 10.3 Media packet

实现：

```bash
e1 build-packets \
  --pairs "$E1/pairs.jsonl" \
  --output-dir "$E1/media-packets"
```

每个 pair 目录：

```text
media-packets/<pair_id>/
├── source.mp4
├── candidate-a.mp4
├── candidate-b.mp4
├── source-contact.jpg
├── candidate-a-contact.jpg
├── candidate-b-contact.jpg
├── mask-overlay.jpg
└── metadata.json
```

空间控制：

- 默认不复制 E0 原视频，优先创建相对软链接；
- contact sheet 和低码率代理可以真实写入 E1；
- `metadata.json` 保存原始绝对路径和 checksum；
- 研究记录永远以 E0 原始视频 checksum 为身份，不以代理 checksum 替代。

联系表统一为 4×4，确保多图 VLM 可看到全部 16 帧。局部编辑保留 mask overlay；mask 不可用时明确写 `mask_available=false`。

完成 pair 和 packet 构造及测试后，写 `DEVLOG.md`，步骤 ID：`E1-pairs-packets-v01`。

---

## 11. 人工标注工具与协议

### 11.1 离线标注服务

实现以下命令，默认只监听 loopback：

```bash
e1 annotate \
  --pairs "$E1/pairs.jsonl" \
  --packets "$E1/media-packets" \
  --annotator-id annotator-01 \
  --output "$E1/human/annotator-01.jsonl" \
  --host 127.0.0.1 \
  --port 8765
```

优先使用 Python 标准库实现单用户 HTTP 服务，避免服务器临时联网安装 Web 框架。必须支持：

- 显示 source、left、right 视频和 contact sheet；
- 隐藏 seed、candidate ID、文件路径和生成配置；
- 四维偏好、overall、confidence、failure tags；
- 上一条/下一条；
- 自动保存和断点续标；
- 防止同一 annotator 重复提交同一 pair；
- 保存 display direction 并映射回 canonical A/B；
- 页面明确显示 instruction 与 target caption；
- 绑定地址默认 `127.0.0.1`，不得默认暴露公网。

本地访问使用 SSH 端口转发：

```bash
ssh -L 8765:127.0.0.1:8765 <学校服务器别名>
```

浏览器打开：

```text
http://127.0.0.1:8765
```

### 11.2 人工 rubric

每项只能选择 `A/B/tie/uncertain`：

1. **Faithfulness**：谁更正确、完整地执行 instruction；不能只依据画面更漂亮。
2. **Preservation**：谁更好地保留背景、运动、非目标对象和不应改变的主体属性。
3. **Temporal consistency**：谁的编辑区域更稳定，运动更连续，闪烁、漂移和突然消失更少。
4. **Visual quality**：谁的结构、纹理、边缘和整体画面更自然，伪影更少。
5. **Overall**：综合偏好，不通过预设线性权重自动计算，人工直接判断。

`tie` 表示两者质量确实接近；`uncertain` 表示证据不足、目标不可见、视频损坏或无法可靠判断。不得把二者合并。

### 11.3 标注人数与裁决

- 最低：两名独立标注者完整标注 100 pairs。
- 两人 overall 或任一关键维度不一致时，由第三人只标注争议 pair。
- 不向第二/第三标注者展示已有答案。
- 标注文件分开保存，禁止共用一个正在写入的 JSONL。

实现合并命令：

```bash
e1 adjudicate \
  --annotations "$E1/human/annotator-01.jsonl" \
  --annotations "$E1/human/annotator-02.jsonl" \
  --third "$E1/human/annotator-03.jsonl" \
  --output "$E1/human/adjudicated.jsonl"
```

必须报告：

- 每位标注者完成率；
- 两人一致率；
- 每维度 Cohen kappa 或等价一致性统计；
- 需要第三人裁决的数量；
- tie 和 uncertain 比例。

标注工具 mock 测试通过后写 `DEVLOG.md`，步骤 ID：`E1-annotation-tool-v01`。每一轮真实人工标注完成后分别追加记录。

---

## 12. Prompt 与输出协议

### 12.1 所有 prompt 的共同要求

- 明确 source、A、B 的角色；
- 先检查 instruction 可见性，再评价编辑；
- 不允许把“视觉更漂亮”自动等同于“更忠实”；
- preservation 必须与 source 对照；
- temporal 必须参考全部 16 帧，而不是单帧；
- 局部编辑优先参考 mask/ROI；
- 没有足够证据时输出 `uncertain`；
- 只输出严格 JSON，不使用 Markdown code fence；
- prompt 不包含 seed、candidate ID 或左右位置偏好暗示。

### 12.2 rubric-swap 输出 JSON

要求模型输出：

```json
{
  "faithfulness": {
    "preference": "a|b|tie|uncertain",
    "confidence": 0.0,
    "evidence": "short evidence"
  },
  "preservation": {
    "preference": "a|b|tie|uncertain",
    "confidence": 0.0,
    "evidence": "short evidence"
  },
  "temporal_consistency": {
    "preference": "a|b|tie|uncertain",
    "confidence": 0.0,
    "evidence": "short evidence"
  },
  "visual_quality": {
    "preference": "a|b|tie|uncertain",
    "confidence": 0.0,
    "evidence": "short evidence"
  },
  "overall_preference": "a|b|tie|uncertain",
  "overall_confidence": 0.0,
  "failure_tags_a": [],
  "failure_tags_b": []
}
```

confidence 范围为 `[0,1]`。解析器必须严格验证；格式错误保存 raw response 和 parse error，不能猜测修复语义。

### 12.3 Prompt 冻结

每个 prompt 文件必须包含：

- prompt version；
- schema version；
- 创建 commit；
- 使用的视觉输入形式；
- 模型 generation 参数；
- dev 集调参记录；
- frozen eval 前的 SHA-256。

开发集完成、prompt 冻结后，写 `DEVLOG.md`，步骤 ID：`E1-prompt-freeze-v01`。该记录必须早于 frozen eval 真实运行记录。

---

## 13. Judge backend、缓存与并发保护

### 13.1 Backend

实现三类控制层 backend：

- `mock`：确定性假结果，仅测 schema，不是研究测量；
- `replay`：严格回放已有真实结果；
- `command`：调用独立 judge 环境中的模型脚本。

`command` backend 接口：

```bash
<judge-python> <judge-script> \
  --request <request.json> \
  --output <response.json>
```

输出必须先写临时文件，再原子重命名。子进程非零退出、超时、OOM 和解析失败都写入 cache，并允许只重试失败请求。

### 13.2 Judge key

规范化 SHA-256 至少包含：

```text
source checksum
candidate A checksum
candidate B checksum
method
comparison direction
backend
model name
exact model revision
prompt version and prompt checksum
parser version
media packet checksum
complete generation parameters
code snapshot
```

JSON 字段顺序不得改变 key。A/B 与 B/A 必须产生不同 key。

### 13.3 SQLite

单独使用：

```text
$E1/cache.sqlite3
```

至少包含 request、status、raw response、parsed result、error、started/finished time、runtime 和 peak VRAM。缓存命中不得调用 backend。

### 13.4 排他锁

`e1 run` 启动时在实验目录建立 `.e1-run.lock`，使用原子 `O_CREAT|O_EXCL`。锁中记录 PID、hostname、command、started_at。

- 活跃锁：拒绝第二实例；
- 疑似陈旧锁：只报告，不自动删除；
- 由用户确认进程不存在后，使用显式 `e1 unlock --experiment-dir ... --reason ...`；
- unlock 必须写审计记录。

完成 backend/cache/lock 和中断恢复测试后写 `DEVLOG.md`，步骤 ID：`E1-runner-cache-v01`。

---

## 14. 离线真实 Judge 模型准备

具体模型必须在施工时根据以下事实选择，而不是凭名称猜测：

1. 服务器是否已有可用权重；
2. 是否支持视频或多图输入；
3. A6000 48GB 是否能完成 1 pair smoke；
4. snapshot、processor、tokenizer 和模板是否完整；
5. 模型许可证是否允许内部研究；
6. 是否能锁定精确 revision 和 SHA-256。

### 14.1 服务器权重盘点

先只读检查：

```bash
find "$DATA_ROOT/models" -maxdepth 3 \
  \( -name config.json -o -name '*.safetensors' -o -name tokenizer_config.json \) \
  -type f -printf '%p\n' | sort
```

不要使用会打印 credential/token 的命令。把候选模型、路径、大小、revision、输入能力和许可证写入 DEVLOG，步骤 ID：`E1-judge-model-inventory-v01`。

### 14.2 如果需要从外部准备模型

在可联网或可访问国内镜像的机器：

- 下载普通目录形式的完整 snapshot；
- 禁止只复制带失效 symlink 的 cache；
- 固定 model revision；
- 保存所有依赖 wheel 或 conda-pack；
- 生成 `SHA256SUMS`；
- 写 `MODEL_CARD_LOCAL.md`，记录来源、revision、许可证和预处理约定；
- 打包上传到 `/DATA/DATA4/hfy/models/<judge-name>-<revision>`。

服务器解包后先执行 `sha256sum -c SHA256SUMS`，再创建独立环境，例如：

```text
/DATA/DATA4/hfy/envs/e1-judge-<model>
```

不得无约束升级现有 `w1-control` 或 `anyv2v-cu118`。

### 14.3 真实 smoke 门

在 DEVLOG 先记录：

- 实验 ID：`E1-judge-smoke-v01`；
- code snapshot；
- 模型名、revision、权重 checksum；
- 两个 dev pair ID；
- 精度、量化、帧输入形式、generation 参数；
- 预计显存、运行时间和输出目录。

然后仅运行 2 个 dev pair 的 `rubric-swap`，共 4 个方向请求。验收：

- 4/4 请求成功；
- 严格 JSON 解析 4/4；
- A/B 与 B/A 均存在；
- 原始响应已保存；
- 峰值显存未超限；
- 相同请求重跑全部 cache hit，不重新调用模型。

smoke 失败不得直接提交 550 次批任务。

---

## 15. CLI 设计与执行顺序

E1 CLI 最低命令：

```text
e1 validate
e1 build-pairs
e1 build-packets
e1 annotate
e1 adjudicate
e1 plan
e1 run
e1 unlock
e1 merge-results
e1 analyze
e1 verify
e1 report
```

### 15.1 Mock E2E

```bash
test ! -e "$E1"

"$CONTROL_ENV/bin/e1" build-pairs \
  --plan "$E0/plan.json" \
  --candidates "$E0/candidates.json" \
  --audit "$E0_AUDIT/audit.csv" \
  --config "$PROJECT/configs/e1/pilot.yaml" \
  --output "$E1/pairs.jsonl"

"$CONTROL_ENV/bin/e1" build-packets \
  --pairs "$E1/pairs.jsonl" \
  --output-dir "$E1/media-packets"

"$CONTROL_ENV/bin/e1" plan \
  --pairs "$E1/pairs.jsonl" \
  --config "$PROJECT/configs/e1/pilot.yaml" \
  --output "$E1/judge-plan.json"

"$CONTROL_ENV/bin/e1" run \
  --backend mock \
  --plan "$E1/judge-plan.json" \
  --experiment-dir "$E1/mock" \
  --cache "$E1/mock/cache.sqlite3"

"$CONTROL_ENV/bin/e1" verify \
  --plan "$E1/judge-plan.json" \
  --results "$E1/mock/results.jsonl" \
  --expect-requests 550
```

Mock 必须得到 550/550，但报告必须醒目标记 `research_measurements=0`。

完成后写 `DEVLOG.md`，步骤 ID：`E1-mock-e2e-v01`。

### 15.2 人工标注

两名标注者完成全部 100 pair 后进行裁决：

```bash
"$CONTROL_ENV/bin/e1" adjudicate \
  --annotations "$E1/human/annotator-01.jsonl" \
  --annotations "$E1/human/annotator-02.jsonl" \
  --third "$E1/human/annotator-03.jsonl" \
  --output "$E1/human/adjudicated.jsonl"
```

如果没有争议项，`--third` 可以省略；如果存在争议项但第三人文件缺失，命令必须失败，不能自动任选一个答案。

### 15.3 Dev 真实 judge

先只运行 30 个 dev pairs 的四种方法：

```bash
"$CONTROL_ENV/bin/e1" run \
  --backend command \
  --plan "$E1/judge-plan.json" \
  --split dev \
  --experiment-dir "$E1/real/dev-v01" \
  --cache "$E1/cache.sqlite3" \
  --judge-python <离线judge环境/bin/python> \
  --judge-script <本地judge适配脚本>
```

只允许在 dev 上：

- 修 prompt 措辞；
- 修严格 JSON schema；
- 选择 absolute score 的差值阈值；
- 选择 confidence threshold；
- 修模型输入尺寸、帧采样和 OOM 参数。

完成后冻结 prompt 和阈值，追加 `E1-prompt-freeze-v01` DEVLOG。冻结后必须重新生成只引用最终 prompt checksum、parser version、阈值和模型参数的计划：

```bash
"$CONTROL_ENV/bin/e1" plan \
  --pairs "$E1/pairs.jsonl" \
  --config "$PROJECT/configs/e1/pilot.yaml" \
  --output "$E1/judge-plan-frozen.json"
```

预冻结的 `judge-plan.json` 保留用于 mock 和开发记录，不能冒充最终 frozen plan。

### 15.4 Frozen eval

冻结后先写真实作业前置 DEVLOG，实验 ID：`E1-judge-pilot-v01`，然后运行：

```bash
"$CONTROL_ENV/bin/e1" run \
  --backend command \
  --plan "$E1/judge-plan-frozen.json" \
  --split frozen-eval \
  --experiment-dir "$E1/real/frozen-eval-v01" \
  --cache "$E1/cache.sqlite3" \
  --judge-python <离线judge环境/bin/python> \
  --judge-script <本地judge适配脚本>
```

只允许重试 failed 请求；不得改变 prompt、阈值、模型 revision 或生成参数后继续写入同一 run 目录。

为了生成完整 100-pair 的最终结果，冻结后还要使用同一个 frozen plan 在 dev 上运行一次。它只用于完整记录和 dev 指标，不能用于 E1 放行门：

```bash
"$CONTROL_ENV/bin/e1" run \
  --backend command \
  --plan "$E1/judge-plan-frozen.json" \
  --split dev \
  --experiment-dir "$E1/real/dev-final-v01" \
  --cache "$E1/cache.sqlite3" \
  --judge-python <离线judge环境/bin/python> \
  --judge-script <本地judge适配脚本>

"$CONTROL_ENV/bin/e1" merge-results \
  --input "$E1/real/dev-final-v01/results.jsonl" \
  --input "$E1/real/frozen-eval-v01/results.jsonl" \
  --output "$E1/results.jsonl"
```

`merge-results` 必须拒绝重复 request ID、混入非 frozen prompt checksum 或不同模型 revision。

### 15.5 分析和报告

```bash
"$CONTROL_ENV/bin/e1" analyze \
  --pairs "$E1/pairs.jsonl" \
  --human "$E1/human/adjudicated.jsonl" \
  --results "$E1/results.jsonl" \
  --config "$PROJECT/configs/e1/pilot.yaml" \
  --output-dir "$E1/analysis"

"$CONTROL_ENV/bin/e1" verify \
  --plan "$E1/judge-plan-frozen.json" \
  --results "$E1/results.jsonl" \
  --human "$E1/human/adjudicated.jsonl" \
  --strict

"$CONTROL_ENV/bin/e1" report \
  --analysis "$E1/analysis" \
  --output-dir "$E1/report"
```

---

## 16. 指标定义

### 16.1 Pairwise accuracy

主准确率只在人工 adjudicated overall 为明确 `a` 或 `b` 的 pair 上计算：

```text
correct decisive predictions / human decisive pairs
```

Judge 输出 `tie/uncertain` 在主准确率中计为未正确，同时单独报告 coverage。不得通过大量拒答提高 accuracy。

同时报告：

- decisive-only accuracy；
- all-pair effective accuracy；
- high-confidence accuracy；
- high-confidence coverage；
- human tie/uncertain rate；
- judge tie/uncertain rate。

### 16.2 Swap consistency

将 `(A,B)` 和 `(B,A)` 的结果都映射回 canonical candidate 身份：

```text
mapped preferences equal / pairs with two successfully parsed directions
```

两个方向都 tie 视为一致；两个方向都 uncertain 视为一致但不算高置信覆盖；一个明确、一个 tie/uncertain 视为不一致。

### 16.3 Position bias

至少报告：

- 原始 left 选择率；
- 原始 right 选择率；
- swap 前后翻转率；
- A/B 方向准确率差；
- 配对检验或 bootstrap 置信区间。

### 16.4 排序相关性

对每个 sample 的五个候选：

- 人工 pair 使用 Bradley–Terry 或预先声明的 tie-aware 排序拟合效用；
- Judge 使用相同排序方法；
- 计算每个 sample 的 Kendall tau 和 Spearman；
- 再按 sample 汇总，不把同一 sample 的 10 个 pair 当作 10 个独立视频输入。

### 16.5 分类别表现

分别报告：

```text
attribute
object
local
```

至少包含 pair 数、accuracy、swap consistency、coverage 和 tie rate。

### 16.6 置信区间

- 固定 bootstrap seed：`20260820`；
- 以 `sample_id` 为 cluster 重采样；
- 2000 次 bootstrap；
- 报告 95% percentile CI；
- 由于 Pilot 只有 10 个 sample，报告中必须明确标记结果为 provisional。

完成 metrics 单元测试和合成案例验算后，写 `DEVLOG.md`，步骤 ID：`E1-metrics-v01`。

---

## 17. E1 判定门

项目原定硬门槛：

- overall pairwise accuracy `>= 70%`；
- swap consistency `>= 85%`。

建议同时执行两个防止虚假通过的操作护栏：

- high-confidence coverage `>= 60%`；
- attribute/object/local 任一类别 accuracy 不低于 `60%`。

判定结果写入：

```text
$E1/decision.json
```

允许值：

```text
PASS_PROVISIONAL
FAIL_REVISE_JUDGE
BLOCKED_MISSING_HUMAN_LABELS
BLOCKED_MISSING_REAL_JUDGE
```

### PASS_PROVISIONAL

满足硬门槛和操作护栏，冻结：

```text
$E1/reward-v0.yaml
```

`reward-v0.yaml` 必须包含：

- model name 和 exact revision；
- prompt version 和 checksum；
- media packet version；
- parser version；
- confidence threshold；
- swap 合并规则；
- tie/uncertain 处理；
- 四维输出定义；
- 是否以及如何形成 overall；
- E1 指标、CI 和数据范围；
- `provisional=true`。

通过后可以进入 E2 Best-of-N 探索，但在完成扩展版 E1 前不得声称 judge 已在广泛输入上得到充分验证。

### FAIL_REVISE_JUDGE

任一硬门槛失败时：

- 保留全部 raw response 和指标；
- 分析位置偏差、类别弱项、解析失败和置信度；
- 只在 dev 集修改 rubric、输入形式或阈值；
- 新建 prompt version 和实验目录；
- 暂停 E2/E3 正式结论与偏好训练对构造。

---

## 18. 测试计划

### 18.1 Schema

- 缺字段拒绝；
- 非法 preference、confidence、split 拒绝；
- 跨 sample pair 拒绝；
- 相同候选自比较拒绝；
- checksum 不匹配拒绝；
- IVEBench 内容拒绝；
- unknown extra fields 拒绝。

### 18.2 Pair 和 randomization

- 恰好 100 个 pair；
- 每 sample 恰好 10；
- dev 30、frozen eval 70；
- 字段顺序不改变 pair key；
- 同一 annotator 恢复时方向不变；
- canonical A/B 不随显示方向变化。

### 18.3 Cache 和 runner

- 字段顺序不改变 judge key；
- A/B 与 B/A key 不同；
- cache hit 不调用 backend；
- 中断后只运行 unfinished；
- 两个 runner 不能写同一目录；
- raw response 永久保存；
- 原子重命名失败不产生伪成功结果。

### 18.4 Swap

- A 优于 B + 换位后 B 位置对应同一候选，判一致；
- 明确 vs tie 判不一致；
- 两次 uncertain 判一致但不计高置信 coverage；
- 缺一个方向不能算 swap consistent。

### 18.5 Human annotation

- 页面 left/right 正确映射回 canonical A/B；
- 断点恢复不重复标注；
- 两人冲突且无第三人时 adjudicate 失败；
- tie 与 uncertain 不混用。

### 18.6 Metrics

用手工可验的微型结果测试：

- 100% accuracy；
- 全反准确率 0%；
- 位置翻转；
- tie/uncertain coverage；
- 分类别汇总；
- cluster bootstrap 固定 seed 可复现；
- Bradley–Terry 排序和 Kendall/Spearman 的已知顺序。

### 18.7 Mock E2E

必须生成：

- 100 pair；
- 550 judge requests；
- 550 mock results；
- 可重复 replay；
- 完整 report；
- `research_measurements=0`。

全部开发完成后运行：

```bash
cd "$PROJECT"
"$CONTROL_ENV/bin/python" -m pytest
git diff --check
```

测试完成后立即写 `DEVLOG.md`，步骤 ID：`E1-local-regression-v01` 或 `E1-server-regression-v01`。

---

## 19. W2/E1 最终产物

服务器最终目录应为：

```text
/DATA/DATA4/hfy/outputs/E1-judge-pilot-v01/
├── protocol.yaml
├── pairs.jsonl
├── split.json
├── media-packets/
├── human/
│   ├── annotator-01.jsonl
│   ├── annotator-02.jsonl
│   ├── annotator-03.jsonl
│   └── adjudicated.jsonl
├── prompts/
├── judge-plan.json
├── judge-plan-frozen.json
├── raw-responses/
├── real/
│   ├── dev-v01/
│   ├── dev-final-v01/
│   └── frozen-eval-v01/
├── cache.sqlite3
├── results.jsonl
├── analysis/
│   ├── metrics.json
│   ├── judge-reliability.csv
│   ├── position-bias.csv
│   ├── category-metrics.csv
│   └── ranking-correlations.csv
├── decision.json
├── reward-v0.yaml
├── run.log
├── SHA256SUMS
└── report/
    ├── E1_REPORT.md
    └── figures/
```

报告必须包含：

- 数据和 pair 数量；
- 人工标注协议、一致性和裁决数；
- 四种 judge 方法主表；
- 换位一致率和位置偏差；
- 四维与分类别表现；
- tie/uncertain 和 coverage；
- Kendall/Spearman；
- 95% cluster bootstrap CI；
- prompt/model/checksum 追溯；
- 代表成功案例；
- 至少两个 under-edit、两个 over-edit 或其他典型失败案例；
- PASS/FAIL/BLOCKED 判定；
- Pilot 规模限制和下一步。

---

## 20. 建议施工顺序与提交边界

严格按以下顺序，不要同时铺开多个未验证模块：

1. `E0-audit-preflight-v01`：只读预检并记 DEVLOG。
2. `E0-audit-hard-verify-v01`：复查 50/50。
3. `E0-audit-tool-v01`：实现审计脚本和测试，记 DEVLOG，提交 Git。
4. `E0-visual-audit-v01`：生成审计包并验 checksum。
5. `E0-visual-review-v01`：人工填写审计表，决定是否进入 E1。
6. `E1-scaffold-v01`：E1 包、CLI、配置骨架，测试后记 DEVLOG，提交 Git。
7. `E1-schema-v01`：严格 schema，测试后记 DEVLOG，提交 Git。
8. `E1-pairs-packets-v01`：100 pair 和 media packets，测试后记 DEVLOG，提交 Git。
9. `E1-annotation-tool-v01`：离线标注工具和裁决，测试后记 DEVLOG，提交 Git。
10. `E1-runner-cache-v01`：backend/cache/lock/resume，测试后记 DEVLOG，提交 Git。
11. `E1-metrics-v01`：统计和报告，测试后记 DEVLOG，提交 Git。
12. `E1-mock-e2e-v01`：550/550 mock/replay，记 DEVLOG。
13. `E1-human-label-v01`：两人标注和第三人裁决，逐轮记 DEVLOG。
14. `E1-judge-model-inventory-v01`：模型盘点或离线交付验收。
15. `E1-judge-smoke-v01`：2 pair、4 方向真实 smoke，前后各记 DEVLOG。
16. `E1-judge-dev-v01`：只在 30 dev pairs 调整。
17. `E1-prompt-freeze-v01`：冻结 prompt、阈值和 checksum。
18. `E1-judge-pilot-v01`：70 frozen eval pairs，前后各记 DEVLOG。
19. `E1-analysis-v01`：分析、report、decision 和 reward-v0。
20. 最终 `pytest`、`git diff --check`，记 DEVLOG 并提交 Git。

Git 提交只包含代码、配置、测试、prompt、文档和小型指标表。原视频、代理视频、模型权重、SQLite cache 和 raw 大文件不得提交 Git。

---

## 21. 停止条件

遇到以下情况，Cline 必须停止扩大执行，记录 DEVLOG 并报告用户：

- E0 verify 不再是 50/50；
- E0 plan/candidate checksum 与记录不一致；
- 已存在同名输出目录且来源不清楚；
- 同一实验目录发现第二个活跃 writer；
- 人工标注不足或争议未裁决；
- 真实 judge 模型 revision/许可证/checksum 不明确；
- 模型仍尝试访问外网；
- 2-pair smoke 解析率不足 100%；
- CUDA OOM 尚未在 dev smoke 解决；
- prompt 尚未冻结却准备运行 frozen eval；
- frozen eval 后有人要求覆盖旧结果重新运行修改后的 prompt。

`BLOCKED` 是合法结果。不得用 mock/replay 或粗审计分数冒充真实 Judge 可靠性结果。

---

## 22. Cline 完工汇报模板

Cline 最终回复用户时必须明确区分“代码完成”和“真实实验完成”，并使用以下结构：

```text
1. 当前 Git commit / dirty 状态
2. E0 硬验收：valid、count、errors
3. E0 视觉审计：50 联系表、22 代理、failure tag 汇总、系统性失败
4. E1 工程：已实现命令、测试数量、mock 550/550
5. 人工标注：人数、完成率、一致率、裁决数
6. 真实 judge：模型/revision、请求成功率、运行时间、峰值显存
7. E1 指标：accuracy、swap consistency、coverage、分类别、CI
8. 决策：PASS_PROVISIONAL / FAIL / BLOCKED
9. 产物绝对路径
10. 尚未完成的外部前置条件和下一步
```

如果真实 judge 或人工标注尚未完成，必须写明：

```text
E1 framework complete; E1 research acceptance not complete.
```

不得写“E1 已完成”或“reward 已可靠”。
