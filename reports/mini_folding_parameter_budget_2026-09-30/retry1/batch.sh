#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_parameter_budget_v1_20260930_retry1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/probe_folding_parameter_budget.py" --root "$ROOT" --index "$1"
