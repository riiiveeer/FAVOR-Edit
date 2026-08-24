# E1 v2：学校 A6000 真实 Judge 执行手册

本手册是 E1 schema-v2 的唯一服务器执行入口。它覆盖离线交付、Qwen2.5-VL-7B 环境、4-request smoke、两人标注与第三人裁决、dev selection、freeze、70-pair frozen gate、恢复和结果回传。

本地代码、mock 和合成 gate 通过不等于真实实验通过。完成本手册前，统一表述为：

> E1 framework complete; E1 research acceptance not complete.

## 1. 不可变基线和停止规则

固定实验根目录：

```text
/DATA/DATA4/hfy/outputs/E1-judge-pilot-v02
```

固定主候选：

- 模型：`Qwen/Qwen2.5-VL-7B-Instruct`
- Hugging Face revision：`a22b9b202f87d21defc75df2652beed712e52261`
- 普通 snapshot 目录：`/DATA/DATA4/hfy/models/Qwen2.5-VL-7B-Instruct-a22b9b2`
- dtype/device：BF16，单张 A6000
- attention：SDPA
- 生成：`do_sample=false`，其余参数来自冻结 prompt YAML
- 不安装 `flash-attn`

环境固定为：Python 3.11、PyTorch `2.1.2+cu118`、torchvision `0.16.2+cu118`、Transformers `4.49.0`、Accelerate `1.2.1`、`qwen-vl-utils 0.0.8`。该环境必须独立于现有 `w1-control` 和 `anyv2v-cu118`，不得升级、卸载或复用后两者中的包。

以下任一条件触发立即停止扩大任务，并写 DEVLOG：

- 目标实验根目录已经存在或来源不明；
- Git snapshot、模型 revision、模型 manifest 或 runtime fingerprint 不明确；
- 模型仍尝试联网；
- 两名主标注者未各自完成 100 个唯一 pair，或争议未由第三人完整裁决；
- 4-request smoke 不是 4/4 成功和 4/4 严格解析；
- smoke 缺任一 swap 方向、第二次不是全 cache hit，或峰值显存不低于 42 GB；
- 同一 experiment directory 存在活跃 writer；
- freeze 前代码或协议文件未提交，或 freeze 后有人要求改 prompt、阈值、模型 revision、generation 参数；
- 准备写入已有输出目录，或准备用 mock/replay 冒充真实测量。

禁止删除或覆盖旧 E0、旧 E1 或失败输出。失败重试仍使用同一身份和 cache；需要改变协议时使用新实验 ID。

## 2. 在联网 Linux x86_64 机器准备离线交付包

Windows wheel、Windows conda 环境不能交付给 Linux 服务器。准备机应尽量与学校服务器同为 Linux x86_64，并能访问 Hugging Face、PyPI 和 PyTorch wheel index。

### 2.1 固化代码

在本次提交推送后执行：

```bash
git clone https://github.com/riiiveeer/FAVOR-Edit.git
cd FAVOR-Edit
git checkout <本次最终40位commit>
test -z "$(git status --porcelain)"
git bundle create ../FAVOR-Edit-e1-v2.bundle --all
```

把 commit 写入交付包 `metadata/versions.txt`，不能只写 `main`。

### 2.2 下载普通模型 snapshot

不要复制 Hugging Face cache 中的悬空 symlink。固定 revision 下载成普通目录：

```bash
export DELIVERY_ROOT="$PWD/e1-v2-delivery"
export MODEL_DIR="$DELIVERY_ROOT/model/Qwen2.5-VL-7B-Instruct-a22b9b2"
mkdir -p "$MODEL_DIR" "$DELIVERY_ROOT/metadata"

python -m pip install "huggingface_hub==0.28.1"
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen2.5-VL-7B-Instruct",
    revision="a22b9b202f87d21defc75df2652beed712e52261",
    local_dir="e1-v2-delivery/model/Qwen2.5-VL-7B-Instruct-a22b9b2",
    local_dir_use_symlinks=False,
)
PY

test -f "$MODEL_DIR/config.json"
test -f "$MODEL_DIR/preprocessor_config.json"
find "$MODEL_DIR" -type l -print -quit | grep -q . && { echo "symlink forbidden"; exit 1; } || true
```

