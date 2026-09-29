#!/bin/bash
set -u
source=/media/PM982/onestepfold/independent32_v2_20260930
root=/media/PM982/onestepfold/independent32_analysis_v1_20260930
export PYTHONPATH="$source/deps_offline:$root/code/src:$root/code/scripts"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ROCR_VISIBLE_DEVICES=""
for attempt in $(seq 1 960); do
 if [ -f "$source/exit.json" ]; then break; fi
 if ! kill -0 169720 2>/dev/null; then
  printf '{"exit_code":125,"reason":"source pipeline exited without terminal artifact"}\n' > "$root/exit.json"
  exit 125
 fi
 sleep 15
done
if [ ! -f "$source/exit.json" ]; then
 printf '{"exit_code":124,"reason":"bounded wait expired; source may remain live"}\n' > "$root/exit.json"
 exit 124
fi
/home/pc/anaconda3/envs/fold/bin/python "$root/code/scripts/summarize_independent_geometry.py" --root "$source" --out "$root/results"
status=$?
printf '{"exit_code":%s}\n' "$status" > "$root/exit.json"
exit "$status"
