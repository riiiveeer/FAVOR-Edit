# W1 学校 A6000 离线交付与执行手册

本手册用于把当前 W1 工程交付到不能访问 GitHub/Hugging Face/PyPI 官方源的学校服务器，并完成 AnyV2V(I2VGen-XL) + InstructPix2Pix 的真实 smoke test 和 10×5 候选生成。

> 当前工程代码基线：`1c61c85c5b75125aed491d91993e846d42d0b5e4`。实际打包前请以 `git rev-parse HEAD` 输出为准，并把最终 SHA 写入交付包的 `metadata/versions.txt`。

## 1. 最终要交付什么

建议在可联网机器或其他可获取资源的 Linux x86_64 机器上生成一个目录：

```text
w1-school-delivery/
├── bundles/
│   ├── robust-v2v-w1.bundle          # 本项目完整 Git bundle
│   └── AnyV2V.bundle                 # 官方 AnyV2V 完整 Git bundle
├── envs/
│   ├── w1-control-linux-x86_64.tar.gz
│   └── anyv2v-cu118-linux-x86_64.tar.gz
├── models/
│   ├── i2vgen-xl/                    # Diffusers 格式，本地可直接 from_pretrained
│   └── instruct-pix2pix/             # Diffusers 格式；不需要原始 7.7GB ckpt
├── data/
│   └── DAVIS/
│       ├── JPEGImages/480p/<10个序列>/
│       └── Annotations/480p/<10个序列>/
├── metadata/
│   ├── versions.txt
│   ├── licenses/
│   └── SHA256SUMS
└── README-FIRST.txt
```

必须携带以下内容，不能等服务器运行时再下载：

1. 本项目 Git bundle；
2. AnyV2V Git bundle及其确切 commit；
3. `ali-vilab/i2vgen-xl` 的完整 Diffusers snapshot；
4. `timbrooks/instruct-pix2pix` 的 Diffusers snapshot；
5. DAVIS 2017 480p 的以下十条序列及对应 annotations；
6. 最稳妥情况下，两个 Linux x86_64 环境包；
7. 全包 SHA-256 和许可文件。

十条 DAVIS 序列为：

```text
bear bus elephant classic-car dog-gooses
horsejump-low mallard-water hike scooter-gray drift-turn
```

建议交付盘至少预留 70GB；学校服务器运行目录至少预留 120GB，推荐 150GB。I2VGen-XL snapshot 约 25GB；完整 InstructPix2Pix 仓库约 32GB，但 Diffusers 推理不需要根目录的原始 `.ckpt` 和重复的 7.7GB 单文件权重。

## 2. 在可联网机器上准备交付包

### 2.1 固化本项目代码

在 `D:\lab idea` 执行：

```powershell
git status --short
git rev-parse HEAD
git bundle create robust-v2v-w1.bundle --all
```

要求 `git status --short` 为空。把 bundle 放入 `w1-school-delivery/bundles/`。

### 2.2 获取并固化 AnyV2V

这一步必须在能访问 GitHub 的机器完成：

```bash
git clone https://github.com/TIGER-AI-Lab/AnyV2V.git
git -C AnyV2V rev-parse HEAD
git -C AnyV2V bundle create ../AnyV2V.bundle --all
```

把 40 位 SHA 写进 `metadata/versions.txt`，不要只写 `main`。学校服务器只从 bundle 克隆，禁止再执行 `git fetch`。

### 2.3 下载两个模型 snapshot

推荐在可联网 Linux 机器下载为普通目录，不要只复制 Hugging Face cache 中的 symlink。先记录精确 revision：

```bash
python -m pip install "huggingface_hub==0.20.3"
python - <<'PY'
from huggingface_hub import model_info
for model in ("ali-vilab/i2vgen-xl", "timbrooks/instruct-pix2pix"):
    info = model_info(model)
    print(model, info.sha)
PY
```

再按输出的 40 位 revision 下载：