在模型目录外生成逐文件清单，再复制进去。生成清单时排除清单自身：

```bash
cd "$MODEL_DIR"
find . -type f ! -name MODEL_SHA256SUMS ! -name MODEL_CARD_LOCAL.md -print0 \
  | LC_ALL=C sort -z | xargs -0 sha256sum > ../MODEL_SHA256SUMS
cp ../MODEL_SHA256SUMS ./MODEL_SHA256SUMS
sha256sum MODEL_SHA256SUMS
```

将上述 `MODEL_SHA256SUMS` 文件自身的 64 位 SHA-256 写入服务器 runtime 的 `model.manifest_sha256`。`MODEL_CARD_LOCAL.md` 至少记录：模型 ID、固定 revision、下载日期、下载工具版本、许可证/使用边界、目录大小、manifest SHA、准备机 OS，以及“仅作为 E1 provisional judge，不代表已验证可靠”。

### 2.3 准备完整 wheelhouse 和独立 conda-pack

使用仓库文件 `configs/e1/qwen25-vl-cu118-requirements.txt`。先下载所有直接和传递依赖：

```bash
python3.11 -m venv /tmp/e1-wheel-builder
source /tmp/e1-wheel-builder/bin/activate
python -m pip install --upgrade pip
mkdir -p "$DELIVERY_ROOT/wheelhouse"
python -m pip download \
  --dest "$DELIVERY_ROOT/wheelhouse" \
  --extra-index-url https://download.pytorch.org/whl/cu118 \
  -r FAVOR-Edit/configs/e1/qwen25-vl-cu118-requirements.txt
deactivate
```

用 wheelhouse 离线安装一次，证明没有漏包，再打包：

```bash
conda create -y -p /tmp/e1-judge-qwen25-vl python=3.11 pip
conda run -p /tmp/e1-judge-qwen25-vl python -m pip install \
  --no-index --find-links "$DELIVERY_ROOT/wheelhouse" \
  -r FAVOR-Edit/configs/e1/qwen25-vl-cu118-requirements.txt
conda run -p /tmp/e1-judge-qwen25-vl python - <<'PY'
import torch, torchvision, transformers, accelerate, qwen_vl_utils
assert torch.__version__ == "2.1.2+cu118"
assert torchvision.__version__ == "0.16.2+cu118"
assert transformers.__version__ == "4.49.0"
assert accelerate.__version__ == "1.2.1"
assert torch.version.cuda == "11.8"
print("judge environment import check passed")
PY
conda install -y -p /tmp/e1-judge-qwen25-vl -c conda-forge conda-pack
conda pack -p /tmp/e1-judge-qwen25-vl \
  -o "$DELIVERY_ROOT/e1-judge-qwen25-vl-linux-x86_64.tar.gz"
```

不要执行 `pip install flash-attn`。若完整 conda-pack 已交付，wheelhouse 仍保留用于审计和少量修复，但不得在服务器无约束升级。

### 2.4 生成全交付包 SHA256SUMS

建议目录：

```text
e1-v2-delivery/
├── FAVOR-Edit-e1-v2.bundle
├── e1-judge-qwen25-vl-linux-x86_64.tar.gz
├── wheelhouse/
├── model/Qwen2.5-VL-7B-Instruct-a22b9b2/
└── metadata/
    ├── versions.txt
    └── SHA256SUMS
```

在交付根目录执行：

```bash
find . -type f ! -path './metadata/SHA256SUMS' -print0 \
  | LC_ALL=C sort -z | xargs -0 sha256sum > metadata/SHA256SUMS
sha256sum metadata/SHA256SUMS
```

`versions.txt` 至少包含 project commit、model revision、model manifest SHA、Python/CUDA/六个核心包版本、准备机 OS 和交付清单 SHA。

## 3. 学校服务器上传与只读验收

先上传到只读交付区；不要直接解压到实验目录：

