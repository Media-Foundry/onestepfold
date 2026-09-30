#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_esmc_bridge_v1_20260930
export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export PYTHONPATH="$ROOT/code/src"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/fit_folding_esmc_bridge.py" --root "$ROOT"
