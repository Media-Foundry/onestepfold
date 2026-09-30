#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_esm_pair_audit_v1_20260930
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH=/data/user/shuang886/Folding/folding_esmc_features_v1_20260930/deps
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$ROOT/audit_folding_esm_pairs.py" --training /data/user/shuang886/Folding/folding_scale_training_v1_20260930 --esmc /data/user/shuang886/Folding/folding_esmc_features_v1_20260930 --output "$ROOT/report.json"