```bash
export DELIVERY=/DATA/DATA4/hfy/deliveries/e1-v2
export PROJECT=/home/sunyinan/FAVOR-Edit
export MODEL_DIR=/DATA/DATA4/hfy/models/Qwen2.5-VL-7B-Instruct-a22b9b2
export JUDGE_ENV=/DATA/DATA4/hfy/envs/e1-judge-qwen25-vl
export E0=/DATA/DATA4/hfy/outputs/E0-anyv2v-w1-v01
export E0_AUDIT=/DATA/DATA4/hfy/outputs/E0-visual-audit-v01
export E1=/DATA/DATA4/hfy/outputs/E1-judge-pilot-v02
```

验收交付包：

```bash
cd "$DELIVERY"
sha256sum -c metadata/SHA256SUMS
test "$(sha256sum model/Qwen2.5-VL-7B-Instruct-a22b9b2/MODEL_SHA256SUMS | cut -d' ' -f1)" \
  = "$(grep '^model_manifest_sha256=' metadata/versions.txt | cut -d= -f2)"
cd model/Qwen2.5-VL-7B-Instruct-a22b9b2
sha256sum -c MODEL_SHA256SUMS
```

任一文件不是 `OK` 就停止。不要通过重新生成清单来掩盖上传损坏。

恢复代码和环境：

```bash
test ! -e "$PROJECT"
git clone "$DELIVERY/FAVOR-Edit-e1-v2.bundle" "$PROJECT"
git -C "$PROJECT" checkout --detach "$(grep '^project_commit=' "$DELIVERY/metadata/versions.txt" | cut -d= -f2)"
test -z "$(git -C "$PROJECT" status --porcelain)"

test ! -e "$JUDGE_ENV"
mkdir -p "$JUDGE_ENV"
tar -xzf "$DELIVERY/e1-judge-qwen25-vl-linux-x86_64.tar.gz" -C "$JUDGE_ENV"
"$JUDGE_ENV/bin/conda-unpack"
```

模型复制到固定路径后再次验收：

```bash
test ! -e "$MODEL_DIR"
cp -a "$DELIVERY/model/Qwen2.5-VL-7B-Instruct-a22b9b2" "$MODEL_DIR"
cd "$MODEL_DIR"
sha256sum -c MODEL_SHA256SUMS
```

不得改动现有 `w1-control` 或 `anyv2v-cu118`。控制命令继续使用当前项目的 `uv run e1` 或已验证的 `w1-control` 安装；模型 adapter 只由 `$JUDGE_ENV/bin/python` 启动。

## 4. A6000、环境和离线预检

```bash
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version \
  --format=csv,noheader
df -h /DATA/DATA4/hfy

"$JUDGE_ENV/bin/python" - <<'PY'
import torch, torchvision, transformers, accelerate
assert torch.cuda.is_available()
assert torch.cuda.get_device_name(0).endswith("A6000")
assert torch.__version__ == "2.1.2+cu118"
assert torchvision.__version__ == "0.16.2+cu118"
assert transformers.__version__ == "4.49.0"
assert accelerate.__version__ == "1.2.1"
print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory)
PY
```

设置离线变量，tmux 中也必须设置：

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
```

仅加载 processor 配置的离线检查：

```bash
"$JUDGE_ENV/bin/python" - <<'PY'
from transformers import AutoProcessor
p = AutoProcessor.from_pretrained(
    "/DATA/DATA4/hfy/models/Qwen2.5-VL-7B-Instruct-a22b9b2",
    local_files_only=True,
)
print(type(p).__name__)
PY
```

## 5. 创建唯一 E1 v02 根目录和 v2 媒体包

首先确认 E0 只读输入存在，并保存前置 checksum：

```bash
test -f "$E0/plan.json"
test -f "$E0/candidates.json"
test -f "$E0_AUDIT/audit.csv"
sha256sum "$E0/plan.json" "$E0/candidates.json" "$E0_AUDIT/audit.csv"
test ! -e "$E1"
mkdir -p "$E1"/{inputs,human,plans,runs,logs}
```

配置 runtime，不要直接修改仓库 example：

```bash
cp "$PROJECT/configs/e1/runtime-qwen25-vl-7b.example.yaml" "$E1/runtime-dev.yaml"
export MODEL_MANIFEST_SHA=$(sha256sum "$MODEL_DIR/MODEL_SHA256SUMS" | cut -d' ' -f1)
cd "$PROJECT"
uv run python - "$E1/runtime-dev.yaml" <<'PY'
import os, sys, yaml
from pathlib import Path
p = Path(sys.argv[1])
d = yaml.safe_load(p.read_text())
d["model"]["manifest_sha256"] = os.environ["MODEL_MANIFEST_SHA"]
d["adapter"]["python"] = "/DATA/DATA4/hfy/envs/e1-judge-qwen25-vl/bin/python"
d["adapter"]["script"] = "/home/sunyinan/FAVOR-Edit/scripts/e1_judge_qwen25_vl.py"
p.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
PY

