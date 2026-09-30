#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_esmc_comparison_v1_20260930
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts"
if [[ "$1" == prepare || "$1" == score ]]; then
 export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''
fi
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/evaluate_folding_esmc.py" --root "$ROOT" --mode "$@"
