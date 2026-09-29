#!/bin/bash
set -u
base=/media/PM982/onestepfold
root=$base/validation_raw_remaining_v3_20260930
export PYTHONPATH="$root/code/src:$root/code/scripts"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 ROCR_VISIBLE_DEVICES=""
export LAYERNORM_TYPE=torch PROTENIX_ROOT_DIR="$base/protenix_stage0_pkg/v1_1/runtime"
/home/pc/anaconda3/envs/fold/bin/python "$root/code/scripts/extend_raw_validation_sources.py" --remaining --root "$root" --base "$base" --v1 "$base/anchored_independent_v1_20260929" --v2 "$base/isolation_calibration_v2_1_20260930" --previous-root "$base/validation_source_extension_v1_1_20260930" --bin "$base/tools/blast_2.17.0/ncbi-blast-2.17.0+/bin"
status=$?
if [ "$status" -eq 0 ]; then
/home/pc/anaconda3/envs/fold/bin/python "$root/code/scripts/preflight_isolated_chemistry.py" --root "$root/chemistry" --base "$base" --selection "$root/chemistry_selection.json" --data-root "$root/data"
status=$?
fi
printf '{"exit_code":%s}\n' "$status" > "$root/exit.json"
exit "$status"