cd "$PROJECT"
uv run e1 validate --runtime "$E1/runtime-dev.yaml"
uv run e1 build-pairs \
  --plan "$E0/plan.json" --candidates "$E0/candidates.json" \
  --audit "$E0_AUDIT/audit.csv" --config configs/e1/pilot.yaml \
  --output "$E1/inputs/pairs.jsonl"
uv run e1 build-packets \
  --pairs "$E1/inputs/pairs.jsonl" --output-dir "$E1/inputs/media-packets"
uv run e1 plan \
  --pairs "$E1/inputs/pairs.jsonl" --packets "$E1/inputs/media-packets" \
  --config configs/e1/pilot.yaml --runtime "$E1/runtime-dev.yaml" \
  --output "$E1/plans/judge-plan-development.jsonl"
```

验收数量：100 pair、10 个共享 source、50 个共享 candidate、每资产完整 16 帧，plan 共 550 request（dev 165、frozen 385）。任何计数不符都停止。

## 6. DEVLOG 前置与后置模板

每个 GPU job 启动前，先在 `DEVLOG.md` 写：

```text
时间/环境：<ISO时间>，school A6000，GPU/driver
实验 ID：<唯一ID>
代码：<git rev-parse HEAD；git status --short>
模型：Qwen2.5-VL-7B-Instruct，revision a22b...，MODEL_SHA256SUMS SHA
数据：DAVIS train；dev/frozen split；pair/request 数
命令/配置：完整命令，prompt checksum，parser，generation，runtime fingerprint
预期产物：绝对路径；禁止覆盖确认
资源估计：单 A6000，BF16/SDPA，预期峰值 <42GB，预期时长/磁盘
下一步：仅在 gate 通过后扩大
```

结束、失败或中断后，立即补：

```text
状态：DONE / FAILED / INTERRUPTED
runtime：总时长
peak VRAM：results.jsonl 的最大 peak_vram_mb
结果：selected/cache_hits/attempted/succeeded/failed，严格解析率
产物：experiment dir、cache、results、raw、stdout/stderr/run.log
异常：错误类型、受影响 judge_key、是否 retryable
下一步：重试同身份 / 停止并修订 dev / 进入下一 gate
```

## 7. 4-request 真实 smoke

从 development plan 选择两个 swap 方法各一个 pair 的双方向，形成 4 条独立 smoke plan：

```bash
cd "$PROJECT"
uv run python - \
  "$E1/plans/judge-plan-development.jsonl" "$E1/plans/smoke-4.jsonl" <<'PY'
import json, sys
from pathlib import Path
src, dst = map(Path, sys.argv[1:])
rows = [json.loads(x) for x in src.read_text().splitlines() if x.strip()]
chosen = []
for method in ("pairwise-swap-v1", "rubric-swap-v1"):
    pair_id = next(r["pair_id"] for r in rows if r["split"] == "dev" and r["method"] == method)
    chosen.extend(r for r in rows if r["method"] == method and r["pair_id"] == pair_id)
assert len(chosen) == 4
dst.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in chosen))
PY
```

写 `E1-judge-smoke-v02` 前置 DEVLOG 后，在一个 tmux session 中以单 writer 运行：

```bash
test ! -e "$E1/runs/smoke-4-v01"
tmux new -s e1-smoke-v02
cd "$PROJECT"
uv run e1 run \
  --plan "$E1/plans/smoke-4.jsonl" --runtime "$E1/runtime-dev.yaml" \
  --experiment-dir "$E1/runs/smoke-4-v01" \
  --cache "$E1/cache-smoke.sqlite3" \
  2>&1 | tee "$E1/logs/smoke-4-first.log"
