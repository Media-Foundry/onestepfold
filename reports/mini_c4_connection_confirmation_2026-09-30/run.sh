#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH=/media/PM982/onestepfold/independent32_v2_20260930/deps_offline:/media/PM982/onestepfold/c4_connection_confirmation_v1_20260930/code/src
export PROTENIX_ROOT_DIR=/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime
export LAYERNORM_TYPE=torch
TASK_ROOT=/media/PM982/onestepfold/c4_connection_confirmation_v1_20260930
TASK_PY=/home/pc/anaconda3/envs/fold/bin/python
cd "$TASK_ROOT"
trap 'rc=$?; echo "{\"returncode\":$rc}" > pipeline_exit.json' EXIT
"$TASK_PY" code/run_c4_connection_confirmation.py --root "$TASK_ROOT" --mode prepare
"$TASK_PY" code/run_c4_connection_confirmation.py --root "$TASK_ROOT" --mode batch
"$TASK_PY" code/run_c4_connection_confirmation.py --root "$TASK_ROOT" --mode seal
export ROCR_VISIBLE_DEVICES=''
"$TASK_PY" code/run_connection_window_trial.py --root "$TASK_ROOT" --mode batch
"$TASK_PY" code/audit_connection_window_trial.py --root "$TASK_ROOT"
"$TASK_PY" code/report_connection_window_trial.py --root "$TASK_ROOT"
