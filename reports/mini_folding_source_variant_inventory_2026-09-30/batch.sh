#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_unseen_source_inventory_v1_20260930
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$ROOT/code"
cd "$ROOT"
sha256sum -c code.sha256
exec /data/user/shuang886/.conda/envs/fold/bin/python -u code/inventory_folding_source_variants.py --root "$ROOT"
