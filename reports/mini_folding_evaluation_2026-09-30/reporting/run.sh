#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_scale_reporting_v1_20260930
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$ROOT/code/src"
sha256sum -c "$ROOT/code.sha256"
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/report_folding_scale.py" --root /data/user/shuang886/Folding/folding_scale_evaluation_v1_20260930 --output "$ROOT/result"
