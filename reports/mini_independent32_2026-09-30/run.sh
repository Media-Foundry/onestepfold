#!/bin/bash
set -u
root=/media/PM982/onestepfold/independent32_v2_20260930
export PYTHONPATH="$root/deps_offline:$root/code/src:$root/code/scripts"
export PROTENIX_ROOT_DIR=/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime
export LAYERNORM_TYPE=torch OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
py=/home/pc/anaconda3/envs/fold/bin/python
"$py" "$root/code/scripts/run_independent_geometry_validation.py" --root "$root" --mode batch
batch_status=$?
"$py" "$root/code/scripts/audit_independent_geometry_validation.py" --root "$root"
audit_status=$?
"$py" "$root/code/scripts/collect_independent_geometry_validation.py" --root "$root"
score_status=$?
printf '{"batch_exit":%s,"audit_exit":%s,"score_exit":%s}\n' "$batch_status" "$audit_status" "$score_status" > "$root/exit.json"
