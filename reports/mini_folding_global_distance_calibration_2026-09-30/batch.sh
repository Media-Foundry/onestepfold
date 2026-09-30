#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_global_distance_calibration_v1_20260930
export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime
export PYTHONPATH="$ROOT/code/src:$ROOT/code:$ROOT/code/scripts"
cd "$ROOT"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u code/scripts/calibrate_folding_global_distance.py --root "$ROOT" --workers 8
