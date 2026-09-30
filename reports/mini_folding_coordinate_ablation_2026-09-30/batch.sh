#!/bin/bash
set -euo pipefail
BASE=/data/user/shuang886/Folding
ROOT="$BASE/folding_coordinate_ablation_v1_20260930"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR="$BASE/protenix_stage0_pkg/v1_1/runtime"
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts"
if [[ "$1" == prepare || "$1" == audit ]]; then export CUDA_VISIBLE_DEVICES=""; fi
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/train_folding_coordinate_ablation.py" --root "$ROOT" --mode "$1" --control "$BASE/folding_scale_training_v1_20260930" --evaluation "$BASE/folding_scale_evaluation_v1_20260930"
