#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_gradient_budget_v1_20260930
export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/measure_folding_gradient_budget.py" --root "$ROOT" --workers 8