```bash
huggingface-cli download ali-vilab/i2vgen-xl \
  --revision <I2VGEN_SHA> \
  --local-dir w1-school-delivery/models/i2vgen-xl \
  --local-dir-use-symlinks False

huggingface-cli download timbrooks/instruct-pix2pix \
  --revision <IP2P_SHA> \
  --local-dir w1-school-delivery/models/instruct-pix2pix \
  --local-dir-use-symlinks False \
  --exclude "*.ckpt" "instruct-pix2pix-00-22000.safetensors"
```

下载后确认两个目录都存在 `model_index.json`。I2VGen-XL 的固定参考 revision 可使用 `d41c055a132139a42cd0d5bed9de53f27c025177`，但仍应在打包时记录实际 revision。该 Hugging Face snapshot 约 24.8GB。[I2VGen-XL snapshot](https://huggingface.co/ali-vilab/i2vgen-xl/tree/d41c055a132139a42cd0d5bed9de53f27c025177)

如果只能访问国内 ModelScope，`damo/i2vgen-xl` 可作为下载来源，但不能默认认为它与 Hugging Face Diffusers 目录完全兼容。下载后必须确认含 `model_index.json` 以及 `feature_extractor/image_encoder/scheduler/text_encoder/tokenizer/unet/vae`；否则不要替换本项目所需的 snapshot。[ModelScope I2VGen-XL 说明](https://community.modelscope.cn/658cf509dafaf23eeaee3df4.html)

InstructPix2Pix 也必须是 Diffusers 目录，而不是只有一个 `.ckpt` 或 `.safetensors` 文件。AnyV2V 官方包装器默认调用 `timbrooks/instruct-pix2pix`。[官方模型页](https://huggingface.co/timbrooks/instruct-pix2pix/tree/main)

### 2.4 准备 DAVIS 数据

建议只携带十条序列，以减少传输量。目录名必须保持原样：

```text
data/DAVIS/JPEGImages/480p/bear/*.jpg
data/DAVIS/Annotations/480p/bear/*.png
...
```

不要把本地已经生成的 `data/processed/w1/manifest.json` 从 Windows 原样复制给 Linux 使用，因为其中保存的是 Windows 绝对路径。应把原始 DAVIS 帧和 mask 传到服务器，再在服务器上重新运行 `w1 prepare`。

### 2.5 准备 Python/CUDA 环境

推荐交付两个 `conda-pack` 环境：

- `w1-control`：Python 3.11，运行本项目 CLI、缓存、校验和报告；
- `anyv2v-cu118`：Python 3.9、PyTorch CUDA 11.8、Diffusers 0.26.3，运行真实模型。

环境包必须在 Linux x86_64 上创建，Windows conda 环境不能复制到 Linux。

建议 GPU 环境核心版本：

```text
python=3.9
pytorch=2.1.x
pytorch-cuda=11.8
diffusers=0.26.3
huggingface_hub=0.20.3
transformers=4.37.x
accelerate=0.27.x
omegaconf
opencv-python-headless
moviepy=1.0.3
imageio
imageio-ffmpeg
```

先在联网 Linux 机器完成一次 `import torch, diffusers, transformers`，然后：

```bash
conda install -n w1-control -c conda-forge conda-pack
conda install -n anyv2v-cu118 -c conda-forge conda-pack
conda pack -n w1-control -o w1-control-linux-x86_64.tar.gz
conda pack -n anyv2v-cu118 -o anyv2v-cu118-linux-x86_64.tar.gz
```

如果无法提前制作环境包，可在学校服务器通过允许访问的国内镜像安装。清华镜像提供 Anaconda、conda-forge、PyTorch 等 channel 配置方式；是否包含 NVIDIA channel 必须现场验证。[清华 Anaconda 镜像帮助](https://mirrors4.tuna.tsinghua.edu.cn/help/anaconda/)

PyPI 临时镜像：

```bash
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
```

此方案只作为环境包不可用时的备选。模型权重和 AnyV2V 代码仍应随交付包携带，不能依赖镜像临时补齐。

### 2.6 生成交付校验和

在交付目录上一级执行：

```bash
cd w1-school-delivery
find bundles envs models data metadata/licenses -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum > metadata/SHA256SUMS
```

`metadata/versions.txt` 至少记录：

```text
w1_git_commit=<40位SHA>
anyv2v_git_commit=<40位SHA>
i2vgen_xl_revision=<40位SHA>
instruct_pix2pix_revision=<40位SHA>
environment_build_os=<Linux发行版和版本>
cuda_runtime=11.8
```

## 3. 上传到学校服务器

推荐服务器目录：

```text
/data/<用户名>/w1-delivery/       # 原始交付包，只读保存
/data/<用户名>/w1-workspace/      # 实际运行目录
/data/<用户名>/w1-envs/           # 解压后的环境
```

使用学校允许的 SFTP、校园网中转盘或移动硬盘上传。大目录优先先打包再传，防止大量小文件丢失：

```bash
tar -I 'zstd -10 -T0' -cf w1-school-delivery.tar.zst w1-school-delivery/
```

服务器收到后：

```bash
cd /data/<用户名>
tar --use-compress-program=unzstd -xf w1-school-delivery.tar.zst
cd w1-school-delivery
sha256sum -c metadata/SHA256SUMS
```

必须看到所有文件均为 `OK`。有任意 checksum 失败都应停止，不要进入环境安装或推理。

## 4. 学校服务器详细操作

下面假设：

```bash
export DELIVERY=/data/<用户名>/w1-school-delivery
export WORK=/data/<用户名>/w1-workspace
export ENVS=/data/<用户名>/w1-envs
```

不要把 `$HOME` 用作大模型、数据或实验输出目录。

### 4.1 硬件和系统预检

```bash
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader
df -h /data/<用户名>
uname -a
```

要求：

- GPU 名称包含 `NVIDIA RTX A6000`；
- 总显存约 48GB；运行 smoke 前尽量有 45GB 以上空闲；
- 工作盘至少 120GB 空闲，推荐 150GB；
- Linux x86_64；NVIDIA driver 能运行 CUDA 11.8 构建的 PyTorch。

### 4.2 从 bundle 恢复两个仓库

```bash
mkdir -p "$WORK/external" "$WORK/artifacts" "$ENVS"

git clone "$DELIVERY/bundles/robust-v2v-w1.bundle" "$WORK/project"
git -C "$WORK/project" checkout --detach "$(grep '^w1_git_commit=' "$DELIVERY/metadata/versions.txt" | cut -d= -f2)"

git clone "$DELIVERY/bundles/AnyV2V.bundle" "$WORK/external/AnyV2V"
git -C "$WORK/external/AnyV2V" checkout --detach "$(grep '^anyv2v_git_commit=' "$DELIVERY/metadata/versions.txt" | cut -d= -f2)"

git -C "$WORK/project" status --short
git -C "$WORK/external/AnyV2V" status --short
```

两个 `status --short` 都必须为空。

### 4.3 解压环境

```bash
mkdir -p "$ENVS/w1-control" "$ENVS/anyv2v-cu118"
tar -xzf "$DELIVERY/envs/w1-control-linux-x86_64.tar.gz" -C "$ENVS/w1-control"
tar -xzf "$DELIVERY/envs/anyv2v-cu118-linux-x86_64.tar.gz" -C "$ENVS/anyv2v-cu118"
"$ENVS/w1-control/bin/conda-unpack"
"$ENVS/anyv2v-cu118/bin/conda-unpack"
```

将本项目安装进控制环境，不访问网络：

```bash
"$ENVS/w1-control/bin/pip" install --no-deps -e "$WORK/project"
"$ENVS/w1-control/bin/python" -m pytest "$WORK/project/tests"
"$ENVS/w1-control/bin/w1" version
```

预期测试全部通过，版本输出 `0.1.0`。

检查 GPU 环境：

```bash
"$ENVS/anyv2v-cu118/bin/python" - <<'PY'
import torch, diffusers, transformers
print("torch", torch.__version__)
print("cuda", torch.version.cuda)
print("gpu", torch.cuda.get_device_name(0))
print("diffusers", diffusers.__version__)
print("transformers", transformers.__version__)
assert torch.cuda.is_available()
assert diffusers.__version__ == "0.26.3"
PY
```

### 4.4 建立离线模型路径

AnyV2V 上游代码把模型 ID 写成相对字符串。无需修改上游源码，只需在它实际运行的 cwd 建立软链接：

```bash
mkdir -p "$WORK/external/AnyV2V/i2vgen-xl/ali-vilab"
mkdir -p "$WORK/external/AnyV2V/timbrooks"

ln -s "$DELIVERY/models/i2vgen-xl" \
  "$WORK/external/AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl"
ln -s "$DELIVERY/models/instruct-pix2pix" \
  "$WORK/external/AnyV2V/timbrooks/instruct-pix2pix"

test -f "$WORK/external/AnyV2V/i2vgen-xl/ali-vilab/i2vgen-xl/model_index.json"
test -f "$WORK/external/AnyV2V/timbrooks/instruct-pix2pix/model_index.json"
```

设置完全离线模式：

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
```

然后测试仅加载配置，不加载整套 GPU 权重：

```bash
cd "$WORK/external/AnyV2V/i2vgen-xl"
"$ENVS/anyv2v-cu118/bin/python" - <<'PY'
from diffusers import DDIMScheduler
s = DDIMScheduler.from_pretrained("ali-vilab/i2vgen-xl", subfolder="scheduler", local_files_only=True)
print(type(s).__name__)
PY
```

预期输出 `DDIMScheduler`，且没有任何网络请求。

### 4.5 在服务器重新准备 DAVIS

```bash
cd "$WORK/project"
"$ENVS/w1-control/bin/w1" validate
"$ENVS/w1-control/bin/w1" prepare \
  --davis-root "$DELIVERY/data/DAVIS" \
  --output-dir "$WORK/project/data/processed/w1"
"$ENVS/w1-control/bin/w1" validate \
  --prepared "$WORK/project/data/processed/w1/manifest.json"
```

预期：

```text
source manifest valid: 10 inputs, 5 seeds
prepared 10 inputs ...
prepared manifest valid: 10 inputs
```

每个输入应产生 16 张 512×512 PNG、16 张 mask 和一个 8 fps `source.mp4`。

### 4.6 写入远程实验前置 DEVLOG

在执行任何真实模型命令前，在 `DEVLOG.md` 新增 `RUNNING` 记录：

```text
experiment: E0-anyv2v-smoke-v01
location: school A6000
w1 commit: <SHA>
AnyV2V commit: <SHA>
I2VGen-XL revision: <SHA>
InstructPix2Pix revision: <SHA>
data: DAVIS train, first input only, seed 101
config: 512x512, 16 frames, 8 fps, inversion 500, PnP 50, CFG 9
expected output: artifacts/E0-anyv2v-smoke-v01-{a,b}
resource estimate: one A6000, <=48GB VRAM, at least 120GB free disk
```

必须先写日志，再运行模型。

### 4.7 生成完整计划和单样本 smoke plan

读取两个 revision：

```bash
export ANYV2V_SHA=$(grep '^anyv2v_git_commit=' "$DELIVERY/metadata/versions.txt" | cut -d= -f2)
export I2VGEN_SHA=$(grep '^i2vgen_xl_revision=' "$DELIVERY/metadata/versions.txt" | cut -d= -f2)
```

生成完整 10×5 计划：

```bash
cd "$WORK/project"
"$ENVS/w1-control/bin/w1" plan \
  --prepared "$WORK/project/data/processed/w1/manifest.json" \
  --output "$WORK/project/artifacts/E0-anyv2v-w1-v01-plan.json" \
  --backend anyv2v \
  --model-commit "$I2VGEN_SHA" \
  --anyv2v-commit "$ANYV2V_SHA"
```

预期：`planned 10 inversions and 50 candidates`。

生成只含第一个候选的 smoke plan：

```bash
"$ENVS/w1-control/bin/python" scripts/make_smoke_plan.py \
  --input artifacts/E0-anyv2v-w1-v01-plan.json \
  --output artifacts/E0-anyv2v-smoke-v01-plan.json
```

### 4.8 运行两次真实 smoke

```bash
export ANYV2V_ROOT="$WORK/external/AnyV2V"
export GPU_PYTHON="$ENVS/anyv2v-cu118/bin/python"

"$ENVS/w1-control/bin/w1" run \
  --backend anyv2v \
  --plan "$WORK/project/artifacts/E0-anyv2v-smoke-v01-plan.json" \
  --experiment-dir "$WORK/project/artifacts/E0-anyv2v-smoke-v01-a" \
  --cache "$WORK/project/artifacts/E0-anyv2v-smoke-v01-a/cache.sqlite3" \
  --anyv2v-root "$ANYV2V_ROOT" \
  --python-executable "$GPU_PYTHON" \
  --device cuda:0

"$ENVS/w1-control/bin/w1" run \
  --backend anyv2v \
  --plan "$WORK/project/artifacts/E0-anyv2v-smoke-v01-plan.json" \
  --experiment-dir "$WORK/project/artifacts/E0-anyv2v-smoke-v01-b" \
  --cache "$WORK/project/artifacts/E0-anyv2v-smoke-v01-b/cache.sqlite3" \
  --anyv2v-root "$ANYV2V_ROOT" \
  --python-executable "$GPU_PYTHON" \
  --device cuda:0
```

不要覆盖或复用 a/b 两个目录。每次都应输出 `completed: 1/1 succeeded`。

验证：

```bash
"$ENVS/w1-control/bin/w1" verify \
  --expected 1 \
  --candidates "$WORK/project/artifacts/E0-anyv2v-smoke-v01-a/candidates.json" \
  --compare "$WORK/project/artifacts/E0-anyv2v-smoke-v01-b/candidates.json"
```

理想结果：

```json
{"valid": true, "count": 1, "errors": {}, "reproducible": true}
```

如果 `reproducible` 为 false，不要直接运行 50 个候选。先记录 CUDA/cuDNN、driver、PyTorch、seed 和差异帧；官方 CUDA 算子可能存在非确定性，必须把实测情况写进 DEVLOG 后再决定是否把验收改为感知一致而非逐字节一致。

### 4.9 运行完整 50 候选

smoke 通过后，先在 DEVLOG 新增 `E0-anyv2v-w1-v01` 的 `RUNNING` 记录，再执行：

```bash
"$ENVS/w1-control/bin/w1" run \
  --backend anyv2v \
  --plan "$WORK/project/artifacts/E0-anyv2v-w1-v01-plan.json" \
  --experiment-dir "$WORK/project/artifacts/E0-anyv2v-w1-v01" \
  --cache "$WORK/project/artifacts/E0-anyv2v-w1-v01/cache.sqlite3" \
  --anyv2v-root "$ANYV2V_ROOT" \
  --python-executable "$GPU_PYTHON" \
  --device cuda:0
```

该命令会：

- 对每条源视频只做一次 DDIM inversion；
- 对五个 seed 分别执行首帧编辑和 PnP；
- 成功项写入 SQLite，重跑命令时自动跳过；
- 单个失败项保留错误，下次只重试失败项。

建议使用 `tmux`，并把标准输出保存到实验目录：

```bash
tmux new -s w1-anyv2v
# 在 tmux 内运行上面的命令，并在命令末尾加：
2>&1 | tee "$WORK/project/artifacts/E0-anyv2v-w1-v01/run.log"
```

### 4.10 验收、mock reward 和报告

```bash
"$ENVS/w1-control/bin/w1" verify \
  --expected 50 \
  --candidates "$WORK/project/artifacts/E0-anyv2v-w1-v01/candidates.json"
```

必须得到：

```json
{"valid": true, "count": 50, "errors": {}}
```

然后运行仅用于接口验收的 mock reward：

```bash
"$ENVS/w1-control/bin/w1" reward \
  --backend mock \
  --candidates "$WORK/project/artifacts/E0-anyv2v-w1-v01/candidates.json" \
  --output "$WORK/project/artifacts/E0-anyv2v-w1-v01/rewards.json" \
  --cache "$WORK/project/artifacts/E0-anyv2v-w1-v01/cache.sqlite3"

"$ENVS/w1-control/bin/w1" report \
  --plan "$WORK/project/artifacts/E0-anyv2v-w1-v01-plan.json" \
  --candidates "$WORK/project/artifacts/E0-anyv2v-w1-v01/candidates.json" \
  --rewards "$WORK/project/artifacts/E0-anyv2v-w1-v01/rewards.json" \
  --output-dir "$WORK/project/artifacts/E0-anyv2v-w1-v01/report"
```

mock reward 不能用于论文结论或候选排序，只证明 schema、缓存和报告链路可用。

## 5. 最终应达到的效果

服务器最终应包含：

```text
artifacts/E0-anyv2v-w1-v01/
├── anyv2v_data/
│   ├── demo/                         # 10 个源视频和帧
│   └── inversions/i2vgen-xl/         # 10 份复用的 inversion latents
├── candidates/
│   └── <sample-id>/seed-<seed>/
│       ├── video.mp4
│       ├── frame_00000.png ... frame_00015.png
│       ├── metadata.json
│       └── official-output/...
├── cache.sqlite3
├── candidates.json
├── rewards.json
├── run.log
└── report/
    ├── W1_REPORT.md
    ├── pipeline.mmd
    └── pipeline.svg
```

数量验收：

- 10 个输入；
- 10 份 inversion；
- 50 个候选目录；
- 50 个 `video.mp4`；
- 每个候选 16 张规范化 PNG；
- 每个视频 512×512、16 帧、8 fps；
- `candidates.json` 中 50 条均为 `succeeded`；
- `w1 verify` 返回 `valid: true`；
- 单条失败后重跑不会重新计算已成功的 49 条。

视觉上应看到 4 个属性编辑、3 个对象替换、3 个局部编辑，每个输入有五个随机种子版本。W1 的硬验收是“真实模型链路、媒体完整性、缓存和复现记录可用”，不是保证 50 个视频都具有同等语义质量；欠编辑、过编辑、闪烁和失败案例必须保留，供 W2 人工校准 reward 使用。

## 6. 故障处理

### 模型仍尝试联网

- 检查两个软链接的相对位置是否准确；
- 检查 `model_index.json` 是否存在；
- 保持 `HF_HUB_OFFLINE=1`；
- 错误中若出现 Hugging Face URL，说明本地 snapshot 不完整，不要关闭离线模式掩盖问题。

### `diffusers` 导入报 `cached_download` 错误

将 `huggingface_hub` 固定为 `0.20.3`；不要在服务器上无约束升级。

### CUDA OOM

- 用 `nvidia-smi` 确认无其他用户占用；
- 先只跑 smoke；
- 保持 512×512、16 帧、单候选串行；
- 不要在同一进程并行加载 IP2P 与 I2VGen-XL。

### inversion 目录存在但不完整

适配器会拒绝覆盖。记录失败后，把该明确的、唯一的未完成实验目录移动到带 `-failed-时间戳` 的诊断目录，再用新实验 ID 重跑；不要删除其他成功 inversion。

### 运行中断

直接用相同 plan、experiment dir 和 cache 重跑。成功候选会命中缓存，失败或缺失候选会再次执行。

### 国内镜像不可达

停止在线安装，改用随包携带的 conda-pack 环境。不要临时切换来源不明的模型或二进制包。

## 7. 从服务器带回哪些结果

至少带回：

```text
artifacts/E0-anyv2v-smoke-v01-a/
artifacts/E0-anyv2v-smoke-v01-b/
artifacts/E0-anyv2v-w1-v01/candidates/
artifacts/E0-anyv2v-w1-v01/candidates.json
artifacts/E0-anyv2v-w1-v01/cache.sqlite3
artifacts/E0-anyv2v-w1-v01/rewards.json
artifacts/E0-anyv2v-w1-v01/report/
artifacts/E0-anyv2v-w1-v01/run.log
DEVLOG.md
```

inversion latents 体积较大；确认以后还要在相同源视频上补 seed 时再带回，否则可保留在服务器并只带 checksum/路径清单。带回前为结果目录生成 SHA-256 清单，传回本地后再次校验。