```

同一命令原样重跑一次，只更换 tee 日志名；experiment dir 和 cache 不变：

```bash
uv run e1 run \
  --plan "$E1/plans/smoke-4.jsonl" --runtime "$E1/runtime-dev.yaml" \
  --experiment-dir "$E1/runs/smoke-4-v01" \
  --cache "$E1/cache-smoke.sqlite3" \
  2>&1 | tee "$E1/logs/smoke-4-cache-rerun.log"
uv run e1 verify --plan "$E1/plans/smoke-4.jsonl" \
  --results "$E1/runs/smoke-4-v01/results.jsonl" --expect-requests 4 --strict
```

smoke 门必须同时满足：

- 4/4 succeeded；
- 4/4 从 raw text 严格 JSON 重解析成功；
- pairwise-swap 和 rubric-swap 均包含 `a_vs_b`、`b_vs_a`；
- 第二次输出为 4 cache hits、0 attempted；
- `max(peak_vram_mb) < 43008`（42×1024 MB）；
- raw response、adapter stdout/stderr 和 run log 均保留。

任一失败立即停止，不运行完整 dev。

## 8. 两名主标注者和第三人争议裁决

两名主标注者必须使用不同 ID，各自完成全部 100 个唯一 pair。通过 SSH port forward 访问仅绑定回环地址的服务，例如本地执行 `ssh -L 8765:127.0.0.1:8765 <server>`。

服务器依次启动：

```bash
uv run e1 annotate --pairs "$E1/inputs/pairs.jsonl" \
  --packets "$E1/inputs/media-packets" --annotator-id primary-01 \
  --output "$E1/human/primary-01.jsonl" --host 127.0.0.1 --port 8765

uv run e1 annotate --pairs "$E1/inputs/pairs.jsonl" \
  --packets "$E1/inputs/media-packets" --annotator-id primary-02 \
  --output "$E1/human/primary-02.jsonl" --host 127.0.0.1 --port 8766
```

页面每次提交立即追加，重启后自动定位下一条，重复提交返回 409。完成后第一次裁决：

```bash
if uv run e1 adjudicate \
  --annotations "$E1/human/primary-01.jsonl" \
  --annotations "$E1/human/primary-02.jsonl" \
  --output "$E1/human/adjudicated.jsonl" \
  --report "$E1/human/agreement-precheck.json"; then
  echo "no disputes; adjudication complete"
else
  echo "disputes require third annotator"
fi
```

有争议时，precheck 已包含精确 `disputed_pair_ids`、逐维 agreement、Cohen kappa、完成率和争议数。第三人只加载争议清单：

```bash
uv run e1 annotate --pairs "$E1/inputs/pairs.jsonl" \
  --packets "$E1/inputs/media-packets" --annotator-id adjudicator-03 \
  --pair-filter "$E1/human/agreement-precheck.json" \
  --output "$E1/human/adjudicator-03.jsonl" --host 127.0.0.1 --port 8767

uv run e1 adjudicate \
  --annotations "$E1/human/primary-01.jsonl" \
  --annotations "$E1/human/primary-02.jsonl" \
  --third "$E1/human/adjudicator-03.jsonl" \
  --output "$E1/human/adjudicated.jsonl" \
  --report "$E1/human/agreement-final.json"
```

若无争议，第一次命令已经生成 final labels；`agreement-precheck.json` 即完成报告。不得为了提高一致率让两名主标注者互相看答案。

## 9. 30 dev pairs 的四方法运行与选择

写 `E1-judge-dev-v02` 前置 DEVLOG，确认 smoke 已通过，再运行完整 dev split（15 absolute + 30 single + 60 pairwise-swap + 60 rubric-swap = 165 requests）：

```bash
test ! -e "$E1/runs/dev-selection-v01"
uv run e1 run \
  --plan "$E1/plans/judge-plan-development.jsonl" --runtime "$E1/runtime-dev.yaml" \
  --split dev --experiment-dir "$E1/runs/dev-selection-v01" \
  --cache "$E1/cache-dev.sqlite3" 2>&1 | tee "$E1/logs/dev-selection.log"

