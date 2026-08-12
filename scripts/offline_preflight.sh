#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <delivery-dir> <work-dir> <control-python> <gpu-python>" >&2
  exit 2
fi

delivery="$1"
work="$2"
control_python="$3"
gpu_python="$4"

required_sequences=(bear bus elephant classic-car dog-gooses horsejump-low mallard-water hike scooter-gray drift-turn)

for path in \
  "$delivery/bundles/robust-v2v-w1.bundle" \
  "$delivery/bundles/AnyV2V.bundle" \
  "$delivery/models/i2vgen-xl/model_index.json" \
  "$delivery/models/instruct-pix2pix/model_index.json" \
  "$delivery/metadata/versions.txt" \
  "$delivery/metadata/SHA256SUMS"; do
  [[ -f "$path" ]] || { echo "missing: $path" >&2; exit 3; }
done

for sequence in "${required_sequences[@]}"; do
  [[ -d "$delivery/data/DAVIS/JPEGImages/480p/$sequence" ]] || { echo "missing frames: $sequence" >&2; exit 3; }
  [[ -d "$delivery/data/DAVIS/Annotations/480p/$sequence" ]] || { echo "missing masks: $sequence" >&2; exit 3; }
done

gpu_line=$(nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader | head -n 1)
echo "GPU: $gpu_line"
grep -qi "A6000" <<<"$gpu_line" || { echo "first GPU is not an A6000" >&2; exit 4; }

free_kb=$(df -Pk "$work" | awk 'NR==2 {print $4}')
(( free_kb >= 120 * 1024 * 1024 )) || { echo "less than 120GB free in $work" >&2; exit 5; }

"$control_python" -c "import pydantic, typer, yaml, imageio, PIL; print('control imports OK')"
"$gpu_python" -c "import torch, diffusers, transformers; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, diffusers.__version__, transformers.__version__)"

echo "offline preflight passed"

