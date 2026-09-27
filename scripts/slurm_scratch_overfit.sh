#!/bin/bash
#SBATCH --partition=acd_u
#SBATCH --job-name=scratch-overfit
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
set -euo pipefail
: "${CODE_ROOT:?}" "${OUTPUT_ROOT:?}" "${ARM:?}"
FOLD_BASE=/data/user/shuang886/Folding/stage1b/coordinate_refiner
FOLD_PYTHON=/data/user/shuang886/.conda/envs/fold/bin/python
export PYTHONPATH="$CODE_ROOT/src:$FOLD_BASE/scaling_eval_deps_v1"
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/runtime_cache/protenix_v1_1
export LAYERNORM_TYPE=torch OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$CODE_ROOT"
"$FOLD_PYTHON" -m pytest -q tests/test_smooth_lddt_supervision.py -k "cuda"
"$FOLD_PYTHON" "$CODE_ROOT/scripts/train_scratch_overfit.py" \
  --parent "$FOLD_BASE/esmc_articulated_capacity_v1_20260918" \
  --arm "$ARM" --size 4 --output "${OUTPUT_ROOT}_preflight" --preflight-only
"$FOLD_PYTHON" "$CODE_ROOT/scripts/train_scratch_overfit.py" \
  --parent "$FOLD_BASE/esmc_articulated_capacity_v1_20260918" \
  --arm "$ARM" --size 4 --output "$OUTPUT_ROOT"
CUDA_VISIBLE_DEVICES= "$FOLD_PYTHON" "$CODE_ROOT/scripts/validate_scratch_overfit.py" \
  --root "$OUTPUT_ROOT"