uv run e1 analyze --mode dev --pairs "$E1/inputs/pairs.jsonl" \
  --human "$E1/human/adjudicated.jsonl" \
  --results "$E1/runs/dev-selection-v01/results.jsonl" \
  --config "$PROJECT/configs/e1/pilot.yaml" \
  --output-dir "$E1/analysis-dev-v01"
```

dev 自动扫描 confidence `[0.5,0.6,0.7,0.8,0.9]` 和 absolute delta `[0,0.25,0.5,0.75,1.0]`。只有 pairwise-swap/rubric-swap 可成为最终方法；先要求 swap≥0.85、coverage≥0.60，再按 effective accuracy 选择，差值≤0.01 时选 rubric-swap。

若 `dev-selection.json` 为 blocked，停止，保留 raw 后在新 prompt version/新 experiment ID 上重做 dev。不得查看 frozen labels 指标后回改。

## 10. Freeze 和 selected-method 子计划

freeze 前把所有会影响协议的文件和 DEVLOG 提交，确保 `git status --porcelain` 为空。服务器实验日志可在专用本地分支提交；若 prompt/代码有任何改动也必须经过测试并形成 commit。

```bash
cd "$PROJECT"
test -z "$(git status --porcelain)"
test ! -e "$E1/frozen-v01"
uv run e1 freeze \
  --dev-selection "$E1/analysis-dev-v01/dev-selection.json" \
  --pairs "$E1/inputs/pairs.jsonl" --packets "$E1/inputs/media-packets" \
  --config configs/e1/pilot.yaml --runtime "$E1/runtime-dev.yaml" \
  --output-dir "$E1/frozen-v01"
```

`protocol.lock.json` 固化选择、阈值、code snapshot、config、四个 prompt、runtime、完整 550-plan checksum 和 protocol fingerprint。冻结后从完整 plan 派生 selected-method 子计划；只筛选，不修改请求内容：

```bash
cd "$PROJECT"
uv run python - \
  "$E1/frozen-v01/protocol.lock.json" \
  "$E1/frozen-v01/judge-plan-frozen.jsonl" \
  "$E1/plans/frozen-selected-all.jsonl" <<'PY'
import json, sys
from pathlib import Path
lock, src, dst = map(Path, sys.argv[1:])
method = json.loads(lock.read_text())["selected_method"]
rows = [json.loads(x) for x in src.read_text().splitlines() if x.strip()]
chosen = [r for r in rows if r["method"] == method]
assert len(chosen) == 200
assert sum(r["split"] == "dev" for r in chosen) == 60
assert sum(r["split"] == "frozen-eval" for r in chosen) == 140
dst.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in chosen))
PY
```

不要手工编辑 frozen YAML、lock、完整 plan 或子计划。为 frozen eval 写前置 DEVLOG 后才能继续。

## 11. 70 frozen eval、dev-final、merge 和最终 gate

顺序固定：先 70 frozen，再以完全相同 frozen runtime 补 30 dev-final。二者都只运行冻结选定方法。

```bash
test ! -e "$E1/runs/frozen-eval-v01"
uv run e1 run \
  --plan "$E1/plans/frozen-selected-all.jsonl" \
  --runtime "$E1/frozen-v01/protocol/runtime-frozen.yaml" \
  --split frozen-eval --experiment-dir "$E1/runs/frozen-eval-v01" \
  --cache "$E1/cache-frozen.sqlite3" 2>&1 | tee "$E1/logs/frozen-eval.log"

test ! -e "$E1/runs/dev-final-v01"
uv run e1 run \
  --plan "$E1/plans/frozen-selected-all.jsonl" \
  --runtime "$E1/frozen-v01/protocol/runtime-frozen.yaml" \
  --split dev --experiment-dir "$E1/runs/dev-final-v01" \
  --cache "$E1/cache-frozen.sqlite3" 2>&1 | tee "$E1/logs/dev-final.log"

