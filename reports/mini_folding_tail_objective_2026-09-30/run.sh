#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_tail_objective_audit_v1_20260930
TRAIN=/data/user/shuang886/Folding/folding_scale_training_v1_20260930
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$TRAIN/code/src:$TRAIN/code/scripts"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/audit_folding_tail_objective.py" --training-root "$TRAIN" --output "$ROOT/report.json"
