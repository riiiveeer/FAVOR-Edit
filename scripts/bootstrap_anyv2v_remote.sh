#!/usr/bin/env bash
set -euo pipefail

echo "WARNING: this bootstrap script requires GitHub/Conda network access." >&2
echo "For the offline school server, follow docs/SCHOOL_SERVER_DELIVERY.md instead." >&2

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <workspace> <anyv2v-commit> <experiment-id>" >&2
  exit 2
fi

workspace="$1"
anyv2v_commit="$2"
experiment_id="$3"
repo_dir="${workspace}/external/AnyV2V"
experiment_dir="${workspace}/artifacts/${experiment_id}"

[[ "${anyv2v_commit}" =~ ^[0-9a-f]{40}$ ]] || { echo "exact AnyV2V commit required" >&2; exit 2; }
[[ ! -e "${experiment_dir}" ]] || { echo "experiment directory already exists: ${experiment_dir}" >&2; exit 3; }

mkdir -p "${workspace}/external" "${experiment_dir}"
if [[ ! -d "${repo_dir}/.git" ]]; then
  git clone https://github.com/TIGER-AI-Lab/AnyV2V.git "${repo_dir}"
fi
git -C "${repo_dir}" fetch --all --tags
git -C "${repo_dir}" checkout --detach "${anyv2v_commit}"
conda env create -f "${repo_dir}/i2vgen-xl/environment.yml" || true

git -C "${repo_dir}" rev-parse HEAD > "${experiment_dir}/anyv2v-commit.txt"
nvidia-smi > "${experiment_dir}/nvidia-smi-before.txt"
