#!/bin/bash
set -euo pipefail
BASE=/data/user/shuang886/Folding
ROOT="$BASE/folding_coordinate_evaluation_v1_20260930"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR="$BASE/protenix_stage0_pkg/v1_1/runtime"
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts"
PY=/data/user/shuang886/.conda/envs/fold/bin/python
case "$1" in
  prepare|report)
    export CUDA_VISIBLE_DEVICES=""
    exec "$PY" -u "$ROOT/code/scripts/evaluate_folding_coordinate_ablation.py" --root "$ROOT" --mode "$1"
    ;;
  worker)
    exec "$PY" -u "$ROOT/code/scripts/evaluate_diffusion_learning.py" --root "$ROOT" --mode worker --index "$2"
    ;;
  score)
    export CUDA_VISIBLE_DEVICES=""
    "$PY" -u "$ROOT/code/scripts/evaluate_folding_scale.py" --root "$ROOT" --mode collect
    "$PY" -u "$ROOT/code/scripts/score_diffusion_learning.py" --root "$ROOT" --workers 12
    exec "$PY" -u "$ROOT/code/scripts/evaluate_folding_scale.py" --root "$ROOT" --mode cohorts
    ;;
  *) exit 2;;
esac