uv run e1 merge-results \
  --input "$E1/runs/frozen-eval-v01/results.jsonl" \
  --input "$E1/runs/dev-final-v01/results.jsonl" \
  --output "$E1/results-frozen-selected.jsonl"

uv run e1 verify --plan "$E1/plans/frozen-selected-all.jsonl" \
  --results "$E1/results-frozen-selected.jsonl" \
  --human "$E1/human/adjudicated.jsonl" --expect-requests 200 --strict

uv run e1 analyze --mode final --pairs "$E1/inputs/pairs.jsonl" \
  --human "$E1/human/adjudicated.jsonl" \
  --results "$E1/results-frozen-selected.jsonl" \
  --config "$E1/frozen-v01/protocol/pilot-frozen.yaml" \
  --frozen-protocol "$E1/frozen-v01/protocol.lock.json" \
  --output-dir "$E1/analysis-final-v01"

uv run e1 report --analysis "$E1/analysis-final-v01" \
  --output-dir "$E1/report-final-v01"
```

最终 gate 仅使用 70 frozen pairs：accuracy≥0.70、swap≥0.85、coverage≥0.60、attribute/object/local 各类别 accuracy≥0.60。四项全过才产生 `PASS_PROVISIONAL` 和 `reward-v0.yaml`；否则必须是 `FAIL_REVISE_JUDGE`，不得进入 E2。

## 12. 单 writer、日志与恢复

每个 `e1 run` 对 experiment directory 建立 `.e1-run.lock`。command backend 对整个 shard 只启动一次模型进程；adapter 每完成一条就原子写 `<judge_key>.json`。进程崩溃后，runner 会吸收已写成功项，缺失或失败项留在 cache 中但不算命中。

正常中断后，原样重跑同一命令：成功项 cache hit，failed 自动重试，`results.jsonl` 从 plan 和成功 cache 确定性重建。不要删除 `batches/`、`raw-responses/` 或 SQLite。

若机器被强杀而残留锁：

1. 读取 `.e1-run.lock` 的 PID/host/time；
2. 用 `ps -fp <PID>` 和 `nvidia-smi` 确认进程确实不存在；
3. 写 DEVLOG，记录判定和原因；
4. 执行 `uv run e1 unlock --experiment-dir <dir> --reason '<明确原因>'`；
5. 原样重跑。

绝不在 writer 仍活跃时 unlock。若需要改 prompt、runtime、模型或 generation 参数，不是恢复；应新建实验 ID，重新 plan/dev/freeze。

## 13. 最终产物和回传

预期目录：

```text
/DATA/DATA4/hfy/outputs/E1-judge-pilot-v02/
├── inputs/{pairs.jsonl,media-packets/}
├── human/{primary-01.jsonl,primary-02.jsonl,adjudicated.jsonl,agreement*.json}
├── plans/{judge-plan-development.jsonl,smoke-4.jsonl,frozen-selected-all.jsonl}
├── frozen-v01/{protocol.lock.json,judge-plan-frozen.jsonl,protocol/}
├── runs/{smoke-4-v01,dev-selection-v01,frozen-eval-v01,dev-final-v01}/
├── analysis-dev-v01/
├── analysis-final-v01/{metrics.json,decision.json,reward-v0.yaml?}
├── report-final-v01/
├── runtime-dev.yaml
├── cache-smoke.sqlite3
├── cache-dev.sqlite3
├── cache-frozen.sqlite3
├── results-frozen-selected.jsonl
└── logs/
```

为整个结果生成清单，不覆盖已有清单：

```bash
test ! -e "$E1/SHA256SUMS"
cd "$E1"
find . -type f ! -name SHA256SUMS -print0 \
  | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS
sha256sum -c SHA256SUMS
```

至少带回 protocol lock、完整/子计划、runtime、human 原始与裁决结果、所有 results/raw responses、analysis、decision、可选 reward、report、日志、SHA256SUMS 和更新后的 DEVLOG。视频媒体和 SQLite 很大时可以分别打包，但不能只带汇总指标而丢失 raw response。

最后再次核对 E0 的三个输入 checksum 与第 5 节一致，证明本次 E1 没有修改既有 E0 研究产物。
