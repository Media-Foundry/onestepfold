#!/usr/bin/env bash
set -euo pipefail

PROTENIX_PYTHON="${PROTENIX_PYTHON:-/hpc2ssd/softwares/anaconda3/envs/af3/bin/python}"
PROTENIX_SITE="${PROTENIX_SITE:-/hpc2hdd/home/shuang886/Folding/protenix_stage0_pkg/v1_1/site}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-/hpc2hdd/home/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime}"

if command -v module >/dev/null 2>&1; then
  module load cuda >/dev/null 2>&1 || true
fi
if [[ -z "${CUDA_HOME:-}" ]] && command -v nvcc >/dev/null 2>&1; then
  CUDA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v nvcc)")")")"
  export CUDA_HOME
fi
export PROTENIX_ROOT_DIR
export PYTHONPATH="$PROTENIX_SITE${PYTHONPATH:+:$PYTHONPATH}"

echo "hostname=$(hostname)"
echo "python=$PROTENIX_PYTHON"
echo "cuda_home=${CUDA_HOME:-}"
nvidia-smi -L
"$PROTENIX_PYTHON" --version
"$PROTENIX_PYTHON" - <<'PY'
import torch
import protenix

assert torch.cuda.is_available(), "CUDA is not available on the allocated node"
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("device", torch.cuda.get_device_name(0))
print("protenix", protenix.__version__)
PY
"$PROTENIX_SITE/bin/protenix" --help >/dev/null
echo "protenix_cli_smoke=ok"
