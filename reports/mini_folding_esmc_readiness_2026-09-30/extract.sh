#!/bin/bash
set -euo pipefail
BASE=/data/user/shuang886/Folding
ROOT="$BASE/folding_esmc_features_v1_20260930"
export PYTHONPATH="$ROOT/code/scripts:$ROOT/code/src:$BASE/vendor/esm-bf343ba:$ROOT/deps"
export HF_HOME="$BASE/hf_cache" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/code/scripts/run_folding_esmc_cache.py" --root "$ROOT"
