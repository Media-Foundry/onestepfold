#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_global_distance_training_v1_20260930
BASE=/data/user/shuang886/Folding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR="$BASE/protenix_stage0_pkg/v1_1/runtime"
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts:$ROOT/code"
cd "$ROOT"
if [[ "$1" == prepare || "$1" == audit ]]; then export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''; fi
exec /data/user/shuang886/.conda/envs/fold/bin/python -u code/scripts/train_folding_global_distance.py --root "$ROOT" --mode "$1" --control "$BASE/folding_scale_training_v1_20260930" --calibration "$BASE/folding_global_distance_calibration_v1_20260930" --evaluation "$BASE/folding_coordinate_evaluation_v1_20260930"
